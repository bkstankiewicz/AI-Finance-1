import { useState } from 'react'
import useSseStream from '../../hooks/useSseStream.js'
import { openValuationStream, VALUATION_STALE_AFTER_MS } from '../../api/pricing.js'

// trade_id -> latest valuation pushed by pricing-service: the live state of the blotter
export default function useLiveValuations() {
  const [byTrade, setByTrade] = useState({})

  const { status, lastEventAt } = useSseStream(openValuationStream, {
    staleAfterMs: VALUATION_STALE_AFTER_MS,
    onEvents: (valuations) => {
      const receivedAt = new Date().toISOString()
      setByTrade((prev) => ({
        ...prev,
        ...Object.fromEntries(valuations.map((v) => [v.trade_id, { ...v, received_at: receivedAt }])),
      }))
    },
  })

  return { byTrade, status, lastEventAt }
}
