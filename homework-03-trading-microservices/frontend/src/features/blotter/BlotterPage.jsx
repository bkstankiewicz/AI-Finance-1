import ColumnSettings from '../../components/ColumnSettings.jsx'
import DataTable from '../../components/DataTable.jsx'
import QueryNotice from '../../components/QueryNotice.jsx'
import StreamNotice from '../../components/StreamNotice.jsx'
import StreamStatusBadge from '../../components/StreamStatusBadge.jsx'
import { NoMatches } from '../../components/TableFilters.jsx'
import useColumnLayout from '../../hooks/useColumnLayout.js'
import usePersistentState from '../../hooks/usePersistentState.js'
import usePolling from '../../hooks/usePolling.js'
import useTableView from '../../hooks/useTableView.js'
import { getBooksSummary } from '../../api/blotter.js'
import { ASSET_CLASSES } from '../../constants.js'
import { formatNumber, shortId } from '../../utils/format.js'
import { useBlotterSessions } from './BlotterSessions.jsx'
import { formatPnl } from './formatPnl.jsx'
import useLiveValuations from './useLiveValuations.js'
import './BlotterPage.scss'

const BOOKS_POLL_MS = 5000
const STORAGE_KEY = 'blotter.books'
const DEFAULT_COLUMNS = ['name', 'expected_asset_class', 'active_trades', 'realized_pnl', 'unrealized_pnl', 'total_pnl', 'alpha', 'beta', 'trades']
const DEFAULT_PINNED = ['name']
const EMPTY_FILTERS = { bookId: '', assetClass: '' }

function BookFilters({ books, filters, onChange }) {
  const setFilter = (key, value) => onChange({ ...filters, [key]: value })
  const isEmpty = !filters.bookId && !filters.assetClass

  return (
    <div className="blotter-filters">
      <label>
        Book
        <select className="input" value={filters.bookId} onChange={(e) => setFilter('bookId', e.target.value)}>
          <option value="">All books</option>
          {books.map((book) => <option key={book.book_id} value={book.book_id}>{book.name}</option>)}
        </select>
      </label>
      <label>
        Asset class
        <select className="input" value={filters.assetClass} onChange={(e) => setFilter('assetClass', e.target.value)}>
          <option value="">All asset classes</option>
          {ASSET_CLASSES.map((assetClass) => <option key={assetClass}>{assetClass}</option>)}
        </select>
      </label>
      <button className="btn" disabled={isEmpty} onClick={() => onChange(EMPTY_FILTERS)}>Clear filters</button>
    </div>
  )
}

// Book unrealized PnL is live once every active trade of the book has a streamed valuation;
// until then (first seconds after opening) the DB aggregate from /books/summary is shown.
function withLiveBookPnl(books, liveByTrade) {
  const live = {}
  for (const v of Object.values(liveByTrade)) {
    const agg = (live[v.book_id] ??= { count: 0, unrealized: 0 })
    agg.count += 1
    agg.unrealized += v.unrealized_pnl
  }
  return books.map((book) => {
    const agg = live[book.book_id]
    const isLive = Boolean(agg) && agg.count >= book.active_trades
    const unrealized = isLive ? agg.unrealized : book.unrealized_pnl
    return { ...book, unrealized_pnl: unrealized, total_pnl: book.realized_pnl + unrealized }
  })
}

// Trades are browsed in micro-session windows (TradesWindow) - one per book or for all books
export default function BlotterPage() {
  const { byTrade, status: streamStatus, lastEventAt } = useLiveValuations()
  const books = usePolling(getBooksSummary, BOOKS_POLL_MS)
  const { sessions, blocked, openSession } = useBlotterSessions()
  const [savedFilters, setFilters] = usePersistentState(`${STORAGE_KEY}.selection`, EMPTY_FILTERS)

  const bookRows = withLiveBookPnl(books.data ?? [], byTrade)
  const openScopes = new Set(sessions.map((s) => s.bookId))

  // Silence is expected when nothing is open, so STALE only counts while there are active trades to value
  const hasActiveTrades = bookRows.some((book) => book.active_trades > 0)
  const status = streamStatus === 'STALE' && !hasActiveTrades ? 'CONNECTED' : streamStatus
  const isLive = status === 'CONNECTED' || status === 'CONNECTING'
  const liveCell = isLive ? undefined : 'is-stale'

  // alpha / beta are not returned by blotter-service yet - shown as "—" until they are
  const bookColumns = [
    { key: 'name', label: 'Book', sortable: true },
    { key: 'book_id', label: 'Book ID', format: shortId, sortable: true },
    { key: 'expected_asset_class', label: 'Asset Class', sortable: true },
    { key: 'active_trades', label: 'Active Trades', sortable: true },
    { key: 'realized_pnl', label: 'Realized PnL', format: formatPnl, sortable: true },
    { key: 'unrealized_pnl', label: 'Unrealized PnL', format: formatPnl, className: liveCell, sortable: true },
    { key: 'total_pnl', label: 'Total PnL', format: formatPnl, className: liveCell, sortable: true },
    { key: 'currency', label: 'Ccy', sortable: true },
    { key: 'alpha', label: 'Alpha', format: (v) => formatNumber(v, 4), sortable: true },
    { key: 'beta', label: 'Beta', format: (v) => formatNumber(v, 2), sortable: true },
    {
      key: 'trades',
      label: 'Trades',
      render: (row) => (
        <button
          className={openScopes.has(row.book_id) ? 'btn btn--primary' : 'btn'}
          title={openScopes.has(row.book_id) ? 'Focus the open trades window' : 'Open trades in a new window'}
          onClick={() => openSession(row.book_id)}
        >
          Trades
        </button>
      ),
    },
  ]

  // A remembered book may have been deleted since - then it no longer filters anything
  const bookId = bookRows.some((book) => book.book_id === savedFilters.bookId) ? savedFilters.bookId : ''
  const filters = { bookId, assetClass: savedFilters.assetClass ?? '' }
  const filteredRows = bookRows.filter(
    (book) =>
      (!filters.bookId || book.book_id === filters.bookId) &&
      (!filters.assetClass || book.expected_asset_class === filters.assetClass),
  )

  const layout = useColumnLayout(STORAGE_KEY, bookColumns, DEFAULT_COLUMNS, DEFAULT_PINNED)
  const view = useTableView(STORAGE_KEY, layout.columns, filteredRows)
  const hasFilters = Boolean(filters.bookId || filters.assetClass)

  return (
    <>
      <StreamNotice
        name="Live valuation stream"
        status={status}
        lastEventAt={lastEventAt}
        impact="PnL is NOT updating – highlighted values are the last known ones"
      />

      <section className="section">
        <div className="blotter-toolbar">
          <h2>
            Books
            <StreamStatusBadge status={status} />
          </h2>
          <button className={openScopes.has('') ? 'btn btn--primary' : 'btn'} onClick={() => openSession('')}>
            All trades
          </button>
        </div>
        {blocked && <p className="error">Popup blocked – allow popups for this site to open trade windows.</p>}
        <div className="blotter-toolbar blotter-toolbar--filters">
          <BookFilters books={books.data ?? []} filters={filters} onChange={setFilters} />
          <ColumnSettings layout={layout} />
        </div>
        <QueryNotice what="books" service="Blotter Service" error={books.error} updatedAt={books.updatedAt} />
        <DataTable
          columns={layout.columns}
          rows={view.rows}
          rowKey="book_id"
          sort={view.sort}
          onSort={view.toggleSort}
          onMoveColumn={layout.move}
          loading={books.loading}
          emptyMessage={
            books.error ? 'Books unavailable'
              : hasFilters && bookRows.length > 0 ? <NoMatches onClear={() => setFilters(EMPTY_FILTERS)} />
                : 'No books yet. Create one in the Books view.'
          }
        />
        <p className="muted">„Trades” opens the book's trades in a separate window (active, history, watchlist).</p>
      </section>
    </>
  )
}
