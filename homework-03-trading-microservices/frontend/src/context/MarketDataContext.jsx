import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import useSseStream from '../hooks/useSseStream.js'
import { getHistory, getSnapshot, openStream } from '../api/marketData.js'

const HISTORY_LENGTH = 500
const STALE_AFTER_MS = 30_000 // ~3x TICK_INTERVAL of market-data-service

// Two contexts: data changes per tick batch, stream status rarely - consumers re-render only for what they read
const MarketDataContext = createContext(null)
const MarketStreamContext = createContext(null)

// What a chart plots: spot price, or yield for bonds (no spot); undefined = nothing to plot (options)
export const plotValue = (tick) => tick?.spot ?? tick?.yield

// seq = backend event_id: unique and increasing, also across service restarts
const toPoint = (tick) => ({ seq: tick.event_id, time: tick.timestamp.slice(11, 19), price: plotValue(tick) })

// DB history and live ticks overlap (stream replays last ticks), so merge by seq
const mergePoints = (series, points) => {
  const bySeq = new Map([...series, ...points].map((p) => [p.seq, p]))
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq).slice(-HISTORY_LENGTH)
}

// pointsBySymbol: { symbol: [point, ...] }
const mergeHistory = (history, pointsBySymbol) => {
  const next = { ...history }
  for (const [symbol, points] of Object.entries(pointsBySymbol)) {
    next[symbol] = mergePoints(history[symbol] ?? [], points)
  }
  return next
}

// Lives above the pages (in App), so the stream and price history survive page switches
export function MarketDataProvider({ children }) {
  const [latest, setLatest] = useState({})   // symbol -> last tick
  const [history, setHistory] = useState({}) // symbol -> [{ seq, time, price }, ...]
  const [received, setReceived] = useState({}) // symbol -> ticks received over the stream since app load

  useEffect(() => {
    getSnapshot()
      .then((snapshot) => setLatest((prev) => ({ ...snapshot, ...prev })))
      .catch((err) => console.error('snapshot failed', err))
  }, [])

  const loadHistory = () =>
    getHistory(HISTORY_LENGTH)
      .then((stored) => {
        const points = Object.fromEntries(Object.entries(stored).map(([symbol, ticks]) => [symbol, ticks.map(toPoint)]))
        setHistory((prev) => mergeHistory(prev, points))
      })
      .catch((err) => console.error('history failed', err))

  const { status, lastEventAt } = useSseStream(openStream, {
    staleAfterMs: STALE_AFTER_MS,
    // Also fires after an automatic reconnect (e.g. service restart) - refill what we missed
    onOpen: loadHistory,
    onEvents: (events) => {
      const ticks = events.filter((e) => e.event_type !== 'CURVE')
      if (ticks.length === 0) return

      const points = {}
      for (const tick of ticks) {
        if (plotValue(tick) !== undefined) (points[tick.symbol] ??= []).push(toPoint(tick))
      }
      setLatest((prev) => ({ ...prev, ...Object.fromEntries(ticks.map((t) => [t.symbol, t])) }))
      setHistory((prev) => mergeHistory(prev, points))
      setReceived((prev) => {
        const next = { ...prev }
        for (const tick of ticks) next[tick.symbol] = (next[tick.symbol] ?? 0) + 1
        return next
      })
    },
  })

  const data = useMemo(() => ({ latest, history, received }), [latest, history, received])
  const stream = useMemo(() => ({ status, lastEventAt }), [status, lastEventAt])

  return (
    <MarketStreamContext.Provider value={stream}>
      <MarketDataContext.Provider value={data}>{children}</MarketDataContext.Provider>
    </MarketStreamContext.Provider>
  )
}

// { latest, history, received }
export const useMarketData = () => useContext(MarketDataContext)

// { status, lastEventAt }
export const useMarketStream = () => useContext(MarketStreamContext)
