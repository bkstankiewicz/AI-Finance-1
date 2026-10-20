import { useState } from 'react'
import DataTable from '../../components/DataTable.jsx'
import Panel from '../../components/Panel.jsx'
import StatusBadge from '../../components/StatusBadge.jsx'
import QueryNotice from '../../components/QueryNotice.jsx'
import TableFilters, { NoMatches } from '../../components/TableFilters.jsx'
import usePolling from '../../hooks/usePolling.js'
import usePersistentState from '../../hooks/usePersistentState.js'
import useTableView from '../../hooks/useTableView.js'
import { deleteBook, getBooks } from '../../api/books.js'
import { shortId } from '../../utils/format.js'
import BookDetails from './BookDetails.jsx'
import BookForm from './BookForm.jsx'

export default function BooksPage() {
  const { data: books, error, loading, updatedAt, reload } = usePolling(getBooks)
  const [selectedId, setSelectedId] = usePersistentState('books.selectedId', null)
  const [editedId, setEditedId] = useState(null)
  const [actionError, setActionError] = useState(null)

  const selected = books?.find((b) => b.book_id === selectedId)
  const edited = books?.find((b) => b.book_id === editedId)

  const handleDelete = async (book) => {
    if (!window.confirm(`Delete book ${book.name}?`)) return
    setActionError(null)
    try {
      await deleteBook(book.book_id)
      reload()
    } catch (err) {
      setActionError(err.kind === 'unavailable' ? 'Delete failed: Books Service is down or unreachable.' : `Delete failed: ${err.message}`)
    }
  }

  const columns = [
    { key: 'name', label: 'Book Name', sortable: true },
    { key: 'book_id', label: 'Book ID', sortable: true, format: shortId },
    { key: 'expected_asset_class', label: 'Asset Class', sortable: true, filter: 'text' },
    {
      key: 'is_active',
      label: 'Status',
      sortable: true,
      filter: 'prefix',
      value: (row) => (row.is_active ? 'ACTIVE' : 'INACTIVE'),
      format: (v) => <StatusBadge status={v ? 'UP' : 'DOWN'}>{v ? 'ACTIVE' : 'INACTIVE'}</StatusBadge>,
    },
    {
      key: 'details',
      label: 'Details',
      render: (row) => <button className="btn" onClick={() => setSelectedId(row.book_id)}>Details</button>,
    },
    {
      key: 'edit',
      label: 'Edit',
      render: (row) => <button className="btn btn--accent" onClick={() => setEditedId(row.book_id)}>Edit</button>,
    },
    {
      key: 'delete',
      label: 'Delete',
      render: (row) => <button className="btn btn--danger" onClick={() => handleDelete(row)}>Delete</button>,
    },
  ]

  const table = useTableView('books.table', columns, books ?? [])
  const hasFilters = Object.values(table.filters).some(Boolean)
  const otherNames = (books ?? []).filter((b) => b.book_id !== editedId).map((b) => b.name)

  return (
    <>
      <section className="section">
        <QueryNotice what="books" service="Books Service" error={error} updatedAt={updatedAt} onRetry={reload} />
        {actionError && <p className="error">{actionError}</p>}
        <TableFilters columns={columns} filters={table.filters} onChange={table.setFilters} />
        <DataTable
          columns={columns}
          rows={table.rows}
          rowKey="book_id"
          sort={table.sort}
          onSort={table.toggleSort}
          loading={loading}
          emptyMessage={
            error && !books ? 'Books unavailable'
              : books?.length && hasFilters ? <NoMatches onClear={() => table.setFilters({})} />
                : 'No books yet. Create the first one with the form below.'
          }
        />
      </section>

      <div className="panels">
        <Panel title="Details">
          {selected ? <BookDetails book={selected} /> : <p className="muted">Click „Details” on a book.</p>}
        </Panel>

        <Panel title={edited ? `Edit ${edited.name}` : 'New Book'}>
          {/* key remounts the form, so its local state resets when switching books */}
          <BookForm
            key={editedId ?? 'new'}
            book={edited}
            existingNames={otherNames}
            onSaved={() => {
              setEditedId(null)
              reload()
            }}
            onCancel={() => setEditedId(null)}
          />
        </Panel>
      </div>
    </>
  )
}
