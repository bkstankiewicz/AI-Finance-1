## Logging & audit (PoC)

Every service calls `configure_logging(SERVICE_NAME)` (`shared/trading_shared/logging_config.py`) at startup:

- **structlog -> stdlib logging**: logs go through a non-blocking `QueueHandler`/`QueueListener` to the console
  (human readable) and to `<LOG_DIR>/<service>/<service>.log` (JSON lines, rotated).
- **Audit shipping**: `ErrorLogShipper` (`shared/trading_shared/audit.py`) tails the `.log` file and pushes
  `error`/`critical` lines plus the explicit `SERVICE_RECOVERED` info event to `AuditLogs`.
  Business events such as `trade_opened` or `book_created` remain plain log lines in the file.
- **Audited errors**: use `log_audit_error(log, AuditEventType.X, "Human readable message", entity_type=..., entity_id=..., **payload)`
  (`TRADE_REJECTED`, `STREAM_ERROR`, `DB_PUSH_ERROR`). Any other `log.error` / `log.exception` is stored as `LOG_ERROR`.
- **No lost errors**: shipped byte offset is checkpointed in `<service>.log.checkpoint.json`. After `docker stop`,
  a crash or a DB outage, the next start resumes from the checkpoint (also across rotated files).
  Inserts are idempotent (`audit_id` + `ON CONFLICT DO NOTHING`), so a replay never duplicates rows.
- `docker stop` (SIGTERM) flushes the log queue and makes a final shipping pass before exit.
- Application containers use `restart: unless-stopped`, so Docker restarts them when their main process exits.
  This does not restart a process that is alive but no longer responding; monitoring records `SERVICE_ERROR`
  when it detects the outage and `SERVICE_RECOVERED` when a later health check succeeds.

With Docker Compose, logs are mapped to `./logs` on the host.

| Variable           | Default                          |
|--------------------|----------------------------------|
| `LOG_DIR`          | `/var/log/trading` (Docker), `./logs` locally |
| `LOG_LEVEL`        | `INFO`                           |
| `LOG_MAX_BYTES`    | `10485760` (10 MB)               |
| `LOG_BACKUP_COUNT` | `5`                              |

`monitoring-service` has DB access to query service-error counts and timestamps. Its detected service outages
and recoveries are shipped to `AuditLogs` with the shared file-based shipper.