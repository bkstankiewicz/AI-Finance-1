import { useMemo } from 'react'
import ColumnSettings from '../../components/ColumnSettings.jsx'
import DataTable from '../../components/DataTable.jsx'
import KpiCard from '../../components/KpiCard.jsx'
import Panel from '../../components/Panel.jsx'
import QueryNotice from '../../components/QueryNotice.jsx'
import DetailsList from '../../components/DetailsList.jsx'
import useColumnLayout from '../../hooks/useColumnLayout.js'
import usePolling from '../../hooks/usePolling.js'
import { getStats } from '../../api/tradeAction.js'
import { formatAge, formatDateTime, formatNumber, formatTime, secondsSince, shortId } from '../../utils/format.js'
import './TradeActionPage.scss'

const POLL_INTERVAL_MS = 2000

const outcomeClass = (row) => (row.outcome ? `outcome-cell outcome-cell--${row.outcome.toLowerCase()}` : '')

// client_request_id is "req-<uuid4>" - drop the prefix so shortId shows the unique part
const formatRef = (id) => shortId(String(id).replace(/^req-/, ''))
const formatMs = (ms) => `${formatNumber(ms, 1)} ms`
// action payload may hold nested objects (e.g. trade_metadata) or booleans React won't render
const formatValue = (value) => (typeof value === 'object' ? JSON.stringify(value) : String(value))

// Known fields of a recent action; any other action payload key appears under its raw name
const ACTION_FIELDS = {
  finished_at: { label: 'Processed At', format: formatTime },
  action_type: { label: 'Action' },
  entity_id: { label: 'Trade / Request Id', format: formatRef },
  symbol: { label: 'Symbol' },
  outcome: { label: 'Outcome', className: outcomeClass },
  wait_ms: { label: 'Queue Wait', format: formatMs },
  processing_ms: { label: 'Processing', format: formatMs },
  message: { label: 'Message' },
  trade_id: { label: 'Trade Id', format: shortId },
  client_request_id: { label: 'Request Id', format: formatRef },
  book_id: { label: 'Book Id', format: shortId },
}
const DEFAULT_ACTION_COLUMNS = ['finished_at', 'action_type', 'entity_id', 'symbol', 'outcome', 'wait_ms', 'processing_ms']
const DEFAULT_PINNED = ['finished_at']

const REJECTED_COLUMNS = [
  { key: 'finished_at', label: 'Datetime', format: formatDateTime },
  { key: 'entity_id', label: 'Trade / Request Id', format: formatRef },
  { key: 'outcome', label: 'Outcome', className: outcomeClass },
  { key: 'message', label: 'Message' },
]

const PERFORMANCE_FIELDS = [
  { key: 'avg_wait_ms', label: 'Avg queue wait', format: formatMs },
  { key: 'avg_processing_ms', label: 'Avg processing', format: formatMs },
  { key: 'max_processing_ms', label: 'Max processing', format: formatMs },
  { key: 'db_writes', label: 'DB writes (open + close)' },
  { key: 'outcomes', label: 'Outcomes', format: (o) => Object.entries(o).map(([k, v]) => `${k}: ${v}`).join(', ') || '—' },
  { key: 'started_at', label: 'Counting since', format: formatDateTime },
]

function RecentActionsTable({ rows, loading }) {
  // Columns = known fields + every key seen in the payloads (sorted, so the set id is stable between polls)
  const extraKeys = [...new Set(rows.flatMap(Object.keys))].filter((k) => !ACTION_FIELDS[k] && k !== 'seq').sort()
  const keysId = [...Object.keys(ACTION_FIELDS), ...extraKeys].join('|')
  const columns = useMemo(
    () => keysId.split('|').map((key) => ({ key, label: key, format: formatValue, ...ACTION_FIELDS[key] })),
    [keysId],
  )
  const layout = useColumnLayout('tradeAction.recentActions', columns, DEFAULT_ACTION_COLUMNS, DEFAULT_PINNED)

  return (
    <section className="section">
      <div className="section-toolbar">
        <h2>Recent Actions</h2>
        <ColumnSettings layout={layout} />
      </div>
      <DataTable
        columns={layout.columns}
        rows={rows}
        rowKey="seq"
        onMoveColumn={layout.move}
        loading={loading}
        emptyMessage="No actions processed yet"
      />
    </section>
  )
}

export default function TradeActionPage() {
  const { data: stats, error, updatedAt, loading } = usePolling(getStats, POLL_INTERVAL_MS)
  const down = Boolean(error)
  const failed = stats ? stats.rejected + stats.errors : undefined

  return (
    <>
      <QueryNotice what="processing stats" service="Trade Action Service" error={error} updatedAt={updatedAt} />

      <section className="kpis">
        <KpiCard label="Processed Actions" value={stats?.processed} hint="since service start" />
        <KpiCard label="Throughput" value={stats && `${formatNumber(stats.throughput_per_min, 0)} / min`} hint="last 60 s" />
        <KpiCard label="Avg Processing Time" value={stats?.avg_processing_ms != null ? formatMs(stats.avg_processing_ms) : undefined} />
        <KpiCard
          label="Queue Size"
          value={down ? 'N/A' : stats?.queue_size}
          tone={down ? 'down' : undefined}
          hint={stats?.avg_wait_ms != null && `avg wait ${formatMs(stats.avg_wait_ms)}`}
        />
        <KpiCard
          label="Errors"
          value={failed}
          tone={failed ? 'down' : undefined}
          hint={stats && `${stats.rejected} rejected, ${stats.errors} failed`}
        />
        <KpiCard
          label="Last DB Write"
          value={stats?.last_db_write_at ? formatAge(secondsSince(stats.last_db_write_at)) : undefined}
          hint={stats?.last_db_write_at && formatTime(stats.last_db_write_at)}
        />
      </section>

      <RecentActionsTable rows={stats?.recent_actions ?? []} loading={loading} />

      <div className="panels">
        <Panel title="Rejected / Failed Actions">
          <p className="muted">Counter: {failed ?? '—'}</p>
          <DataTable columns={REJECTED_COLUMNS} rows={stats?.recent_rejections ?? []} rowKey="seq" emptyMessage="No rejected actions" />
        </Panel>
        <Panel title="Performance">
          {stats && <DetailsList fields={PERFORMANCE_FIELDS} data={stats} />}
        </Panel>
      </div>
    </>
  )
}
