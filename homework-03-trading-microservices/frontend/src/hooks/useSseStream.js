import { useEffect, useRef, useState } from 'react'

const FLUSH_INTERVAL_MS = 250
const RETRY_MS = 3000
const STALE_CHECK_MS = 1000

// status: CONNECTING -> CONNECTED; RECONNECTING after any error (retried until it works);
// STALE = connected, but no event for staleAfterMs (publisher alive but not publishing).
// Events are buffered and passed to onEvents(batch) every FLUSH_INTERVAL_MS: one render per burst, not per event.
// The hook itself causes no render per batch - only onEvents decides (e.g. skips batches it filters out).
// lastEventAt (ms timestamp) is only published when the stream goes STALE/RECONNECTING - it's shown only then.
export default function useSseStream(openSource, { onEvents, onOpen, staleAfterMs = null }) {
  const [status, setStatus] = useState('CONNECTING')
  const [lastEventAt, setLastEventAt] = useState(null)

  // Latest callbacks without reopening the stream when they change
  const handlers = useRef({ onEvents, onOpen })
  useEffect(() => {
    handlers.current = { onEvents, onOpen }
  })

  useEffect(() => {
    let source = null
    let buffer = []
    let flushTimer = null
    let retryTimer = null
    let lastEvent = Date.now()
    let lastMessageAt = null

    const flush = () => {
      flushTimer = null
      const batch = buffer
      buffer = []
      setStatus((s) => (s === 'STALE' ? 'CONNECTED' : s))
      handlers.current.onEvents(batch)
    }

    const connect = () => {
      source = openSource()
      source.onopen = () => {
        lastEvent = Date.now()
        setStatus('CONNECTED')
        handlers.current.onOpen?.()
      }
      source.onmessage = (message) => {
        lastEvent = Date.now()
        lastMessageAt = lastEvent
        buffer.push(JSON.parse(message.data))
        flushTimer ??= setTimeout(flush, FLUSH_INTERVAL_MS)
      }
      source.onerror = () => {
        setLastEventAt(lastMessageAt)
        setStatus('RECONNECTING')
        // EventSource retries by itself, except when the response was not a stream (e.g. 503) - then it gives up
        if (source.readyState === EventSource.CLOSED) retryTimer = setTimeout(connect, RETRY_MS)
      }
    }
    connect()

    const staleTimer = staleAfterMs
      ? setInterval(() => {
          if (Date.now() - lastEvent <= staleAfterMs) return
          setLastEventAt(lastMessageAt)
          setStatus((s) => (s === 'CONNECTED' ? 'STALE' : s))
        }, STALE_CHECK_MS)
      : null

    return () => {
      clearTimeout(flushTimer)
      clearTimeout(retryTimer)
      clearInterval(staleTimer)
      source.close()
    }
  }, [openSource, staleAfterMs])

  return { status, lastEventAt }
}
