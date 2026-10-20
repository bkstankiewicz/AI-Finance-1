import { createContext, useContext, useEffect, useRef, useState } from 'react'
import ChartWindow from './ChartWindow.jsx'

const POPUP_FEATURES = 'popup,width=900,height=760'

const ChartSessionsContext = createContext(null)

// Micro-sessions: each one is a popup window rendered through a portal from this tree,
// so it is wired only to the main window (shared market data stream, no own connection).
// Lives in App, so the windows survive page switches in the main window.
export function ChartSessionsProvider({ children }) {
  const [sessions, setSessions] = useState([]) // [{ id, title, win, symbols }]
  const [activeId, setActiveId] = useState(null)
  const [blocked, setBlocked] = useState(false)
  const nextId = useRef(1)
  const sessionsRef = useRef(sessions)
  sessionsRef.current = sessions

  // Popups die with the main window - their content is rendered from here
  useEffect(() => {
    const closeAll = () => sessionsRef.current.forEach((s) => s.win.close())
    window.addEventListener('pagehide', closeAll)
    return () => {
      window.removeEventListener('pagehide', closeAll)
      closeAll()
    }
  }, [])

  const active = sessions.find((s) => s.id === activeId) ?? sessions.at(-1)

  // Must be called straight from a click handler, otherwise the browser blocks the popup
  const openSession = (symbols = []) => {
    const win = window.open('', '_blank', POPUP_FEATURES)
    setBlocked(!win)
    if (!win) return
    const id = nextId.current++
    setSessions((prev) => [...prev, { id, title: `Charts #${id}`, win, symbols }])
    setActiveId(id)
  }

  const dropSession = (id) => setSessions((prev) => prev.filter((s) => s.id !== id))

  const closeSession = (id) => {
    sessions.find((s) => s.id === id)?.win.close()
    dropSession(id)
  }

  const focusSession = (id) => {
    setActiveId(id)
    sessions.find((s) => s.id === id)?.win.focus()
  }

  const toggleSymbol = (id, symbol) =>
    setSessions((prev) =>
      prev.map((s) =>
        s.id !== id
          ? s
          : { ...s, symbols: s.symbols.includes(symbol) ? s.symbols.filter((x) => x !== symbol) : [...s.symbols, symbol] },
      ),
    )

  // "Plot" in the main table targets the active window, or opens the first one
  const plot = (symbol) => (active ? toggleSymbol(active.id, symbol) : openSession([symbol]))

  const value = { sessions, active, blocked, openSession, closeSession, focusSession, plot }

  return (
    <ChartSessionsContext.Provider value={value}>
      {children}
      {sessions.map((session) => (
        <ChartWindow
          key={session.id}
          session={session}
          onClosed={dropSession}
          onFocus={setActiveId}
          onToggle={(symbol) => toggleSymbol(session.id, symbol)}
        />
      ))}
    </ChartSessionsContext.Provider>
  )
}

export const useChartSessions = () => useContext(ChartSessionsContext)
