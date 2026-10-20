import DataTable from '../../components/DataTable.jsx'
import Panel from '../../components/Panel.jsx'
import StatusBadge from '../../components/StatusBadge.jsx'
import StreamNotice from '../../components/StreamNotice.jsx'
import StreamStatusBadge from '../../components/StreamStatusBadge.jsx'
import ServiceStatusCards from '../../components/ServiceStatusCards.jsx'
import useServiceStatus, { MONITORING_SERVICE_ID } from '../../hooks/useServiceStatus.js'
import usePersistentState from '../../hooks/usePersistentState.js'
import useTableView from '../../hooks/useTableView.js'
import ServiceDetails from './ServiceDetails.jsx'
import './MonitoringPage.scss'

export default function MonitoringPage() {
  const { services, streamStatus } = useServiceStatus()
  // monitoring-service can't check itself - its health is the stream connection shown in the header
  const monitored = services.filter((service) => service.id !== MONITORING_SERVICE_ID)
  const [selectedId, setSelectedId] = usePersistentState('monitoring.selectedService', null)
  const selected = monitored.find((row) => row.id === selectedId)

  const columns = [
    { key: 'label', label: 'Service', sortable: true },
    { key: 'status', label: 'Status', sortable: true, format: (v) => <StatusBadge status={v} /> },
    { key: 'response_time_ms', label: 'Response Time', sortable: true, format: (v) => `${Math.round(v)} ms` },
    {
      key: 'details',
      label: 'Details',
      render: (row) => (
        <button
          className={row.id === selectedId ? 'btn btn--primary' : 'btn'}
          onClick={() => setSelectedId(row.id)}
        >
          Details
        </button>
      ),
    },
  ]

  const table = useTableView('monitoring.table', columns, monitored)

  return (
    <>
      <StreamNotice
        name="Monitoring feed"
        status={streamStatus}
        impact="Monitoring Service is down or not publishing – the state of other services is unknown"
      />

      <section className="section">
        <h2>
          Monitoring feed
          <StreamStatusBadge status={streamStatus} />
        </h2>
        <ServiceStatusCards services={monitored} />
      </section>

      <div className="panels">
        <DataTable columns={columns} rows={table.rows} rowKey="id" sort={table.sort} onSort={table.toggleSort} />

        <Panel title={selected ? `${selected.label} Service – Details` : 'Details'}>
          {selected ? <ServiceDetails service={selected} /> : <p className="muted">Click „Details” on a service.</p>}
        </Panel>
      </div>
    </>
  )
}
