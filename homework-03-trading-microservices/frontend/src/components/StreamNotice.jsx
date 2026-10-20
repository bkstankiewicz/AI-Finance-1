import Notice from './Notice.jsx'

// impact: what the user loses while the stream is down, e.g. "Fair value and PnL are not updating"
export default function StreamNotice({ name, status, lastEventAt, impact }) {
  const lastUpdate = lastEventAt ? ` Last update at ${new Date(lastEventAt).toLocaleTimeString()}.` : ''

  if (status === 'RECONNECTING') {
    return (
      <Notice tone="error" title={`${name} unavailable`}>
        {impact}.{lastUpdate} Reconnecting automatically…
      </Notice>
    )
  }
  if (status === 'STALE') {
    return (
      <Notice tone="warning" title={`${name} is stale`}>
        Connected, but no updates received recently. {impact}.{lastUpdate}
      </Notice>
    )
  }
  return null
}
