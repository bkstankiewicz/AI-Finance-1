import DataTable from '../../components/DataTable.jsx'
import KpiCard from '../../components/KpiCard.jsx'
import Panel from '../../components/Panel.jsx'
import QueryNotice from '../../components/QueryNotice.jsx'
import usePolling from '../../hooks/usePolling.js'
import { useMarketData } from '../../context/MarketDataContext.jsx'
import { getRecentErrors } from '../../api/blotter.js'
import { getLatestValuation } from '../../api/pricing.js'
import { formatAge, formatTime, secondsSince } from '../../utils/format.js'

const POLL_INTERVAL_MS = 5000
const ERROR_WINDOW_MINUTES = 5
const STALE_AFTER_SECONDS = 60 // ticks come every ~10 s, DB valuations every ~10 s

const fetchRecentErrors = () => getRecentErrors(ERROR_WINDOW_MINUTES, 10)

const ERROR_COLUMNS = [
  { key: 'created_at', label: 'Time', format: formatTime },
  { key: 'service_name', label: 'Service' },
  { key: 'event_type', label: 'Event' },
  { key: 'message', label: 'Message' },
]

function TimestampCard({ label, timestamp }) {
  if (!timestamp) return <KpiCard label={label} />
  const age = secondsSince(timestamp)
  return (
    <KpiCard
      label={label}
      value={formatTime(timestamp)}
      hint={formatAge(age)}
      tone={age > STALE_AFTER_SECONDS ? 'down' : undefined}
    />
  )
}

// Errors from audit logs and data freshness - "is the pipeline alive?"
export default function DeveloperOverview() {
  const { latest } = useMarketData()
  const { data: errors, error: errorsError, updatedAt: errorsUpdatedAt } = usePolling(fetchRecentErrors, POLL_INTERVAL_MS)
  const { data: valuation } = usePolling(getLatestValuation, POLL_INTERVAL_MS)

  const lastTick = Object.values(latest)
    .map((tick) => tick.timestamp)
    .sort()
    .at(-1)

  return (
    <div className="panels">
      <Panel title={`Errors (last ${ERROR_WINDOW_MINUTES} min)`}>
        <QueryNotice what="errors" service="Blotter Service" error={errorsError} updatedAt={errorsUpdatedAt} />
        <div className="kpis">
          <KpiCard label="Error count" value={errors?.count} tone={errors?.count > 0 ? 'down' : undefined} />
        </div>
        {errors?.count > 0 && <DataTable columns={ERROR_COLUMNS} rows={errors.errors} rowKey="audit_id" />}
      </Panel>

      <Panel title="Timestamps">
        <div className="kpis">
          <TimestampCard label="Last market tick" timestamp={lastTick} />
          <TimestampCard label="Last valuation" timestamp={valuation?.valuation_time} />
        </div>
      </Panel>
    </div>
  )
}
