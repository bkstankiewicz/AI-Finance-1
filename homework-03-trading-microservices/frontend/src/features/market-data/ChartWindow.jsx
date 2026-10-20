import { memo, useMemo } from 'react'
import PopupWindow from '../../components/PopupWindow.jsx'
import StreamStatusBadge from '../../components/StreamStatusBadge.jsx'
import { plotValue, useMarketData, useMarketStream } from '../../context/MarketDataContext.jsx'
import PriceChart, { EmptyChartGrid } from './PriceChart.jsx'
import './ChartWindow.scss'

const isYield = (tick) => tick?.spot == null && tick?.yield != null

export default function ChartWindow({ session, onClosed, onFocus, onToggle }) {
  const { id, title, win, symbols } = session
  return (
    <PopupWindow win={win} title={title} onClosed={() => onClosed(id)} onFocus={() => onFocus(id)}>
      <ChartSessionView title={title} symbols={symbols} onToggle={onToggle} />
    </PopupWindow>
  )
}

function ChartSessionView({ title, symbols, onToggle }) {
  const { latest, history } = useMarketData()
  const { status } = useMarketStream()

  // Instrument set only grows and a symbol's asset class never changes, so the list is rebuilt only for new symbols
  const instrumentsId = Object.keys(latest).join('|')
  const available = useMemo(
    () =>
      Object.keys(latest)
        .filter((s) => !symbols.includes(s) && plotValue(latest[s]) !== undefined)
        .sort()
        .map((symbol) => ({ symbol, assetClass: latest[symbol].asset_class })),
    [instrumentsId, symbols],
  )

  return (
    <div className="chart-window">
      <header className="chart-window__header">
        <h1>{title}</h1>
        <StreamStatusBadge status={status} />
        <InstrumentPicker options={available} onPick={onToggle} />
      </header>

      {symbols.length === 0 ? (
        <EmptyChartGrid message="Click „Plot” in the main window or add an instrument above." />
      ) : (
        <div className="chart-window__grid">
          {symbols.map((symbol) => (
            <ChartTile key={symbol} symbol={symbol} tick={latest[symbol]} points={history[symbol]} onRemove={onToggle} />
          ))}
        </div>
      )}
    </div>
  )
}

const InstrumentPicker = memo(function InstrumentPicker({ options, onPick }) {
  return (
    <select
      className="input chart-window__add"
      value=""
      disabled={options.length === 0}
      onChange={(e) => e.target.value && onPick(e.target.value)}
    >
      <option value="">+ Add instrument…</option>
      {options.map(({ symbol, assetClass }) => (
        <option key={symbol} value={symbol}>
          {symbol} · {assetClass}
        </option>
      ))}
    </select>
  )
})

const EMPTY_POINTS = []

// Re-renders only when its own tick/history changes - other instruments ticking don't touch it
const ChartTile = memo(function ChartTile({ symbol, tick, points = EMPTY_POINTS, onRemove }) {
  const asPercent = isYield(tick)
  return (
    <article className="chart-window__item">
      <header className="chart-window__item-header">
        <strong>{symbol}</strong>
        <span className="muted">{tick?.asset_class}{asPercent && ' · yield'}</span>
        <span className="chart-window__price">
          {asPercent ? `${(tick.yield * 100).toFixed(3)}%` : tick?.spot}
        </span>
        <button className="btn chart-window__remove" title={`Remove ${symbol}`} onClick={() => onRemove(symbol)}>
          ×
        </button>
      </header>
      <PriceChart points={points} storageKey={`marketData.chart.${symbol}`} asPercent={asPercent} />
    </article>
  )
})
