import './TableFilters.scss'

// DataTable emptyMessage when rows exist but none pass the filters
export function NoMatches({ onClear }) {
  return (
    <>
      No rows match the current filters.{' '}
      <button className="btn btn--link" onClick={onClear}>Clear filters</button>
    </>
  )
}

// Renders a text input for every column with `filter` set
export default function TableFilters({ columns, filters, onChange }) {
  const filterable = columns.filter((col) => col.filter)
  const setFilter = (key, value) => onChange({ ...filters, [key]: value })
  const isEmpty = filterable.every((col) => !filters[col.key])

  return (
    <div className="table-filters">
      {filterable.map((col) => (
        <label key={col.key}>
          {col.label}
          <input
            className="input"
            type="search"
            placeholder={`Filter ${col.label.toLowerCase()}...`}
            value={filters[col.key] ?? ''}
            onChange={(e) => setFilter(col.key, e.target.value)}
          />
        </label>
      ))}
      <button className="btn" disabled={isEmpty} onClick={() => onChange({})}>Clear filters</button>
    </div>
  )
}
