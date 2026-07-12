## 1. System Overview

The system consists of three independent microservices communicating over HTTP:

- **market-data-service** – generates market data (equities, bonds, FX) and exposes it as an SSE stream and REST snapshots.
- **pricing-service** – subscribes to the stream from market-data-service, calculates fair values for financial instruments, and exposes them via REST API.
- **monitoring-service** – polls the `/health` endpoints of both services every second and reports their status.

---

## 2. Architecture

```
┌─────────────────────┐        SSE /stream         ┌──────────────────────┐
│  market-data-service│ ─────────────────────────> │   pricing-service    │
│      port 8001      │                            │      port 8002       │
└─────────────────────┘                            └──────────────────────┘
           ^                                                    ^
           │                                                    │
           │                                                    │
           │                                                    │
           │GET /health ┌────────────────────────┐ GET /health  │
           └──────────  │   monitoring-service   │──────────────┘
                        │       port 8003        │
                        └────────────────────────┘
```
Market data is generated in a single background thread every 100ms (3 events per tick: EQUITY, BOND, FX).
Each connected SSE client receives its own `queue.Queue` – fan-out happens at publish time.

---

## 3. Running the System

### Docker Compose (recommended)

```bash
cd homework-02-market-data-microservices
docker compose up --build
```

### Locally

```bash
# Install dependencies
pip install bottle

# Terminal 1
python market-data-service/app.py

# Terminal 2
python pricing-service/app.py

# Terminal 3
python monitoring-service/app.py
```

---

## 4. API Endpoints

### market-data-service (port 8001)

| Endpoint    | Method | Description |
|-------------|--------|-------------|
| `/health`   | GET    | Service status, number of generated events |
| `/snapshot` | GET    | Latest market data for ACME, GOVT_5Y, EURUSD |
| `/stream`   | GET    | Real-time SSE stream of market data events |

### pricing-service (port 8002)

| Endpoint                        | Method | Description |
|---------------------------------|--------|-------------|
| `/health`                       | GET    | Service status, stream connection status |
| `/valuations`                   | GET    | Fair values for all instruments |
| `/valuations/<instrument_id>`   | GET    | Fair value for a specific instrument (`EQ_ACME`, `BOND_GOVT_5Y`, `FX_EURUSD_1Y`) |

### monitoring-service (port 8003)

| Endpoint  | Method | Description |
|-----------|--------|-------------|
| `/health` | GET    | Monitoring service status |
| `/status` | GET    | Status of market-data-service and pricing-service with response times |

---

## 5. Inter-Service Communication

- **market-data-service → pricing-service**: one-way SSE stream (`text/event-stream`). pricing-service maintains a single long-lived HTTP connection and reads the response line by line. On disconnection it retries every 1 second.
- **monitoring-service → other services**: periodic HTTP GET requests every 1 second to the `/health` endpoint of each service.
- **URL configuration**: service addresses are passed via environment variables (`MARKET_DATA_URL`, `MARKET_DATA_HEALTH_URL`, `PRICING_HEALTH_URL`), enabling both local (localhost) and Docker Compose (DNS service names) deployments.

---

## 6. Streaming Mechanism – SSE (Server-Sent Events)

SSE is a one-directional HTTP protocol where the server pushes events to the client over a single long-lived connection.

Event format:
```
data: {"event_id": 1, "asset_type": "EQUITY", ...}\n\n
```

- Each event ends with a double `\n\n` (SSE event separator).
- If no data is available for 30 seconds, a heartbeat comment is sent: `: heartbeat\n\n`.
- The WSGI generator yields `bytes` (required by the WSGI standard).
- Each connected client has its own `queue.Queue` – data is pushed by the generator thread and consumed via `get(timeout=30)`.

---

## 7. Concurrency

### market-data-service

- `ThreadingWSGIServer` (`ThreadingMixIn + WSGIServer`) – each HTTP connection is handled in a separate thread, allowing multiple concurrent SSE connections.
- A separate `daemon=True` thread generates market data every 100ms.
- The shared `subscribers` list is protected by `threading.Lock`.

### pricing-service

- A separate `daemon=True` thread maintains the SSE connection to market-data-service and updates valuation state.
- The main thread handles HTTP requests (Bottle/wsgiref).
- Shared state (`latest_equity`, `latest_bond`, `latest_fx`) is protected by `threading.Lock`.

### monitoring-service

- Two separate `daemon=True` threads – one per monitored service – poll `/health` every 1 second independently.

---

## 8. Testing the System

After starting with `docker compose up --build`:

```bash
# Health checks
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Latest market data snapshot
curl http://localhost:8001/snapshot

# Instrument valuations
curl http://localhost:8002/valuations
curl http://localhost:8002/valuations/EQ_ACME
curl http://localhost:8002/valuations/BOND_GOVT_5Y
curl http://localhost:8002/valuations/FX_EURUSD_1Y

# Monitoring status
curl http://localhost:8003/status

# Watch the SSE stream (Ctrl+C to stop)
curl -N http://localhost:8001/stream
```

---

## 9. Implementation Challenges

| Problem | Solution |
|---------|----------|
| Single-threaded wsgiref blocked when an SSE connection was held open | Replaced with `ThreadingWSGIServer` (`ThreadingMixIn + WSGIServer`) |
| SSE generator was yielding `str` instead of `bytes` | Added `.encode('utf-8')` – WSGI requires bytes |
| `response.read()` blocked forever on SSE stream | Changed to `for line in response:` – line-by-line iteration |
| `urllib` returned 403 on Windows (corporate proxy) | Added `ProxyHandler({})` to force direct connections |
| Services could not reach each other in Docker | `host='localhost'` binds only the loopback inside the container – changed to `host='0.0.0.0'` |