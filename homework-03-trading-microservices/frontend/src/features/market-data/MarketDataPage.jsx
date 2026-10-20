import { useMemo, useRef } from 'react'
import ColumnSettings from '../../components/ColumnSettings.jsx'
import DataTable from '../../components/DataTable.jsx'
import StreamNotice from '../../components/StreamNotice.jsx'
import StreamStatusBadge from '../../components/StreamStatusBadge.jsx'
import TableFilters, { NoMatches } from '../../components/TableFilters.jsx'
import { plotValue, useMarketData, useMarketStream } from '../../context/MarketDataContext.jsx'
import useColumnLayout from '../../hooks/useColumnLayout.js'
import usePersistentState from '../../hooks/usePersistentState.js'
import useTableView from '../../hooks/useTableView.js'
import { useChartSessions } from './ChartSessions.jsx'
import './MarketDataPage.scss'

const ALL = 'ALL'

// Tab order; asset classes not listed here (new generators) follow alphabetically
const CLASS_ORDER = ['EQUITY', 'FOREX', 'COMMODITY', 'FUTURES', 'FIXED_INCOME', 'EUROPEAN_OPTION']

const timeOfDay = (v) => String(v).slice(11, 23)
const percent = (digits) => (v) => `${(v * 100).toFixed(digits)}%`
// `last` / `last_yield` in a tick are the previous values (see market-data-service generator.py)
const moveClass = (current, previous) => (row) =>
  row[current] > row[previous] ? 'is-up' : row[current] < row[previous] ? 'is-down' : undefined

// Labels/formats of known tick fields (tick = raw_payload in DB); unknown fields still show up under their raw key
const FIELDS = {
  symbol: { label: 'Symbol', filter: 'text' },
  asset_class: { label: 'Asset Class', filter: 'text' },
  timestamp: { label: 'Timestamp', format: timeOfDay },
  bid: { label: 'Bid' },
  ask: { label: 'Ask' },
  mid: { label: 'Mid' },
  spot: { label: 'Spot', className: moveClass('spot', 'last') },
  last: { label: 'Last' },
  yield: { label: 'Yield', format: percent(3), className: moveClass('yield', 'last_yield') },
  last_yield: { label: 'Last Yield', format: percent(3) },
  face_value: { label: 'Face Value' },
  domestic_rate: { label: 'Domestic Rate', format: percent(2) },
  foreign_rate: { label: 'Foreign Rate', format: percent(2) },
  underlying_symbol: { label: 'Underlying' },
  volatility: { label: 'Volatility', format: percent(2) },
  dividend_yield: { label: 'Dividend Yield', format: percent(2) },
  currency: { label: 'Currency' },
  event_id: { label: 'Event ID' },
  snapshot_type: { label: 'Snapshot Type' },
  snapshot_time: { label: 'Snapshot Time', format: timeOfDay },
}

// What matters per asset class: bonds are quoted by yield, options by vol - not by bid/ask
const PRICE_COLUMNS = ['symbol', 'timestamp', 'bid', 'ask', 'mid', 'spot', 'last', 'currency', 'received', 'plot']
const DEFAULT_COLUMNS = {
  EQUITY: PRICE_COLUMNS,
  COMMODITY: PRICE_COLUMNS,
  FUTURES: PRICE_COLUMNS,
  FOREX: [...PRICE_COLUMNS, 'domestic_rate', 'foreign_rate'],
  FIXED_INCOME: ['symbol', 'timestamp', 'yield', 'last_yield', 'face_value', 'currency', 'received', 'plot'],
  EUROPEAN_OPTION: ['symbol', 'timestamp', 'underlying_symbol', 'volatility', 'dividend_yield', 'received'],
  [ALL]: ['symbol', 'asset_class', 'timestamp', 'mid', 'spot', 'yield', 'volatility', 'received', 'plot'],
}
const DEFAULT_PINNED = ['symbol']
const FALLBACK_COLUMNS = Object.keys(FIELDS).concat('received')

const classLabel = (assetClass) =>
  assetClass === ALL ? 'All' : assetClass.toLowerCase().split('_').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ')

const byClassOrder = (a, b) => {
  const rank = (c) => (CLASS_ORDER.includes(c) ? CLASS_ORDER.indexOf(c) : CLASS_ORDER.length)
  return rank(a) - rank(b) || a.localeCompare(b)
}

// Remounted per asset class (key), so persisted sort/filters/layout are read for that class
function TicksTable({ assetClass, ticks, received, loading }) {
  const { active, blocked, openSession, plot } = useChartSessions()
  const defaults = DEFAULT_COLUMNS[assetClass] ?? FALLBACK_COLUMNS
  const present = new Set([...defaults, ...ticks.flatMap((tick) => Object.keys(tick))])
  const keys = [...Object.keys(FIELDS).filter((k) => present.has(k)), ...[...present].filter((k) => !FIELDS[k])]
  const keysId = keys.join('|')

  // Row objects are reused until their tick or received count changes, so unchanged rows skip re-rendering
  const rowCache = useRef(new Map())
  const rows = ticks.map((tick) => {
    const count = received[tick.symbol] ?? 0
    const cached = rowCache.current.get(tick.symbol)
    if (cached?.tick === tick && cached.row.received === count) return cached.row
    const row = { ...tick, received: count }
    rowCache.current.set(tick.symbol, { tick, row })
    return row
  })

  // Rebuilt only when the column set or the active chart window changes - not per tick
  const columns = useMemo(() => {
    const plotColumn = {
      key: 'plot',
      label: 'Plot',
      // Charts plot spot (bonds: yield) - options have nothing to plot
      render: (row) => {
        if (plotValue(row) === undefined) return '—'
        const isPlotted = active?.symbols.includes(row.symbol) ?? false
        return (
          <button
            className={isPlotted ? 'btn btn--accent' : 'btn'}
            aria-pressed={isPlotted}
            title={`${active ? `Toggle in ${active.title}` : 'Open in a new chart window'} (Shift+click: new window)`}
            onClick={(e) => (e.shiftKey ? openSession([row.symbol]) : plot(row.symbol))}
          >
            {isPlotted ? 'Hide' : 'Plot'}
          </button>
        )
      },
    }
    return keysId.split('|').map((key) =>
      key === 'plot'
        ? plotColumn
        : key === 'received'
        ? { key, label: 'Received', sortable: true }
        : { key, label: key, sortable: true, ...FIELDS[key] },
    )
  }, [keysId, active, openSession, plot])

  const storageKey = `marketData.ticks.${assetClass}`
  const layout = useColumnLayout(storageKey, columns, defaults, DEFAULT_PINNED)
  const table = useTableView(storageKey, layout.columns, rows, { key: 'symbol', dir: 'asc' })
  const hasFilters = Object.values(table.filters).some(Boolean)

  return (
    <>
      <div className="ticks-toolbar">
        <TableFilters columns={layout.columns} filters={table.filters} onChange={table.setFilters} />
        <ColumnSettings layout={layout} />
      </div>
      {blocked && <p className="error">Popup blocked – allow popups for this site to open chart windows.</p>}
      <DataTable
        columns={layout.columns}
        rows={table.rows}
        rowKey="symbol"
        sort={table.sort}
        onSort={table.toggleSort}
        onMoveColumn={layout.move}
        loading={loading}
        emptyMessage={ticks.length && hasFilters ? <NoMatches onClear={() => table.setFilters({})} /> : 'No ticks received yet'}
      />
    </>
  )
}

export default function MarketDataPage() {
  const { latest, received } = useMarketData()
  const { status, lastEventAt } = useMarketStream()
  const [savedClass, setSavedClass] = usePersistentState('marketData.assetClass', null)
  const totalReceived = Object.values(received).reduce((sum, n) => sum + n, 0)

  const allTicks = Object.values(latest)
  const classes = [...new Set(allTicks.map((tick) => tick.asset_class))].sort(byClassOrder)
  const tabs = classes.length ? [...classes, ALL] : []
  // Saved tab is kept while ticks are still loading; one asset class at a time by default
  const assetClass = tabs.includes(savedClass) ? savedClass : (tabs[0] ?? savedClass ?? ALL)
  const ticks = assetClass === ALL ? allTicks : allTicks.filter((tick) => tick.asset_class === assetClass)

  return (
    <>
      <StreamNotice
        name="Market data stream"
        status={status}
        lastEventAt={lastEventAt}
        impact="Prices and charts are not updating"
      />

      <section className="section">
        <h2>
          Last Generated Ticks
          <StreamStatusBadge status={status} />
          <span className="muted" title="Ticks received by this browser over the live stream since app load">
            {totalReceived.toLocaleString()} ticks received
          </span>
        </h2>
        {tabs.length > 0 && (
          <div className="asset-tabs" role="tablist" aria-label="Asset class">
            {tabs.map((name) => (
              <button
                key={name}
                role="tab"
                className={name === assetClass ? 'btn btn--primary' : 'btn'}
                aria-selected={name === assetClass}
                onClick={() => setSavedClass(name)}
              >
                {classLabel(name)}
              </button>
            ))}
          </div>
        )}
        <TicksTable
          key={assetClass}
          assetClass={assetClass}
          ticks={ticks}
          received={received}
          loading={status === 'CONNECTING'}
        />
      </section>
    </>
  )
}
