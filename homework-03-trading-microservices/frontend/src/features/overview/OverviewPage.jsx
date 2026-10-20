import ServiceStatusCards from '../../components/ServiceStatusCards.jsx'
import useServiceStatus from '../../hooks/useServiceStatus.js'
import usePersistentState from '../../hooks/usePersistentState.js'
import BusinessOverview from './BusinessOverview.jsx'
import DeveloperOverview from './DeveloperOverview.jsx'
import './OverviewPage.scss'

// Each mode is its own component, so only the visible one polls its data
const MODES = {
  Business: BusinessOverview,
  Developer: DeveloperOverview,
}

export default function OverviewPage() {
  const [mode, setMode] = usePersistentState('overview.mode', 'Business')
  const { services } = useServiceStatus()
  const ModeView = MODES[mode] ?? BusinessOverview

  return (
    <>
      <div className="overview-mode" role="group" aria-label="Overview mode">
        {Object.keys(MODES).map((name) => (
          <button
            key={name}
            className={name === mode ? 'btn btn--primary' : 'btn'}
            aria-pressed={name === mode}
            onClick={() => setMode(name)}
          >
            {name}
          </button>
        ))}
      </div>

      <ServiceStatusCards services={services} />

      <ModeView />
    </>
  )
}
