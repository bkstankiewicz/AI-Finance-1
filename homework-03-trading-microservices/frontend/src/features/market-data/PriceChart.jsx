import { useRef, useState } from 'react'
import usePersistentState from '../../hooks/usePersistentState.js'
import './PriceChart.scss'

const X_WINDOWS = [50, 100, 250, 500] // number of last ticks shown
const Y_TICK_COUNT = 5
const X_TICK_COUNT = 6
const Y_PADDING = 0.05 // 5% empty space above max and below min
const Y_DRAG_THRESHOLD_PX = 6 // ignore vertical jitter while dragging sideways

// Round step to 1/2/5 x 10^n, so axis labels are "nice" numbers
function niceStep(range, count) {
  const raw = range / count
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const normalized = raw / magnitude
  const nice = normalized < 1.5 ? 1 : normalized < 3 ? 2 : normalized < 7 ? 5 : 10
  return nice * magnitude
}

const EMPTY_GRID = [0, 25, 50, 75, 100]

// Axes + dashed grid without data, so the chart area keeps its shape
export function EmptyChartGrid({ message }) {
  return (
    <div className="price-chart__body">
      <div className="price-chart__y-axis" />
      <svg className="price-chart__plot price-chart__plot--empty" viewBox="0 0 100 100" preserveAspectRatio="none">
        {EMPTY_GRID.map((v) => (
          <g key={v}>
            <line x1="0" x2="100" y1={v} y2={v} vectorEffect="non-scaling-stroke" />
            <line x1={v} x2={v} y1="0" y2="100" vectorEffect="non-scaling-stroke" />
          </g>
        ))}
      </svg>
      <div className="price-chart__empty">{message}</div>
      <div className="price-chart__x-axis" />
    </div>
  )
}

// asPercent: values are fractions (e.g. bond yield 0.043) shown on the Y axis as 4.30%
export default function PriceChart({ points, storageKey = 'priceChart', asPercent = false }) {
  const [windowSize, setWindowSize] = usePersistentState(`${storageKey}.window`, 100)
  const [yZoom, setYZoom] = useState(1) // 1 = auto-fit, >1 zoom in, <1 zoom out
  const [endSeq, setEndSeq] = useState(null) // seq of the rightmost point; null = follow live data
  const [yCenter, setYCenter] = useState(null) // null = center on visible prices
  const drag = useRef(null)

  // seq values have gaps (event ids are shared across symbols), so pan by array index
  const lastIndex = points.length - 1
  const minEndIndex = Math.min(lastIndex, windowSize - 1)
  const anchoredIndex = endSeq === null ? lastIndex : points.findLastIndex((p) => p.seq <= endSeq)
  const endIndex = Math.max(anchoredIndex, minEndIndex)
  const visible = points.slice(Math.max(0, endIndex - windowSize + 1), endIndex + 1)

  const controls = (
    <div className="price-chart__controls">
      <span className="price-chart__axis-name">X</span>
      {X_WINDOWS.map((n) => (
        <button key={n} className={n === windowSize ? 'btn btn--primary' : 'btn'} onClick={() => setWindowSize(n)}>
          {n}
        </button>
      ))}
      <button className="btn" disabled={endSeq === null} onClick={() => setEndSeq(null)}>Live</button>
      <span className="price-chart__axis-name">Y</span>
      <button className="btn" title="Zoom out" onClick={() => setYZoom((z) => z / 2)}>−</button>
      <button className="btn" title="Zoom in" onClick={() => setYZoom((z) => z * 2)}>+</button>
      <button
        className="btn"
        disabled={yZoom === 1 && yCenter === null}
        onClick={() => {
          setYZoom(1)
          setYCenter(null)
        }}
      >
        Auto
      </button>
    </div>
  )

  if (visible.length < 2) {
    return (
      <div className="price-chart">
        {controls}
        <EmptyChartGrid message="Waiting for data..." />
      </div>
    )
  }

  // Y domain: fit visible prices, then scale by yZoom around yCenter (or the auto middle)
  const prices = visible.map((p) => p.price)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const mid = yCenter ?? (min + max) / 2
  const span = ((max - min || Math.abs(mid) * 0.001 || 1) * (1 + 2 * Y_PADDING)) / yZoom
  const yMin = mid - span / 2
  const yMax = mid + span / 2

  // Drag right = go back in time, drag down = look at higher prices
  const handlePointerDown = (e) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    drag.current = { x: e.clientX, y: e.clientY, endIndex, mid }
  }

  const handlePointerMove = (e) => {
    if (!drag.current) return
    const rect = e.currentTarget.getBoundingClientRect()
    const dx = e.clientX - drag.current.x
    const dy = e.clientY - drag.current.y

    const shift = Math.round((dx / rect.width) * (visible.length - 1))
    const newIndex = Math.min(lastIndex, Math.max(minEndIndex, drag.current.endIndex - shift))
    setEndSeq(newIndex >= lastIndex ? null : points[newIndex].seq)

    if (Math.abs(dy) > Y_DRAG_THRESHOLD_PX) {
      setYCenter(drag.current.mid + (dy / rect.height) * span)
    }
  }

  const handlePointerUp = () => {
    drag.current = null
  }

  // SVG uses a 0..100 coordinate space stretched to the container
  const toX = (i) => (i / (visible.length - 1)) * 100
  const toY = (price) => (1 - (price - yMin) / (yMax - yMin)) * 100

  const step = niceStep(yMax - yMin, Y_TICK_COUNT)
  const decimals = Math.max(0, -Math.floor(Math.log10(step)))
  const yLabel = (v) => (asPercent ? `${(v * 100).toFixed(Math.max(0, decimals - 2))}%` : v.toFixed(decimals))
  const yTicks = []
  for (let v = Math.ceil(yMin / step) * step; v <= yMax; v += step) yTicks.push(v)

  const xTicks = [...new Set(
    Array.from({ length: X_TICK_COUNT }, (_, k) => Math.round((k * (visible.length - 1)) / (X_TICK_COUNT - 1))),
  )]

  const line = visible.map((p, i) => `${toX(i)},${toY(p.price)}`).join(' ')

  return (
    <div className="price-chart">
      {controls}
      <div className="price-chart__body">
        <div className="price-chart__y-axis">
          {yTicks.map((v) => (
            <span key={v} style={{ top: `${toY(v)}%` }}>{yLabel(v)}</span>
          ))}
        </div>

        <svg
          className="price-chart__plot"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          {yTicks.map((v) => (
            <line key={`y${v}`} x1="0" x2="100" y1={toY(v)} y2={toY(v)} vectorEffect="non-scaling-stroke" />
          ))}
          {xTicks.map((i) => (
            <line key={`x${i}`} x1={toX(i)} x2={toX(i)} y1="0" y2="100" vectorEffect="non-scaling-stroke" />
          ))}
          <polyline points={line} vectorEffect="non-scaling-stroke" />
        </svg>

        <div className="price-chart__x-axis">
          {xTicks.map((i) => (
            <span key={i} style={{ left: `${toX(i)}%` }}>{visible[i].time}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
