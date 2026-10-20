import './Pagination.scss'

const MAX_BUTTONS = 7

// [1, null, 4, 5, 6, null, 10] - null = gap; current page always has its neighbours visible
function pageList(page, pageCount) {
  if (pageCount <= MAX_BUTTONS) return Array.from({ length: pageCount }, (_, i) => i + 1)
  const pages = [...new Set([1, page - 1, page, page + 1, pageCount])]
    .filter((p) => p >= 1 && p <= pageCount)
    .sort((a, b) => a - b)
  return pages.flatMap((p, i) => (i > 0 && p - pages[i - 1] > 1 ? [null, p] : [p]))
}

export const pageCountOf = (total, pageSize) => Math.max(1, Math.ceil(total / pageSize))

export default function Pagination({ page, pageSize, total, onChange }) {
  const pageCount = pageCountOf(total, pageSize)
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="pagination__summary">{from} to {to} of {total} results</span>
      <div className="pagination__pages">
        <button className="pagination__btn" disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ Prev</button>
        {pageList(page, pageCount).map((p, i) =>
          p === null ? (
            <span key={`gap-${i}`} className="pagination__gap">…</span>
          ) : (
            <button
              key={p}
              className={p === page ? 'pagination__btn is-active' : 'pagination__btn'}
              aria-current={p === page ? 'page' : undefined}
              onClick={() => onChange(p)}
            >
              {p}
            </button>
          ),
        )}
        <button className="pagination__btn" disabled={page >= pageCount} onClick={() => onChange(page + 1)}>Next ›</button>
      </div>
    </nav>
  )
}
