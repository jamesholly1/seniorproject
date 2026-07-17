/**
 * API client for JRG Trading backend (REST API at http://localhost:5000).
 * All paths are relative — Vite proxies /api/* to the backend.
 *
 * Auth: Bearer token injected automatically from sessionStorage.
 * On 401, token is cleared and the user is redirected to /login.
 *
 * Endpoints marked TODO need shape confirmation from the backend team.
 */

import axios from 'axios'

// ── HTTP instance ─────────────────────────────────────────────────────────────

const http = axios.create({
  baseURL: '/',
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('auth_token') || localStorage.getItem('auth_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      sessionStorage.removeItem('auth_token')
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default http   // keep default export so existing imports still work

// ── Auth ──────────────────────────────────────────────────────────────────────

export const login = (username, password) =>
  http.post('/api/auth/login', { username, password }).then((r) => r.data)

export const register = (username, email, password) =>
  http.post('/api/auth/register', { username, email, password }).then((r) => r.data)

export const logout = () => {
  sessionStorage.removeItem('auth_token')
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_user')
}

export const getMe = () =>
  http.get('/api/auth/me').then((r) => r.data)

// ── Portfolio ─────────────────────────────────────────────────────────────────

export const getPortfolioTickers = () =>
  http.get('/api/portfolio').then((r) => r.data.tickers)

export const addTicker = (ticker) =>
  http.post('/api/portfolio/add', { ticker: ticker.toUpperCase() }).then((r) => r.data)

export const removeTicker = (ticker) =>
  http.delete(`/api/portfolio/${ticker.toUpperCase()}`).then((r) => r.data)

export const clearAllTickers = () =>
  http.delete('/api/portfolio').then((r) => r.data)

// ── Stock data ────────────────────────────────────────────────────────────────

export const getStockInfo = (ticker) =>
  http.get(`/api/stocks/${ticker.toUpperCase()}`).then((r) => r.data)

// TODO: confirm batch endpoint shape with backend team.
// Proposed: GET /api/stocks/batch?tickers=AAPL,MSFT → { results: { AAPL: {...}, MSFT: {...} } }
export const getMultipleStockInfo = (tickers) =>
  http.get('/api/stocks/batch', { params: { tickers: tickers.join(',') } }).then((r) => r.data.results)

export const getHistoricalData = (ticker, period = '1mo') =>
  http.get(`/api/stocks/${ticker.toUpperCase()}/history`, { params: { period } }).then((r) => r.data)

export const getSP500History = (period = '1mo') =>
  http.get('/api/charts/sp500', { params: { period } }).then((r) => r.data)

// ── Notification thresholds ───────────────────────────────────────────────────
// TODO: all notification endpoints need shape confirmation from backend team.
// Proposed shapes are based on the Streamlit database schema:
//   add_notification_threshold(user_id, ticker, threshold_type, threshold_price)
//   → POST /api/notifications  { ticker, threshold_type: 'above'|'below', threshold_price }
//   → returns the created threshold object with { id, ticker, threshold_type, threshold_price,
//              is_active, triggered, created_at }
//
//   get_user_notification_thresholds(user_id)
//   → GET /api/notifications
//   → returns { thresholds: [...] }
//
//   delete_notification_threshold(threshold_id)
//   → DELETE /api/notifications/:id
//
//   update_notification_threshold_status(threshold_id, is_active)
//   → PATCH /api/notifications/:id/status  { is_active: bool }
//
//   reset_threshold_trigger(threshold_id)
//   → POST /api/notifications/:id/reset

export const getNotificationThresholds = () =>
  http.get('/api/notifications').then((r) => r.data.thresholds)

export const addNotificationThreshold = (ticker, price, direction) =>
  http
    .post('/api/notifications', {
      ticker: ticker.toUpperCase(),
      threshold_type: direction,  // 'above' | 'below'
      threshold_price: Number(price),
    })
    .then((r) => r.data)

export const deleteNotificationThreshold = (id) =>
  http.delete(`/api/notifications/${id}`).then((r) => r.data)

export const updateThresholdStatus = (id, isActive) =>
  http.patch(`/api/notifications/${id}/status`, { is_active: isActive }).then((r) => r.data)

export const resetThresholdTrigger = (id) =>
  http.post(`/api/notifications/${id}/reset`).then((r) => r.data)
