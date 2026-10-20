import './ColumnSettings.scss'

// "Columns" dropdown for a layout from useColumnLayout: show/hide, pin to the front, reorder
export default function ColumnSettings({ layout }) {
  const { items, toggleVisible, togglePin, move, reset, isCustom } = layout
  const movable = items.filter((item) => !item.pinned).map((item) => item.col.key)

  return (
    <details className="column-settings">
      <summary className="btn">Columns</summary>
      <div className="column-settings__menu card">
        <ul>
          {items.map(({ col, visible, pinned }) => {
            const i = movable.indexOf(col.key)
            return (
              <li key={col.key} className={pinned ? 'column-settings__item is-pinned' : 'column-settings__item'}>
                <label title={pinned ? 'Unpin to hide' : undefined}>
                  <input type="checkbox" checked={visible} disabled={pinned} onChange={() => toggleVisible(col.key)} />
                  {col.label}
                </label>
                <button
                  className={pinned ? 'btn btn--accent' : 'btn'}
                  aria-pressed={pinned}
                  title={pinned ? 'Unpin column' : 'Pin to the front (locks position and visibility)'}
                  onClick={() => togglePin(col.key)}
                >
                  {pinned ? 'Pinned' : 'Pin'}
                </button>
                <button
                  className="btn"
                  disabled={pinned || i <= 0}
                  aria-label={`Move ${col.label} left`}
                  onClick={() => move(col.key, movable[i - 1])}
                >
                  ↑
                </button>
                <button
                  className="btn"
                  disabled={pinned || i === movable.length - 1}
                  aria-label={`Move ${col.label} right`}
                  onClick={() => move(col.key, movable[i + 1])}
                >
                  ↓
                </button>
              </li>
            )
          })}
        </ul>
        <button className="btn" disabled={!isCustom} onClick={reset}>Reset to default</button>
      </div>
    </details>
  )
}
