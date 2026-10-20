import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import usePersistentState from '../../hooks/usePersistentState.js'
import usePolling from '../../hooks/usePolling.js'
import { getBooksSummary } from '../../api/blotter.js'
import TradesWindow from './TradesWindow.jsx'
import useLiveValuations from './useLiveValuations.js'

const POPUP_FEATURES = 'popup,width=1400,height=820'
const BOOKS_POLL_MS = 30000 // only names / scope options - PnL lives in the main Blotter view

const BlotterSessionsContext = createContext(null)

// Trade micro-sessions: popup windows rendered through a portal from this tree (same pattern as chart sessions).
// Lives in App, so the windows survive page switches; the watchlist is shared by all windows.
export function BlotterSessionsProvider({ children }) {
  const [sessions, setSessions] = useState([]) // [{ id, win, bookId }] - bookId '' = all books
  const [blocked, setBlocked] = useState(false)
  const [watchlist, setWatchlist] = usePersistentState('blotter.watchlist', [])
  const nextId = useRef(1)
  const sessionsRef = useRef(sessions)
  sessionsRef.current = sessions
  // Stable toggle, so the trade tables' memoized columns survive watchlist changes
  const watchlistRef = useRef(watchlist)
  watchlistRef.current = watchlist

  // Popups die with the main window - their content is rendered from here
  useEffect(() => {
    const closeAll = () => sessionsRef.current.forEach((s) => s.win.close())
    window.addEventListener('pagehide', closeAll)
    return () => {
      window.removeEventListener('pagehide', closeAll)
      closeAll()
    }
  }, [])

  const focusSession = (id) => sessions.find((s) => s.id === id)?.win.focus()

  // Must be called straight from a click handler, otherwise the browser blocks the popup.
  // A window already showing this scope is focused instead of opening a duplicate.
  const openSession = (bookId = '') => {
    const existing = sessions.find((s) => s.bookId === bookId)
    if (existing) return focusSession(existing.id)
    const win = window.open('', '_blank', POPUP_FEATURES)
    setBlocked(!win)
    if (!win) return
    setSessions((prev) => [...prev, { id: nextId.current++, win, bookId }])
  }

  const dropSession = (id) => setSessions((prev) => prev.filter((s) => s.id !== id))

  const setScope = (id, bookId) => setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, bookId } : s)))

  const toggleWatch = useCallback((tradeId) => {
    const list = watchlistRef.current
    setWatchlist(list.includes(tradeId) ? list.filter((id) => id !== tradeId) : [...list, tradeId])
  }, [])

  const value = { sessions, blocked, openSession, focusSession, watchlist }

  return (
    <BlotterSessionsContext.Provider value={value}>
      {children}
      {sessions.length > 0 && (
        <TradeWindows
          sessions={sessions}
          watchlist={watchlist}
          onToggleWatch={toggleWatch}
          onScopeChange={setScope}
          onClosed={dropSession}
        />
      )}
    </BlotterSessionsContext.Provider>
  )
}

// Mounted only while a window is open, so the valuation stream isn't held without a reader
function TradeWindows({ sessions, watchlist, onToggleWatch, onScopeChange, onClosed }) {
  const live = useLiveValuations()
  const books = usePolling(getBooksSummary, BOOKS_POLL_MS)

  return sessions.map((session) => (
    <TradesWindow
      key={session.id}
      session={session}
      books={books.data ?? []}
      live={live}
      watchlist={watchlist}
      onToggleWatch={onToggleWatch}
      onScopeChange={(bookId) => onScopeChange(session.id, bookId)}
      onClosed={() => onClosed(session.id)}
    />
  ))
}

export const useBlotterSessions = () => useContext(BlotterSessionsContext)
