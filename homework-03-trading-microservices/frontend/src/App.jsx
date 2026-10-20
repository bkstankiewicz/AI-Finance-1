import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import OverviewPage from './features/overview/OverviewPage.jsx'
import MarketDataPage from './features/market-data/MarketDataPage.jsx'
import { MarketDataProvider } from './context/MarketDataContext.jsx'
import { ChartSessionsProvider } from './features/market-data/ChartSessions.jsx'
import PricingPage from './features/pricing/PricingPage.jsx'
import BooksPage from './features/books/BooksPage.jsx'
import TradeGenerationPage from './features/trade-generation/TradeGenerationPage.jsx'
import TradeActionPage from './features/trade-action/TradeActionPage.jsx'
import BlotterPage from './features/blotter/BlotterPage.jsx'
import { BlotterSessionsProvider } from './features/blotter/BlotterSessions.jsx'
import MonitoringPage from './features/monitoring/MonitoringPage.jsx'

// page name -> component; null = not implemented yet
const PAGES = {
  'Overview': OverviewPage,
  'Market Data': MarketDataPage,
  'Pricing Data': PricingPage,
  'Books': BooksPage,
  'Trade Generation': TradeGenerationPage,
  'Trade Action': TradeActionPage,
  'Blotter': BlotterPage,
  'Monitoring': MonitoringPage,
}

const DEFAULT_PAGE = 'Overview'

// 'Market Data' <-> '#/market-data'
const toHash = (page) => `#/${page.toLowerCase().replaceAll(' ', '-')}`
const fromHash = (hash) => Object.keys(PAGES).find((page) => toHash(page) === hash) ?? DEFAULT_PAGE

export default function App() {
  const [activePage, setActivePage] = useState(() => fromHash(window.location.hash))
  const Page = PAGES[activePage]

  // Browser back/forward and manually edited URLs
  useEffect(() => {
    const onHashChange = () => setActivePage(fromHash(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const navigate = (page) => {
    window.location.hash = toHash(page)
  }

  return (
    <MarketDataProvider>
      <ChartSessionsProvider>
        <BlotterSessionsProvider>
          <div className="app">
            <Sidebar pages={Object.keys(PAGES)} active={activePage} onSelect={navigate} />

            <main className="app__content">
              {Page ? <Page /> : <p className="placeholder">{activePage} – coming soon</p>}
            </main>
          </div>
        </BlotterSessionsProvider>
      </ChartSessionsProvider>
    </MarketDataProvider>
  )
}
