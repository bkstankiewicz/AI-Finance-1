import { getJson } from './http.js'

const BASE = '/api/blotter'

// filters: { limit, book_id, asset_class, status, symbol, trade_id: [ids] }; empty values are skipped
export const getTrades = (filters = {}) => {
  const query = new URLSearchParams(
    Object.entries(filters)
      .flatMap(([key, value]) => (Array.isArray(value) ? value.map((v) => [key, v]) : [[key, value]]))
      .filter(([, value]) => value !== undefined && value !== null && value !== ''),
  )
  return getJson(`${BASE}/trades?${query}`).then((res) => res.trades)
}

// { trade, latest_valuation, valuation_history, audit_logs } or { error } (still HTTP 200) when no live valuation
export const getTradeDetails = (tradeId) => getJson(`${BASE}/trades/${encodeURIComponent(tradeId)}`)

export const getTradeAuditLogs = (tradeId) =>
  getJson(`${BASE}/trades/${encodeURIComponent(tradeId)}/audit-logs`).then((res) => res.audit_logs)

export const getBooksSummary = () => getJson(`${BASE}/books/summary`).then((res) => res.books)

// { count, minutes, errors: [{ created_at, service_name, event_type, message, ... }] }
export const getRecentErrors = (minutes = 5, limit = 10) =>
  getJson(`${BASE}/audit-logs/errors?minutes=${minutes}&limit=${limit}`)
