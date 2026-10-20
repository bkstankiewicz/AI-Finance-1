import './Notice.scss'

// tone: 'error' (feature broken) | 'warning' (works, but data may be outdated) | 'info'
export default function Notice({ tone = 'info', title, children, action }) {
  return (
    <div className={`notice notice--${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <div className="notice__body">
        <strong>{title}</strong>
        {children && <span className="notice__text">{children}</span>}
      </div>
      {action}
    </div>
  )
}
