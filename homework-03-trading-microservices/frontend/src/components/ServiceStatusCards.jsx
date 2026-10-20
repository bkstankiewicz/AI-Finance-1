import StatusBadge from './StatusBadge.jsx'
import './ServiceStatusCards.scss'

// services: `services` from useServiceStatus()
export default function ServiceStatusCards({ services }) {
  return (
    <section className="service-cards">
      {services.map(({ id, label, status }) => (
        <div key={id} className="card service-card">
          <span>{label} Service Status</span>
          <StatusBadge status={status} />
        </div>
      ))}
    </section>
  )
}
