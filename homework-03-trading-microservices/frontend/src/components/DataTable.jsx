import { memo } from 'react'
import './DataTable.scss'

// column: { key, label, format?(value), render?(row) } - render wins, used for buttons/links
export const renderCell = (col, row) => {
  if (col.render) return col.render(row)
  const value = row[col.key]
  if (value === undefined || value === null) return '—'
  return col.format ? col.format(value) : value
}

const SORT_ICONS = { asc: '▲', desc: '▼' }

// col.className: string, or (row) => string for per-row styling (ignored in the header)
const cellClass = (col, row) => {
  const custom = typeof col.className === 'function' ? row && col.className(row) : col.className
  return [custom, col.pinned && 'is-pinned'].filter(Boolean).join(' ') || undefined
}

// Re-renders only when its row object or the columns array changes - live tables keep both stable
// (so a column's render/format must not read state that isn't in the row or in the columns' memo deps)
const DataRow = memo(function DataRow({ row, columns }) {
  return <tr>{columns.map((col) => <td key={col.key} className={cellClass(col, row)}>{renderCell(col, row)}</td>)}</tr>
})

// sort/onSort (from useTableView) are optional; only columns with `sortable` get a clickable header.
// col.className styles cells (e.g. stale values); emptyMessage replaces "No data" (e.g. no filter matches).
// footer: rendered under the rows inside the table frame, e.g. <Pagination />
// onMoveColumn(key, targetKey) (from useColumnLayout) enables header drag & drop; col.pinned headers stay put
export default function DataTable({ columns, rows, rowKey, sort, onSort, loading = false, emptyMessage = 'No data', footer, onMoveColumn }) {
  const dragProps = (col) =>
    onMoveColumn && !col.pinned
      ? {
          draggable: true,
          title: 'Drag to reorder',
          onDragStart: (e) => e.dataTransfer.setData('text/plain', col.key),
          onDragOver: (e) => e.preventDefault(),
          onDrop: (e) => {
            e.preventDefault()
            onMoveColumn(e.dataTransfer.getData('text/plain'), col.key)
          },
        }
      : {}

  const header = (col) => {
    const props = { className: cellClass(col), ...dragProps(col) }
    if (!col.sortable || !onSort) return <th key={col.key} {...props}>{col.label}</th>
    const dir = sort?.key === col.key ? sort.dir : null
    return (
      <th key={col.key} {...props} aria-sort={dir ? `${dir}ending` : 'none'}>
        <button className="data-table__sort" onClick={() => onSort(col.key)}>
          {col.label}
          <span className={dir ? 'data-table__sort-icon is-active' : 'data-table__sort-icon'}>
            {SORT_ICONS[dir] ?? '↕'}
          </span>
        </button>
      </th>
    )
  }

  return (
    <div className="data-table">
      <div className="data-table__scroll">
        <table>
          <thead>
            <tr>{columns.map(header)}</tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td className="data-table__empty" colSpan={columns.length}>{loading ? 'Loading…' : emptyMessage}</td>
              </tr>
            )}
            {rows.map((row) => <DataRow key={row[rowKey]} row={row} columns={columns} />)}
          </tbody>
        </table>
      </div>
      {footer && <div className="data-table__footer">{footer}</div>}
    </div>
  )
}
