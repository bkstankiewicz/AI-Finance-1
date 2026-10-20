import { useEffect, useState } from 'react'
import useTheme from '../hooks/useTheme.js'
import Icon from './Icon.jsx'
import './Sidebar.scss'

const STORAGE_KEY = 'sidebar-collapsed'

// page name (keys of PAGES in App.jsx) -> Icon name
const PAGE_ICONS = {
  'Overview': 'overview',
  'Market Data': 'marketData',
  'Pricing Data': 'pricing',
  'Books': 'books',
  'Trade Generation': 'tradeGeneration',
  'Trade Action': 'tradeAction',
  'Blotter': 'blotter',
  'Monitoring': 'monitoring',
}

export default function Sidebar({ pages, active, onSelect }) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(STORAGE_KEY) === 'true')
  const { theme, toggleTheme } = useTheme()

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed))
  }, [collapsed])

  return (
    <nav className={collapsed ? 'sidebar sidebar--collapsed' : 'sidebar'}>
      <button
        className="sidebar__toggle"
        title={collapsed ? 'Expand menu' : 'Collapse menu'}
        aria-expanded={!collapsed}
        onClick={() => setCollapsed((c) => !c)}
      >
        <Icon name={collapsed ? 'expand' : 'collapse'} />
      </button>

      <ul>
        {pages.map((page) => (
          <li key={page}>
            <button
              className={page === active ? 'sidebar__item sidebar__item--active' : 'sidebar__item'}
              aria-current={page === active ? 'page' : undefined}
              title={collapsed ? page : undefined}
              onClick={() => onSelect(page)}
            >
              <Icon name={PAGE_ICONS[page]} />
              <span className="sidebar__label">{page}</span>
            </button>
          </li>
        ))}
      </ul>

      <button
        className="sidebar__toggle sidebar__theme"
        title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        onClick={toggleTheme}
      >
        <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
      </button>
    </nav>
  )
}
