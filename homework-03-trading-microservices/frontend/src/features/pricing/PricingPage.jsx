import { useState } from 'react'
import DataTable from '../../components/DataTable.jsx'
import StreamNotice from '../../components/StreamNotice.jsx'
import StreamStatusBadge from '../../components/StreamStatusBadge.jsx'
import { getTradeValuations } from '../../api/pricing.js'
import { formatDateTime, formatNumber, shortId } from '../../utils/format.js'
import useValuationStream from './useValuationStream.js'
import './PricingPage.scss'

// valuation_status is not returned by pricing-service yet; valuation_time only by GET /valuations
const valuationColumns = (renderTradeId) => [
  { key: 'asset_class', label: 'Asset Class' },
  { key: 'trade_id', label: 'Trade ID', render: renderTradeId },
  { key: 'book_id', label: 'Book ID', format: shortId },
  { key: 'fair_value', label: 'Fair Value', format: formatNumber },
  { key: 'realized_pnl', label: 'Realized PnL', format: formatNumber },
  { key: 'unrealized_pnl', label: 'Unrealized PnL', format: formatNumber },
  { key: 'valuation_status', label: 'Valuation Status' },
  { key: 'valuation_time', label: 'Created At', format: formatDateTime },
]

const SEARCH_COLUMNS = valuationColumns((row) => shortId(row.trade_id))

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export default function PricingPage() {
  const { latestBySymbol, status, lastEventAt } = useValuationStream()
  const [tradeId, setTradeId] = useState('')
  const [results, setResults] = useState(null)
  const [searchError, setSearchError] = useState(null)
  const [searching, setSearching] = useState(false)

  const search = async (id) => {
    setTradeId(id)
    setResults(null)
    if (!UUID_RE.test(id.trim())) {
      setSearchError('Trade ID must be a full UUID, e.g. 3f2b9c1e-0a4d-4b7e-9c2f-1d5e8a7b6c40.')
      return
    }
    setSearchError(null)
    setSearching(true)
    try {
      setResults(await getTradeValuations(id.trim()))
    } catch (err) {
      setSearchError(err.kind === 'unavailable' ? 'Pricing Service is down or unreachable.' : `Backend error: ${err.message}`)
    } finally {
      setSearching(false)
    }
  }

  const lastColumns = [
    { key: 'symbol', label: 'Symbol' },
    ...valuationColumns((row) => (
      <button className="btn btn--link" title="Search this trade" onClick={() => search(row.trade_id)}>
        {shortId(row.trade_id)}
      </button>
    )),
  ]
  const lastValuations = Object.values(latestBySymbol).sort((a, b) => a.symbol.localeCompare(b.symbol))

  return (
    <>
      <StreamNotice
        name="Live valuation stream"
        status={status}
        lastEventAt={lastEventAt}
        impact="Valuations below may be outdated (or there are no active trades to value)"
      />

      <section className="section">
        <h2>
          Last valuations
          <StreamStatusBadge status={status} />
        </h2>
        <DataTable
          columns={lastColumns}
          rows={lastValuations}
          rowKey="symbol"
          loading={status === 'CONNECTING'}
          emptyMessage="No valuations received yet"
        />
      </section>

      <section className="section">
        <form
          className="card valuation-search"
          onSubmit={(e) => {
            e.preventDefault()
            search(tradeId)
          }}
        >
          <input
            className={`input valuation-search__input${searchError ? ' input--invalid' : ''}`}
            placeholder="Search Valuation by Trade ID"
            aria-invalid={Boolean(searchError)}
            value={tradeId}
            onChange={(e) => setTradeId(e.target.value)}
          />
          <button className="btn btn--primary" disabled={!tradeId.trim() || searching}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        {searchError && <p className="error">{searchError}</p>}
        {results && (
          <DataTable columns={SEARCH_COLUMNS} rows={results} rowKey="valuation_id" emptyMessage="No valuations found for this trade" />
        )}
      </section>
    </>
  )
}
