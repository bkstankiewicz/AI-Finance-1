import KpiCard from '../../components/KpiCard.jsx'
import Panel from '../../components/Panel.jsx'
import QueryNotice from '../../components/QueryNotice.jsx'
import usePolling from '../../hooks/usePolling.js'
import { getBooksSummary } from '../../api/blotter.js'
import { formatNumber } from '../../utils/format.js'

const POLL_INTERVAL_MS = 5000

const sum = (rows, key) => rows?.reduce((total, row) => total + row[key], 0)
const pnlTone = (value) => (value < 0 ? 'down' : undefined)

// PnL and transaction totals, aggregated from the blotter's per-book summary
export default function BusinessOverview() {
  const { data: books, error, updatedAt } = usePolling(getBooksSummary, POLL_INTERVAL_MS)

  const unrealized = sum(books, 'unrealized_pnl')
  const realized = sum(books, 'realized_pnl')
  const format = (value) => (value === undefined ? null : formatNumber(value))

  return (
    <>
      <QueryNotice what="book summary" service="Blotter Service" error={error} updatedAt={updatedAt} />

      <div className="panels">
        <Panel title="P&L (USD)">
          <div className="kpis">
            <KpiCard label="Unrealized P&L" value={format(unrealized)} tone={pnlTone(unrealized)} />
            <KpiCard label="Realized P&L" value={format(realized)} tone={pnlTone(realized)} />
          </div>
        </Panel>

        <Panel title="Transactions">
          <div className="kpis">
            <KpiCard label="Active Trades" value={sum(books, 'active_trades')} />
            <KpiCard label="Books" value={books?.length} />
          </div>
        </Panel>
      </div>
    </>
  )
}
