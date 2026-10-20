import './StatusBadge.scss'

// status: 'UP' | 'DOWN' | 'WARN' | undefined (unknown)
export default function StatusBadge({ status, children }) {
  const modifier = (status ?? 'unknown').toLowerCase()
  return <span className={`status-badge status-badge--${modifier}`}>{children ?? status ?? '?'}</span>
}
