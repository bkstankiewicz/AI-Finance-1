import { useMemo } from 'react'
import usePersistentState from './usePersistentState.js'

const without = (list, key) => list.filter((k) => k !== key)

// User-defined column order / visibility / pinning for a DataTable, remembered per storageKey.
// Pinned columns always come first and are locked: they can't be hidden or moved until unpinned.
// Until the user changes something, defaults are derived on every render (columns may appear as data arrives).
export default function useColumnLayout(storageKey, columns, defaultVisible, defaultPinned = []) {
  const [saved, setSaved] = usePersistentState(`${storageKey}.columns`, null)
  const keys = columns.map((col) => col.key)
  const byKey = Object.fromEntries(columns.map((col) => [col.key, col]))

  // Keys that showed up after the layout was saved are appended (hidden unless default-visible)
  const base = (saved?.order ?? defaultVisible).filter((k) => byKey[k])
  const order = [...base, ...keys.filter((k) => !base.includes(k))]
  const pinned = (saved?.pinned ?? defaultPinned).filter((k) => byKey[k])
  const visible = saved?.visible ?? defaultVisible
  const ordered = [...pinned, ...order.filter((k) => !pinned.includes(k))]
  const isVisible = (k) => pinned.includes(k) || visible.includes(k)

  const commit = (next) => setSaved({ order: ordered, visible: ordered.filter(isVisible), pinned, ...next })

  const toggleVisible = (key) => {
    if (pinned.includes(key)) return
    commit({ visible: isVisible(key) ? without(ordered.filter(isVisible), key) : [...ordered.filter(isVisible), key] })
  }

  // Pinning moves the column right behind the already pinned ones; unpinning leaves it there
  const togglePin = (key) => {
    if (pinned.includes(key)) return commit({ pinned: without(pinned, key) })
    const rest = without(ordered, key)
    rest.splice(pinned.length, 0, key)
    commit({ order: rest, pinned: [...pinned, key], visible: [...ordered.filter(isVisible), key] })
  }

  // Puts `key` at the position of `targetKey` (drag & drop or a neighbour for up/down)
  const move = (key, targetKey) => {
    if (key === targetKey || pinned.includes(key) || pinned.includes(targetKey)) return
    const next = without(ordered, key)
    next.splice(ordered.indexOf(targetKey), 0, key)
    commit({ order: next })
  }

  // Same array while inputs are the same, so DataTable's memoized rows can skip re-rendering
  const visibleColumns = useMemo(
    () => ordered.filter(isVisible).map((k) => (pinned.includes(k) ? { ...byKey[k], pinned: true } : byKey[k])),
    [columns, saved, defaultVisible, defaultPinned],
  )

  return {
    columns: visibleColumns,
    items: ordered.map((k) => ({ col: byKey[k], visible: isVisible(k), pinned: pinned.includes(k) })),
    toggleVisible,
    togglePin,
    move,
    reset: () => setSaved(null),
    isCustom: saved !== null,
  }
}
