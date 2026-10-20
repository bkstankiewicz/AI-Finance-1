import { useCallback, useMemo, useRef, useState } from 'react'
import ColumnSettings from '../../components/ColumnSettings.jsx'
import DataTable from '../../components/DataTable.jsx'
import Pagination, { pageCountOf } from '../../components/Pagination.jsx'
import PopupWindow from '../../components/PopupWindow.jsx'
import QueryNotice from '../../components/QueryNotice.jsx'
import StreamNotice from '../../components/StreamNotice.jsx'
import StreamStatusBadge from '../../components/StreamStatusBadge.jsx'
import TableFilters, { NoMatches } from '../../components/TableFilters.jsx'
import useColumnLayout from '../../hooks/useColumnLayout.js'
import usePersistentState from '../../hooks/usePersistentState.js'
import usePolling from '../../hooks/usePolling.js'
import useTableView from '../../hooks/useTableView.js'
import { getTrades } from '../../api/blotter.js'
import { ASSET_CLASSES } from '../../constants.js'
import { formatDateTime, formatNumber, shortId } from '../../utils/format.js'
import TradeDetails from './TradeDetails.jsx'
import './TradesWindow.scss'

const TRADES_POLL_MS = 5000 // only to pick up new/closed trades - values are overlaid live from SSE
const LIMIT_OPTIONS = [100, 500, 1000, 5000]
const PAGE_SIZE_OPTIONS = [25, 50, 100]

const TABS = [
  { key: 'ACTIVE', label: 'Active', status: 'ACTIVE' },
  { key: 'HISTORY', label: 'History', status: 'CLOSED' },
  { key: 'WATCHLIST', label: 'Watchlist' },
  { key: 'ALL', label: 'All' },
]

const OPEN_COLUMNS = ['watched', 'trade_date', 'book_id', 'asset_class', 'symbol', 'side', 'quantity', 'trade_price', 'trade_currency', 'status', 'fair_value', 'unrealized_pnl', 'total_pnl', 'details']
const DEFAULT_COLUMNS = {
  ACTIVE: OPEN_COLUMNS,
  HISTORY: ['watched', 'closed_at', 'book_id', 'asset_class', 'symbol', 'side', 'quantity', 'trade_price', 'close_price', 'realized_pnl', 'close_reason', 'settlement', 'details'],
  WATCHLIST: [...OPEN_COLUMNS.slice(0, -1), 'settlement', 'details'],
  ALL: [...OPEN_COLUMNS.slice(0, -1), 'settlement', 'details'],
}
const DEFAULT_PINNED = ['watched']
const DEFAULT_SORT = { key: 'trade_date', dir: 'desc' }

// Palette slot (--color-tag-N in _themes.scss) per asset class; a symbol keeps its asset class hue
// and only gets a stable shade (.tag-shade--N in TradesWindow.scss) from a hash
const TAG_SLOTS = 8
const TAG_SHADES = 4
const tagOf = (assetClass) => {
  const i = ASSET_CLASSES.indexOf(assetClass)
  return i === -1 ? TAG_SLOTS - 1 : i
}
const shadeOf = (text) => [...String(text)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7) % TAG_SHADES

const sideClass = (row) => `tag-cell side-cell--${String(row.side).toLowerCase()}`
const statusClass = (row) => `tag-cell status-cell--${String(row.status).toLowerCase()}`
const settlementClass = (row) => `tag-cell settlement-cell--${row.settlement.toLowerCase()}`
const pnlClass = (value) => (value > 0 ? 'is-up' : value < 0 ? 'is-down' : undefined)

const settlementOf = (trade) => (trade.is_settled ? 'SETTLED' : trade.status === 'CLOSED' ? 'PENDING' : 'OPEN')

// Row objects are reused while their trade, valuation and watch flag are unchanged, so DataTable skips them
function useTradeRows(trades, byTrade, watchSet) {
  const cache = useRef(new Map())
  return useMemo(() => {
    const next = new Map()
    const rows = trades.map((trade) => {
      const valuation = byTrade[trade.trade_id]
      const watched = watchSet.has(trade.trade_id)
      const hit = cache.current.get(trade.trade_id)
      const row =
        hit && hit.trade === trade && hit.valuation === valuation && hit.watched === watched
          ? hit.row
          : {
              ...trade,
              ...(valuation && {
                fair_value: valuation.fair_value,
                unrealized_pnl: valuation.unrealized_pnl,
                realized_pnl: valuation.realized_pnl,
                total_pnl: valuation.total_pnl,
              }),
              watched,
              settlement: settlementOf(trade),
            }
      next.set(trade.trade_id, { trade, valuation, watched, row })
      return row
    })
    cache.current = next
    return rows
  }, [trades, byTrade, watchSet])
}

export default function TradesWindow({ session, books, live, watchlist, onToggleWatch, onScopeChange, onClosed }) {
  const bookName = books.find((b) => b.book_id === session.bookId)?.name
  const title = `Trades – ${session.bookId ? bookName ?? shortId(session.bookId) : 'All books'}`
  return (
    <PopupWindow win={session.win} title={title} onClosed={onClosed}>
      <TradesView
        title={title}
        bookId={session.bookId}
        books={books}
        live={live}
        watchlist={watchlist}
        onToggleWatch={onToggleWatch}
        onScopeChange={onScopeChange}
      />
    </PopupWindow>
  )
}

function TradesView({ title, bookId, books, live, watchlist, onToggleWatch, onScopeChange }) {
  const [tab, setTab] = useState('ACTIVE')
  const [limit, setLimit] = usePersistentState('blotter.trades.limit', 500)
  const [selected, setSelected] = useState(null) // row snapshot - details of closed trades fall back to it
  const bookNames = Object.fromEntries(books.map((book) => [book.book_id, book.name]))

  return (
    <div className="trades-window">
      <header className="trades-window__header">
        <h1>{title}</h1>
        <StreamStatusBadge status={live.status} />
        <label className="trades-window__control">
          Scope
          <select className="input" value={bookId} onChange={(e) => onScopeChange(e.target.value)}>
            <option value="">All books</option>
            {books.map((book) => <option key={book.book_id} value={book.book_id}>{book.name}</option>)}
          </select>
        </label>
        <label className="trades-window__control">
          Load latest
          <select className="input" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            {LIMIT_OPTIONS.map((n) => <option key={n} value={n}>{n} trades</option>)}
          </select>
        </label>
      </header>

      <div className="trades-window__tabs" role="tablist" aria-label="Trade list">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            role="tab"
            className={key === tab ? 'btn btn--primary' : 'btn'}
            aria-selected={key === tab}
            onClick={() => setTab(key)}
          >
            {label}
            {key === 'WATCHLIST' && watchlist.length > 0 && <span className="trades-window__count">{watchlist.length}</span>}
          </button>
        ))}
      </div>

      <TradesTable
        key={`${tab}|${bookId}`}
        tab={tab}
        bookId={bookId}
        limit={limit}
        bookNames={bookNames}
        live={live}
        watchlist={watchlist}
        onSelect={setSelected}
        onToggleWatch={onToggleWatch}
      />

      {selected && (
        <TradeDetails
          key={selected.trade_id}
          tradeId={selected.trade_id}
          row={selected}
          live={live.byTrade[selected.trade_id]}
          isLive={live.status === 'CONNECTED' || live.status === 'CONNECTING'}
          bookNames={bookNames}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}

// Remounted per tab + scope (key), so each keeps its own column layout, sort and filters
function TradesTable({ tab, bookId, limit, bookNames, live, watchlist, onSelect, onToggleWatch }) {
  const [pageSize, setPageSize] = usePersistentState('blotter.trades.pageSize', PAGE_SIZE_OPTIONS[0])
  const [page, setPage] = useState(1)
  const storageKey = `blotter.trades.${tab}`
  const status = TABS.find((t) => t.key === tab).status
  const watchedIds = tab === 'WATCHLIST' ? watchlist.join('|') : ''

  const fetchTrades = useCallback(() => {
    if (tab !== 'WATCHLIST') return getTrades({ limit, book_id: bookId, status })
    const ids = watchedIds ? watchedIds.split('|') : []
    return ids.length ? getTrades({ limit: ids.length, book_id: bookId, trade_id: ids }) : Promise.resolve([])
  }, [tab, bookId, limit, status, watchedIds])
  const trades = usePolling(fetchTrades, TRADES_POLL_MS)

  const watchSet = useMemo(() => new Set(watchlist), [watchlist])
  const rows = useTradeRows(trades.data ?? [], live.byTrade, watchSet)

  // Silence is expected when nothing is open, so STALE only counts while there are active trades to value
  const hasActive = rows.some((row) => row.status === 'ACTIVE')
  const streamStatus = live.status === 'STALE' && !hasActive ? 'CONNECTED' : live.status
  const isLive = streamStatus === 'CONNECTED' || streamStatus === 'CONNECTING'

  const bookNamesId = JSON.stringify(bookNames)
  const columns = useMemo(() => {
    const liveCell = (value) => (isLive ? pnlClass(value) : 'is-stale')
    return [
      {
        key: 'watched',
        label: '★',
        sortable: true,
        value: (row) => (row.watched ? 1 : 0),
        className: 'watch-cell',
        render: (row) => (
          <button
            className={row.watched ? 'watch-btn is-active' : 'watch-btn'}
            aria-pressed={row.watched}
            title={row.watched ? 'Remove from watchlist' : 'Add to watchlist'}
            onClick={() => onToggleWatch(row.trade_id)}
          >
            {row.watched ? '★' : '☆'}
          </button>
        ),
      },
      { key: 'trade_date', label: 'Date/Time', format: formatDateTime, sortable: true },
      { key: 'trade_id', label: 'Trade', format: shortId, sortable: true, filter: 'prefix' },
      { key: 'book_id', label: 'Book', format: (id) => bookNames[id] ?? shortId(id), value: (row) => bookNames[row.book_id] ?? row.book_id, sortable: true, filter: 'text' },
      { key: 'asset_class', label: 'Asset Class', sortable: true, filter: 'prefix', className: (row) => `tint-cell tag-color--${tagOf(row.asset_class)}` },
      { key: 'symbol', label: 'Symbol', sortable: true, filter: 'text', className: (row) => `symbol-cell tag-color--${tagOf(row.asset_class)} tag-shade--${shadeOf(row.symbol)}` },
      { key: 'side', label: 'Side', sortable: true, filter: 'prefix', className: sideClass },
      { key: 'quantity', label: 'Qty', sortable: true, className: 'num-cell' },
      { key: 'trade_price', label: 'Trade Price', sortable: true, className: 'num-cell' },
      { key: 'trade_currency', label: 'Ccy', sortable: true },
      { key: 'status', label: 'Status', sortable: true, filter: 'prefix', className: statusClass },
      { key: 'fair_value', label: 'Fair Value', format: formatNumber, sortable: true, className: isLive ? 'num-cell' : 'num-cell is-stale' },
      { key: 'unrealized_pnl', label: 'Unrealized', format: formatNumber, sortable: true, className: (row) => `num-cell ${liveCell(row.unrealized_pnl) ?? ''}` },
      { key: 'realized_pnl', label: 'Realized', format: formatNumber, sortable: true, className: (row) => `num-cell ${pnlClass(row.realized_pnl) ?? ''}` },
      { key: 'total_pnl', label: 'Total PnL', format: formatNumber, sortable: true, className: (row) => `num-cell ${liveCell(row.total_pnl) ?? ''}` },
      { key: 'close_price', label: 'Close Price', sortable: true, className: 'num-cell' },
      { key: 'closed_at', label: 'Closed At', format: formatDateTime, sortable: true },
      { key: 'close_reason', label: 'Close Reason', sortable: true },
      { key: 'settlement', label: 'Settlement', sortable: true, className: settlementClass },
      {
        key: 'details',
        label: 'Details',
        render: (row) => (
          <button className="btn" onClick={() => onSelect(row)}>Details</button>
        ),
      },
    ]
  }, [isLive, bookNamesId, onToggleWatch, onSelect])

  const layout = useColumnLayout(storageKey, columns, DEFAULT_COLUMNS[tab], DEFAULT_PINNED)
  const view = useTableView(storageKey, layout.columns, rows, DEFAULT_SORT)

  // Another filter = another result set, so start from its first page
  const setFilters = (next) => {
    view.setFilters(next)
    setPage(1)
  }

  // Clamp, because a refresh can shrink the list below the current page
  const current = Math.min(page, pageCountOf(view.rows.length, pageSize))
  const pageRows = view.rows.slice((current - 1) * pageSize, current * pageSize)
  const hasFilters = Object.values(view.filters).some(Boolean)

  return (
    <>
      <StreamNotice
        name="Live valuation stream"
        status={streamStatus}
        lastEventAt={live.lastEventAt}
        impact="Fair value and PnL are NOT updating – highlighted values are the last known ones"
      />
      <div className="trades-window__toolbar">
        <TableFilters columns={layout.columns} filters={view.filters} onChange={setFilters} />
        <label className="trades-window__control">
          Rows per page
          <select
            className="input"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value))
              setPage(1)
            }}
          >
            {PAGE_SIZE_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <ColumnSettings layout={layout} />
      </div>
      <QueryNotice what="trades" service="Blotter Service" error={trades.error} updatedAt={trades.updatedAt} />
      <DataTable
        columns={layout.columns}
        rows={pageRows}
        rowKey="trade_id"
        sort={view.sort}
        onSort={view.toggleSort}
        onMoveColumn={layout.move}
        loading={trades.loading}
        footer={
          view.rows.length > 0 && (
            <Pagination page={current} pageSize={pageSize} total={view.rows.length} onChange={setPage} />
          )
        }
        emptyMessage={
          trades.error ? 'Trades unavailable'
            : hasFilters && rows.length > 0 ? <NoMatches onClear={() => setFilters({})} />
              : tab === 'WATCHLIST' ? 'Watchlist is empty – mark trades with ☆ to follow them here.'
                : tab === 'HISTORY' ? 'No closed trades yet.'
                  : 'No trades yet. Start the generator in the Trade Generation view.'
        }
      />
      <p className="muted">
        {tab === 'WATCHLIST'
          ? `${watchlist.length} trades on the watchlist (shared by all trade windows). `
          : `Showing up to the ${limit} most recent ${status ? status.toLowerCase() + ' ' : ''}trades. `}
        {isLive
          ? 'Fair value and PnL update live from the valuation stream.'
          : 'Live valuation is unavailable – fair value and PnL are frozen at their last known values.'}
      </p>
    </>
  )
}
