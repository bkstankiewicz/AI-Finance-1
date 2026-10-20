import { useEffect, useState } from 'react'

// fetcher must be a stable (module-level) function; intervalMs = null -> load once, refresh via reload()
// On a failed refresh the previous data is kept: error + data = stale data, error alone = nothing to show
export default function usePolling(fetcher, intervalMs = null) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const result = await fetcher()
        if (cancelled) return
        setData(result)
        setError(null)
        setUpdatedAt(new Date())
      } catch (err) {
        if (!cancelled) setError(err)
      }
    }

    load()
    const id = intervalMs ? setInterval(load, intervalMs) : null
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [fetcher, intervalMs, reloadCount])

  const reload = () => setReloadCount((n) => n + 1)

  return { data, error, loading: updatedAt === null && error === null, updatedAt, reload }
}
