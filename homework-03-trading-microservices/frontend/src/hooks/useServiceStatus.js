import { useState } from 'react'
import useSseStream from './useSseStream.js'
import { openStatusStream } from '../api/monitoring.js'

export const MONITORING_SERVICE_ID = 'monitoring-service'

const SERVICES = [
  { id: 'market-data-service', label: 'Market Data' },
  { id: 'pricing-service', label: 'Pricing' },
  { id: MONITORING_SERVICE_ID, label: 'Monitoring' },
  { id: 'blotter-service', label: 'Blotter' },
  { id: 'books-service', label: 'Books' },
  { id: 'trade-action-service', label: 'Trade Action' },
  { id: 'trade-generation-service', label: 'Trade Generator' },
]

// Each SSE event is a full snapshot, so only the newest one in a batch matters
const STREAM_TO_STATUS = { CONNECTED: 'UP', STALE: 'DOWN', RECONNECTING: 'DOWN' }
const STALE_AFTER_MS = 10_000 // monitoring-service publishes every MONITORING_INTERVAL (1 s)

// services: [{ id, label, status, response_time_ms, ... }] for every known service
export default function useServiceStatus() {
  const [snapshot, setSnapshot] = useState({})
  const { status: streamStatus } = useSseStream(openStatusStream, {
    staleAfterMs: STALE_AFTER_MS,
    onEvents: (batch) => setSnapshot(batch.at(-1)),
  })

  // Without a live stream the last snapshot is stale, so show only monitoring-service itself
  const statuses = {
    ...(streamStatus === 'CONNECTED' ? snapshot : {}),
    [MONITORING_SERVICE_ID]: { status: STREAM_TO_STATUS[streamStatus] },
  }
  const services = SERVICES.map((service) => ({ ...service, ...statuses[service.id] }))
  return { services, streamStatus }
}
