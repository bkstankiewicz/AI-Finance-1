"""Shared logging setup for all trading services.

Pipeline:
    structlog (caller thread: level filter, enrichment, exc_info capture)
        -> stdlib QueueHandler (non-blocking, hot paths never wait on disk I/O)
        -> QueueListener thread -> console handler (human readable)
                                -> RotatingFileHandler (JSON lines, one file per service)
    ErrorLogShipper thread (audit.py) tails the JSON file and pushes ERROR/CRITICAL lines to AuditLogs.

Usage (first statement executed in a service's ``__main__``):
    configure_logging(SERVICE_NAME)

Environment variables:
    LOG_DIR           base directory, the file lands in <LOG_DIR>/<service>/<service>.log
    LOG_LEVEL         DEBUG / INFO / WARNING / ERROR / CRITICAL (default INFO)
    LOG_MAX_BYTES     rotate after this many bytes (default 10 MB)
    LOG_BACKUP_COUNT  rotated files kept (default 5)
"""
import atexit
import importlib.util
import logging
import logging.handlers
import os
import queue
import signal
import sys
import threading
import uuid
from pathlib import Path

import structlog

from shared.trading_shared.serialization import to_jsonable

DEFAULT_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
ERROR_LEVELS = ["error", "critical"]

_runtime = {}
_atexit_registered = False


def _add_service(service_name):
    def processor(_, __, event_dict):
        event_dict.setdefault("service", service_name)
        return event_dict
    return processor


def _add_audit_id(_, __, event_dict):
    """Give error lines a stable id; the shipper uses it as AuditLogs PK so replays are idempotent"""
    if event_dict.get("level") in ERROR_LEVELS:
        event_dict.setdefault("audit_id", str(uuid.uuid4()))
    return event_dict


def _capture_exc_info(_, __, event_dict):
    """Resolve exc_info=True while still in the caller's thread; the listener thread has no active exception"""
    if event_dict.get("exc_info") is True:
        exc_info = sys.exc_info()
        if exc_info[0] is None:
            event_dict.pop("exc_info")
        else:
            event_dict["exc_info"] = exc_info
    return event_dict


def _json_default(value):
    """UUID/Decimal/datetime -> JSON primitives (same rules as DB payloads), anything else -> repr"""
    converted = to_jsonable(value)
    return repr(value) if converted is value else converted


class _StructlogQueueHandler(logging.handlers.QueueHandler):
    """Enqueue records untouched; the stock prepare() pre-formats them, which breaks ProcessorFormatter"""

    def prepare(self, record):
        return record


def _terminate_torn_line(log_file):
    try:
        with open(log_file, "r+b") as log:
            log.seek(0, os.SEEK_END)
            end = log.tell()
            if not end:
                return
            log.seek(end - 1)
            if log.read(1) == b"\n":
                return
            while end:
                start = max(0, end - 4096)
                log.seek(start)
                newline = log.read(end - start).rfind(b"\n")
                if newline >= 0:
                    log.truncate(start + newline + 1)
                    return
                end = start
            log.truncate(0)
    except FileNotFoundError:
        pass


def _install_sigterm_handler():
    """`docker stop` sends SIGTERM; turning it into SystemExit lets atexit flush logs and ship pending errors"""
    if threading.current_thread() is not threading.main_thread():
        return
    if signal.getsignal(signal.SIGTERM) is not signal.SIG_DFL:
        return

    def _on_sigterm(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, _on_sigterm)


def _shutdown():
    """Drain the log queue to disk, then let the shipper do a final pass"""
    listener = _runtime.pop("listener", None)
    shipper = _runtime.pop("shipper", None)
    queue_handler = _runtime.pop("queue_handler", None)
    handlers = _runtime.pop("handlers", ())

    if listener is not None:
        listener.stop()
    root = logging.getLogger()
    if queue_handler is not None:
        # The listener is gone: route any late records (e.g. from the shipper) synchronously
        root.removeHandler(queue_handler)
        for handler in handlers:
            root.addHandler(handler)
    if shipper is not None:
        shipper.stop()
    for handler in handlers:
        handler.flush()


def configure_logging(service_name, log_dir=None, level=None, ship_errors=True, handle_sigterm=True):
    """Configure structlog + stdlib logging for a service and return the path of its .log file.

    ship_errors: start ErrorLogShipper, which pushes ERROR/CRITICAL lines to the AuditLogs table
                 (requires DB access, disable for services without a database).
    """
    global _atexit_registered

    _shutdown()

    level_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    service_dir = Path(log_dir or os.environ.get("LOG_DIR") or DEFAULT_LOG_DIR) / service_name
    service_dir.mkdir(parents=True, exist_ok=True)
    log_file = service_dir / f"{service_name}.log"
    backup_count = int(os.environ.get("LOG_BACKUP_COUNT", 5))
    _terminate_torn_line(log_file)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        _add_service(service_name),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_audit_id,
    ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            _capture_exc_info,
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024)),
        backupCount=backup_count,
        encoding="utf-8",
    )

    file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(default=_json_default),
        ],
    ))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        ],
    ))

    # Unbounded on purpose: a bounded queue would drop records (possibly errors) under bursts
    log_queue = queue.SimpleQueue()
    queue_handler = _StructlogQueueHandler(log_queue)
    listener = logging.handlers.QueueListener(log_queue, console_handler, file_handler, respect_handler_level=True)

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    root.addHandler(queue_handler)
    root.setLevel(level_name)

    listener.start()
    _runtime.update(listener=listener, queue_handler=queue_handler, handlers=(console_handler, file_handler))

    if ship_errors:
        from shared.trading_shared.audit import ErrorLogShipper

        shipper = ErrorLogShipper(service_name, log_file, backup_count=backup_count)
        shipper.start()
        _runtime["shipper"] = shipper

    if not _atexit_registered:
        atexit.register(_shutdown)
        _atexit_registered = True
    if handle_sigterm:
        _install_sigterm_handler()

    return log_file
