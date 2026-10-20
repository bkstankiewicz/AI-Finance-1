import { useState } from 'react'
import useSseStream from '../../hooks/useSseStream.js'
import { openValuationStream, VALUATION_STALE_AFTER_MS } from '../../api/pricing.js'

// Latest valuation per symbol; pricing-service sends one event per trade in bursts, so batching matters here
export default function useValuationStream() {
  const [latestBySymbol, setLatestBySymbol] = useState({})

  const { status, lastEventAt } = useSseStream(openValuationStream, {
    staleAfterMs: VALUATION_STALE_AFTER_MS,
    onEvents: (valuations) =>
      setLatestBySymbol((prev) => ({ ...prev, ...Object.fromEntries(valuations.map((v) => [v.symbol, v])) })),
  })

  return { latestBySymbol, status, lastEventAt }
}
