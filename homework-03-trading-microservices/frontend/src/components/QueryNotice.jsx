import Notice from './Notice.jsx'

// Failed usePolling load: with earlier data -> stale warning, without -> error.
// onRetry = manual retry for one-shot loads; polled loads retry on their own.
export default function QueryNotice({ what, service, error, updatedAt, onRetry }) {
  if (!error) return null

  const reason = error.kind === 'unavailable' ? `${service} is down or unreachable.` : `Backend error: ${error.message}.`
  const retry = onRetry ? <button className="btn" onClick={onRetry}>Retry</button> : null
  const retryText = onRetry ? '' : ' Retrying automatically…'

  if (updatedAt) {
    return (
      <Notice tone="warning" title={`Showing stale ${what}`} action={retry}>
        {reason} Data from {updatedAt.toLocaleTimeString()}.{retryText}
      </Notice>
    )
  }
  return (
    <Notice tone="error" title={`Cannot load ${what}`} action={retry}>
      {reason}{retryText}
    </Notice>
  )
}
