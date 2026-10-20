import hashlib
import json
import os
import re
import threading
import uuid
from enum import Enum
from datetime import timezone, datetime
from pathlib import Path

import structlog


class AuditEventType(str, Enum):
    """AuditLogs holds operational errors and recoveries; business events remain plain log lines"""
    TRADE_REJECTED = "TRADE_REJECTED"
    DB_PUSH_ERROR = "DB_PUSH_ERROR"
    STREAM_ERROR = "STREAM_ERROR"
    LOG_ERROR = "LOG_ERROR"
    SERVICE_ERROR = "SERVICE_ERROR"
    SERVICE_RECOVERED = "SERVICE_RECOVERED"


def log_audit_error(log, event_type, message, *, entity_type=None, entity_id=None, exc_info=False, **fields):
    """Single entry point for audited errors: ERROR line in the .log file -> ErrorLogShipper -> AuditLogs.

    message becomes AuditLogs.message, event_type/entity_* map to their columns, extra fields go to payload.
    """
    if exc_info:
        fields["exc_info"] = exc_info
    log.error(
        message,
        audit_event_type=getattr(event_type, "value", event_type),
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        **fields,
    )


def log_audit_recovery(log, service_name, downtime_seconds):
    log.info(
        "Service recovered",
        audit_event_type=AuditEventType.SERVICE_RECOVERED.value,
        entity_type="Service",
        entity_id=service_name,
        downtime_seconds=round(downtime_seconds, 3),
    )


# Cheap byte-level pre-filter; json.loads only runs for the (rare) matching lines
ERROR_LINE_PATTERN = re.compile(rb'"level":\s*"(?:error|critical)"')
SHIPPED_LEVELS = frozenset({"error", "critical"})
INFO_AUDIT_EVENT_TYPES = frozenset({AuditEventType.SERVICE_RECOVERED.value})
INFO_AUDIT_EVENT_PATTERN = re.compile(rb'"audit_event_type":\s*"SERVICE_RECOVERED"')
_FINGERPRINT_MAX_BYTES = 4096
_LOG_LINE_NAMESPACE = uuid.UUID("5b0c7a5e-6f1d-4c5e-9a43-3f1f4f2b8d11")


def iter_complete_lines(fh, offset):
    """Yield (end_offset, line) for newline-terminated lines from offset; stops before a half-written tail"""
    fh.seek(offset)
    for line in fh:
        if not line.endswith(b"\n"):
            return
        offset += len(line)
        yield offset, line


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _verified_tail(fh, offset, tail_len, tail_hash):
    if offset == 0:
        return b""
    if tail_len is None or tail_hash is None or tail_len <= 0 or tail_len > offset:
        return None
    fh.seek(0, os.SEEK_END)
    if offset > fh.tell():
        return None
    fh.seek(offset - tail_len)
    tail = fh.read(tail_len)
    return tail if tail.endswith(b"\n") and _sha256(tail) == tail_hash else None


def _read_fingerprint(fh):
    """Identify a log file by its first line; survives renames done by RotatingFileHandler"""
    fh.seek(0)
    first = fh.readline(_FINGERPRINT_MAX_BYTES)
    if not first.endswith(b"\n") and len(first) < _FINGERPRINT_MAX_BYTES:
        return None
    return hashlib.sha256(first).hexdigest()


def _fingerprint(path):
    try:
        with open(path, "rb") as fh:
            return _read_fingerprint(fh)
    except FileNotFoundError:
        return None


def _parse_timestamp(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class ErrorLogShipper:
    """Tail a service's JSON .log file and push ERROR/CRITICAL lines to the AuditLogs table.

    The .log file acts as a durable outbox. After each batch the byte offset (plus a fingerprint of the
    file and a hash of the last shipped line) is checkpointed next to the log, so after a crash /
    `docker stop` the next start resumes where shipping stopped, including lines that were rotated into
    <service>.log.N meanwhile. If the file no longer matches the checkpoint (e.g. data lost in a power
    failure), the file is re-scanned from the start. Inserts use the
    line's audit_id with ON CONFLICT DO NOTHING, so a crash between DB commit and checkpoint write
    cannot create duplicates (at-least-once delivery + idempotent sink = effectively once).
    """

    def __init__(self, service_name, log_file, backup_count=5, push=None, poll_interval=2.0,
                 max_backoff=30.0, batch_lines=1000):
        self.service_name = service_name
        self.log_file = Path(log_file)
        self.backup_count = backup_count
        self.checkpoint_file = self.log_file.with_name(self.log_file.name + ".checkpoint.json")
        self.poll_interval = poll_interval
        self.max_backoff = max_backoff
        self.batch_lines = batch_lines
        self._push = push
        self._last_checkpoint = None
        self._stop_event = threading.Event()
        self._thread = None
        self.log = structlog.get_logger("trading_shared.audit_shipper")

    def start(self):
        self._thread = threading.Thread(target=self._run, name="audit-error-shipper", daemon=True)
        self._thread.start()

    def stop(self, timeout=5.0):
        """Stop polling and make a final best-effort pass"""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self):
        checkpoint = self._load_checkpoint()
        self.log.info("audit_shipper_started", log_file=str(self.log_file),
                      resume_offset=checkpoint["offset"] if checkpoint else None)
        recovering = True
        delay = self.poll_interval
        while True:
            try:
                shipped = self.run_once()
                if shipped:
                    self.log.info("audit_shipper_recovered" if recovering else "audit_shipper_shipped", count=shipped)
                recovering = False
                delay = self.poll_interval
            except Exception as exc:
                delay = min(delay * 2, self.max_backoff)
                self.log.warning("audit_shipper_push_failed", error=repr(exc), retry_in=delay)
            if self._stop_event.wait(delay):
                break
        try:
            self.run_once()
        except Exception as exc:
            self.log.warning("audit_shipper_final_pass_failed", error=repr(exc))

    def run_once(self):
        """Ship all complete error lines that were not shipped yet; returns the number of rows pushed"""
        files = [(path, _fingerprint(path)) for path in self._candidate_files()]
        files = [(path, fp) for path, fp in files if fp is not None]
        if not files:
            return 0

        start, offset, tail = 0, 0, (None, None)
        checkpoint = self._load_checkpoint()
        if checkpoint:
            # No match -> checkpointed file already rotated out of retention: ship everything still on disk
            for index, (_, fp) in enumerate(files):
                if fp == checkpoint["fingerprint"]:
                    start, offset = index, checkpoint["offset"]
                    tail = (checkpoint["tail_len"], checkpoint["tail_hash"])
                    break

        shipped = 0
        for path, fp in files[start:]:
            shipped += self._ship_file(path, fp, offset, *tail)
            offset, tail = 0, (None, None)
        return shipped

    def _candidate_files(self):
        """Oldest -> newest: <service>.log.N ... <service>.log.1, <service>.log"""
        rotated = (self.log_file.with_name(f"{self.log_file.name}.{i}") for i in range(self.backup_count, 0, -1))
        return [path for path in rotated if path.exists()] + [self.log_file]

    def _ship_file(self, path, fingerprint, offset, tail_len=None, tail_hash=None):
        try:
            fh = open(path, "rb")
        except FileNotFoundError:
            return 0
        with fh:
            if _read_fingerprint(fh) != fingerprint:
                return 0  # rotated between listing and opening; picked up on the next poll
            last_line = _verified_tail(fh, offset, tail_len, tail_hash)
            if last_line is None:
                # Re-scan is safe: inserts are idempotent on audit_id
                self.log.warning("audit_shipper_checkpoint_mismatch", log_file=str(path), offset=offset)
                offset, last_line = 0, b""

            shipped, scanned, rows, end_offset = 0, 0, [], offset
            for end_offset, raw in iter_complete_lines(fh, offset):
                last_line = raw
                if ERROR_LINE_PATTERN.search(raw) or INFO_AUDIT_EVENT_PATTERN.search(raw):
                    row = self._to_audit_row(raw)
                    if row is not None:
                        rows.append(row)
                scanned += 1
                if scanned >= self.batch_lines:
                    shipped += self._flush(rows, fingerprint, end_offset, last_line)
                    scanned, rows = 0, []
            shipped += self._flush(rows, fingerprint, end_offset, last_line)
            return shipped

    def _flush(self, rows, fingerprint, end_offset, last_line):
        """Push first, checkpoint second: a failed push leaves the offset untouched and is retried"""
        if rows:
            self._push_rows(rows)
        self._save_checkpoint(fingerprint, end_offset, last_line)
        return len(rows)

    def _push_rows(self, rows):
        if self._push is None:
            from shared.trading_shared.repositories import AuditLogsRepository
            self._push = AuditLogsRepository().push_audit_logs_idempotent
        self._push(rows)

    def _to_audit_row(self, raw):
        try:
            record = json.loads(raw)
        except ValueError:
            self.log.warning("audit_shipper_unparseable_line", line=raw[:200].decode("utf-8", "replace"))
            return None
        if not isinstance(record, dict):
            return None
        level = record.get("level")
        event_type = record.get("audit_event_type")
        is_error = level in SHIPPED_LEVELS
        is_audited_info = level == "info" and event_type in INFO_AUDIT_EVENT_TYPES
        if not (is_error or is_audited_info):
            return None

        try:
            audit_id = uuid.UUID(str(record.pop("audit_id")))
        except (KeyError, ValueError):
            audit_id = uuid.uuid5(_LOG_LINE_NAMESPACE, hashlib.sha256(raw.rstrip()).hexdigest())
        entity_id = record.pop("entity_id", None)

        return {
            "audit_id": audit_id,
            "created_at": _parse_timestamp(record.pop("timestamp", None)),
            "service_name": record.pop("service", None) or self.service_name,
            "event_type": str(record.pop("audit_event_type", None) or AuditEventType.LOG_ERROR.value),
            "entity_type": record.pop("entity_type", None),
            "entity_id": str(entity_id) if entity_id is not None else None,
            "correlation_id": record.pop("correlation_id", None),
            "severity": "INFO" if is_audited_info else "ERROR",
            "message": str(record.pop("event", "")),
            "payload": record,
        }

    def _load_checkpoint(self):
        try:
            data = json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
            tail_len = data.get("tail_len")
            return {
                "fingerprint": str(data["fingerprint"]),
                "offset": int(data["offset"]),
                "tail_len": int(tail_len) if tail_len is not None else None,
                "tail_hash": data.get("tail_hash"),
            }
        except FileNotFoundError:
            return None
        except (ValueError, KeyError, TypeError):
            self.log.warning("audit_shipper_corrupt_checkpoint", checkpoint=str(self.checkpoint_file))
            return None

    def _save_checkpoint(self, fingerprint, offset, last_line):
        tail_hash = _sha256(last_line)
        state = (fingerprint, offset, tail_hash)
        if self._last_checkpoint == state:
            return
        tmp = self.checkpoint_file.with_name(self.checkpoint_file.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({
                "fingerprint": fingerprint,
                "offset": offset,
                "tail_len": len(last_line),
                "tail_hash": tail_hash,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.checkpoint_file)
        self._last_checkpoint = state
