import { useState } from 'react'
import { createBook, updateBook } from '../../api/books.js'
import { ASSET_CLASSES } from '../../constants.js'

const EMPTY_BOOK = { name: '', description: '', expected_asset_class: 'EQUITY', is_active: true }
const NAME_MAX = 100
const DESCRIPTION_MAX = 500

// Returns { field: message } - empty object = valid. Name is UNIQUE in the DB, so duplicates are caught here.
function validate(form, existingNames) {
  const errors = {}
  const name = form.name.trim()
  if (!name) errors.name = 'Name is required.'
  else if (name.length > NAME_MAX) errors.name = `Name must be at most ${NAME_MAX} characters.`
  else if (existingNames.some((n) => n.toLowerCase() === name.toLowerCase())) errors.name = 'A book with this name already exists.'
  if ((form.description ?? '').length > DESCRIPTION_MAX) {
    errors.description = `Description must be at most ${DESCRIPTION_MAX} characters.`
  }
  if (!ASSET_CLASSES.includes(form.expected_asset_class)) errors.expected_asset_class = 'Choose a valid asset class.'
  return errors
}

const describeSaveError = (err) => {
  if (err.kind === 'unavailable') return 'Books Service is down or unreachable – changes were not saved.'
  if (err.kind === 'validation' || err.kind === 'not-found') return `Rejected by Books Service: ${err.message}`
  return `Backend error: ${err.message}`
}

// existingNames: names of the other books (without the edited one)
export default function BookForm({ book, existingNames = [], onSaved, onCancel }) {
  const [form, setForm] = useState(book ?? EMPTY_BOOK)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setFieldErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault() // stop the browser's default full-page form submit
    const errors = validate(form, existingNames)
    setFieldErrors(errors)
    setError(null)
    if (Object.keys(errors).length) return

    setSaving(true)
    const payload = {
      name: form.name.trim(),
      description: form.description?.trim() ?? '',
      expected_asset_class: form.expected_asset_class,
      is_active: form.is_active,
    }
    try {
      if (book) {
        await updateBook(book.book_id, payload)
      } else {
        await createBook(payload)
        setForm(EMPTY_BOOK)
      }
      onSaved()
    } catch (err) {
      setError(describeSaveError(err))
    } finally {
      setSaving(false)
    }
  }

  const fieldError = (key) => fieldErrors[key] && <p className="error form__field-error">{fieldErrors[key]}</p>

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <label>
        Name
        <input
          className={fieldErrors.name ? 'input input--invalid' : 'input'}
          aria-invalid={Boolean(fieldErrors.name)}
          value={form.name}
          onChange={(e) => setField('name', e.target.value)}
        />
      </label>
      {fieldError('name')}
      <label>
        Description
        <input
          className={fieldErrors.description ? 'input input--invalid' : 'input'}
          aria-invalid={Boolean(fieldErrors.description)}
          value={form.description ?? ''}
          onChange={(e) => setField('description', e.target.value)}
        />
      </label>
      {fieldError('description')}
      <label>
        Asset Class
        <select
          className={fieldErrors.expected_asset_class ? 'input input--invalid' : 'input'}
          value={form.expected_asset_class}
          onChange={(e) => setField('expected_asset_class', e.target.value)}
        >
          {ASSET_CLASSES.map((assetClass) => <option key={assetClass}>{assetClass}</option>)}
        </select>
      </label>
      {fieldError('expected_asset_class')}
      <label>
        Active
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(e) => setField('is_active', e.target.checked)}
        />
      </label>

      {error && <p className="error">{error}</p>}

      <div className="form__actions">
        <button className="btn btn--primary" disabled={saving}>{saving ? 'Saving…' : book ? 'Save' : 'Create'}</button>
        {book && <button type="button" className="btn" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  )
}
