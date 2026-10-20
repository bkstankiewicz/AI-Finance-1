import { useCallback } from 'react'
import DataTable from '../../components/DataTable.jsx'
import DetailsList from '../../components/DetailsList.jsx'
import Panel from '../../components/Panel.jsx'
import QueryNotice from '../../components/QueryNotice.jsx'
import usePolling from '../../hooks/usePolling.js'
import { getTradeAuditLogs, getTradeDetails } from '../../api/blotter.js'
import { getTradeValuations } from '../../api/pricing.js'
import { formatAge, formatDateTime, formatNumber, secondsSince } from '../../utils/format.js'
import { formatPnl } from './formatPnl.jsx'

const DETAILS_POLL_MS = 10000
const HISTORY_LIMIT = 50

const TRADE_FIELDS = [
  { key: 'trade_id', label: 'Trade ID' },
  { key: 'book_name', label: 'Book' },
  { key: 'asset_class', label: 'Asset class' },
  { key: 'symbol', label: 'Symbol' },
  { key: 'side', label: 'Side' },
  { key: 'quantity', label: 'Quantity' },
  { key: 'trade_price', label: 'Trade price' },
  { key: 'status', label: 'Status' },
]

const LIVE_FIELDS = [
  { key: 'fair_value', label: 'Fair value', format: formatNumber },
  { key: 'unrealized_pnl', label: 'Unrealized PnL', format: formatPnl },
  { key: 'realized_pnl', label: 'Realized PnL', format: formatPnl },
  { key: 'total_pnl', label: 'Total PnL', format: formatPnl },
  { key: 'received_at', label: 'Updated', format: (v) => formatAge(secondsSince(v)) },
]

const HISTORY_COLUMNS = [
  { key: 'valuation_time', label: 'Time', format: formatDateTime },
  { key: 'fair_value', label: 'Fair Value', format: formatNumber },
  { key: 'unrealized_pnl', label: 'Unrealized', format: formatPnl },
  { key: 'realized_pnl', label: 'Realized', format: formatPnl },
  { key: 'total_pnl', label: 'Total', format: formatPnl },
]

const AUDIT_COLUMNS = [
  { key: 'created_at', label: 'Time', format: formatDateTime },
  { key: 'service_name', label: 'Service' },
  { key: 'event_type', label: 'Event' },
  { key: 'severity', label: 'Severity' },
  { key: 'message', label: 'Message' },
]

// Static trade data, valuation history and audit log come from the DB; the live valuation from SSE
export default function TradeDetails({ tradeId, row, live, isLive, bookNames, onClose }) {
  const fetchDetails = useCallback(
    () =>
      Promise.all([getTradeDetails(tradeId), getTradeValuations(tradeId, HISTORY_LIMIT), getTradeAuditLogs(tradeId)])
        .then(([details, valuations, auditLogs]) => ({ details, valuations, auditLogs })),
    [tradeId],
  )
  const { data, error, loading, updatedAt } = usePolling(fetchDetails, DETAILS_POLL_MS)

  // blotter returns { error } (HTTP 200) e.g. for trades without a cached valuation - fall back to the table row
  const trade = data?.details?.trade ?? row ?? { trade_id: tradeId }
  const tradeWithBook = { ...trade, book_name: bookNames[trade.book_id] ?? trade.book_id }
  const auditRows = (data?.auditLogs ?? []).map((log, index) => ({ ...log, key: index }))

  return (
    <>
      <div className="trade-details__header">
        <h2>Trade details</h2>
        <button className="btn" onClick={onClose}>Close</button>
      </div>
      <QueryNotice what="trade details" service="Blotter or Pricing Service" error={error} updatedAt={updatedAt} />

      <div className="panels">
        <Panel title="Trade">
          <DetailsList fields={TRADE_FIELDS} data={tradeWithBook} />
        </Panel>

        <Panel title="Live valuation">
          {!isLive && <p className="error">Live valuation stream unavailable – values below are not updating.</p>}
          {live
            ? <DetailsList fields={LIVE_FIELDS} data={live} />
            : <p className="muted">{isLive ? 'Waiting for the next valuation from the stream…' : 'No valuation received yet.'}</p>}
        </Panel>
      </div>

      <Panel title="Valuation history">
        <DataTable columns={HISTORY_COLUMNS} rows={data?.valuations ?? []} rowKey="valuation_id" loading={loading} emptyMessage="No valuations stored yet" />
      </Panel>

      <Panel title="Audit log">
        <DataTable columns={AUDIT_COLUMNS} rows={auditRows} rowKey="key" loading={loading} emptyMessage="No audit entries" />
      </Panel>
    </>
  )
}
