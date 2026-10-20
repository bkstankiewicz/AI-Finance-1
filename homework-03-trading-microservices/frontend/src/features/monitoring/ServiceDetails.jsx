import { useEffect, useState } from 'react'
import DetailsList from '../../components/DetailsList.jsx'
import StatusBadge from '../../components/StatusBadge.jsx'
import { getLastErrorTimestamp, getServiceErrorCounter } from '../../api/monitoring.js'
import { formatDateTime } from '../../utils/format.js'

const FIELDS = [
  { key: 'status', label: 'Status', format: (v) => <StatusBadge status={v} /> },
  { key: 'last_checked', label: 'Last check', format: formatDateTime },
  { key: 'response_time_ms', label: 'Response time', format: (v) => `${Math.round(v)} ms` },
  { key: 'error', label: 'Current error' },
  { key: 'error_count', label: 'Error counter' },
  { key: 'last_error_timestamp', label: 'Last error', format: formatDateTime },
]

export default function ServiceDetails({ service }) {
  const [diagnostics, setDiagnostics] = useState(null)
  const [diagnosticsError, setDiagnosticsError] = useState(null)

  useEffect(() => {
    let active = true
    setDiagnostics(null)
    setDiagnosticsError(null)

    Promise.all([
      getServiceErrorCounter(service.id),
      getLastErrorTimestamp(service.id),
    ])
      .then(([counter, lastError]) => {
        if (active) setDiagnostics({ ...counter, ...lastError })
      })
      .catch((error) => {
        if (active) setDiagnosticsError(error)
      })

    return () => { active = false }
  }, [service.id])

  return (
    <>
      <DetailsList fields={FIELDS} data={{ ...service, ...diagnostics }} />
      {diagnosticsError && <p className="muted">Could not load error diagnostics: {diagnosticsError.message}</p>}
    </>
  )
}
