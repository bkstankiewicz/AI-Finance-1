import { getJson } from './http.js'

const BASE = '/api/monitoring'

export const getServiceStatus = () => getJson(`${BASE}/status`)

export const getServiceErrorCounter = (serviceName) =>
	getJson(`${BASE}/error-counter/${encodeURIComponent(serviceName)}`)

export const getLastErrorTimestamp = (serviceName) =>
	getJson(`${BASE}/last-error-timestamp/${encodeURIComponent(serviceName)}`)

export const openStatusStream = () => new EventSource(`${BASE}/stream`)
