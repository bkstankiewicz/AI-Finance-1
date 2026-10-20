import usePersistentState from './usePersistentState.js'

export const NO_SORT = { key: null, dir: 'asc' }

// Value used for sorting/filtering - column.value(row) wins, e.g. boolean -> 'ACTIVE'
export const cellValue = (col, row) => (col.value ? col.value(row) : row[col.key])

const compare = (a, b) => {
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), undefined, { numeric: true })
}

// filter: 'prefix' = starts with (so "active" skips "INACTIVE"), anything else = substring; case-insensitive
const matches = (col, row, wanted) => {
  const value = cellValue(col, row)
  if (value === undefined || value === null) return false
  const text = String(value).toLowerCase()
  const query = wanted.trim().toLowerCase()
  return col.filter === 'prefix' ? text.startsWith(query) : text.includes(query)
}

// Sort + filter state for a DataTable, remembered per storageKey across page switches
export default function useTableView(storageKey, columns, rows, initialSort = NO_SORT) {
  const [sort, setSort] = usePersistentState(`${storageKey}.sort`, initialSort)
  const [filters, setFilters] = usePersistentState(`${storageKey}.filters`, {})

  const byKey = Object.fromEntries(columns.map((col) => [col.key, col]))
  const activeFilters = Object.entries(filters).filter(([key, wanted]) => wanted && byKey[key])
  let visible = rows.filter((row) => activeFilters.every(([key, wanted]) => matches(byKey[key], row, wanted)))

  const sortCol = byKey[sort.key]
  if (sortCol) {
    const sign = sort.dir === 'desc' ? -1 : 1
    const isMissing = (v) => v === undefined || v === null
    visible = [...visible].sort((a, b) => {
      const va = cellValue(sortCol, a)
      const vb = cellValue(sortCol, b)
      // Missing values stay at the bottom in both directions
      if (isMissing(va) || isMissing(vb)) return isMissing(va) - isMissing(vb)
      return sign * compare(va, vb)
    })
  }

  // Header click cycles: asc -> desc -> unsorted
  const toggleSort = (key) => {
    if (sort.key !== key) setSort({ key, dir: 'asc' })
    else if (sort.dir === 'asc') setSort({ key, dir: 'desc' })
    else setSort(NO_SORT)
  }

  return { rows: visible, sort, toggleSort, filters, setFilters }
}
