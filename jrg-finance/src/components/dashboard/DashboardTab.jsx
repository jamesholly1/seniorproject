import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePortfolio } from '../../hooks/usePortfolio'
import { useNotifications, deriveStatus } from '../../hooks/useNotifications'
import MetricCard from '../common/MetricCard'
import Card from '../common/Card'
import Table from '../common/Table'
import EmptyState from '../common/EmptyState'
import Button from '../common/Button'
import Input from '../common/Input'
import StatusBadge from '../common/StatusBadge'
import './DashboardTab.css'

function fmtPrice(val) {
  if (val === 'N/A' || val == null) return '—'
  return `$${Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// ── Portfolio summary table ───────────────────────────────────────────────────

const HOLDING_COLS = [
  { key: 'symbol', label: 'Symbol', render: (r) => <strong className="dash__symbol">{r.symbol}</strong> },
  { key: 'name', label: 'Company' },
  { key: 'current_price', label: 'Price', render: (r) => fmtPrice(r.current_price) },
]

// ── Alert form ────────────────────────────────────────────────────────────────

function AlertForm({ tickers, onAdd }) {
  const [ticker, setTicker] = useState('')
  const [price, setPrice] = useState('')
  const [direction, setDirection] = useState('above')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const t = ticker.trim().toUpperCase() || tickers[0]
    const p = parseFloat(price)
    if (!t) { setError('Choose a ticker.'); return }
    if (!price || isNaN(p) || p <= 0) { setError('Enter a valid price.'); return }
    setLoading(true)
    try {
      await onAdd(t, p, direction)
      setPrice('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add alert.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="alert-form" onSubmit={handleSubmit} noValidate>
      <div className="alert-form__fields">
        {/* Ticker */}
        <div className="alert-form__field">
          <label className="alert-form__label">Ticker</label>
          {tickers.length > 0 ? (
            <select
              className="alert-form__select"
              value={ticker || tickers[0]}
              onChange={(e) => setTicker(e.target.value)}
            >
              {tickers.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          ) : (
            <input
              className="alert-form__input"
              placeholder="AAPL"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
            />
          )}
        </div>

        {/* Price */}
        <div className="alert-form__field">
          <label className="alert-form__label">Price ($)</label>
          <input
            className="alert-form__input"
            type="number"
            min="0.01"
            step="0.01"
            placeholder="150.00"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </div>

        {/* Direction */}
        <div className="alert-form__field">
          <label className="alert-form__label">Direction</label>
          <div className="alert-form__direction">
            <button
              type="button"
              className={`alert-form__dir-btn alert-form__dir-btn--above ${direction === 'above' ? 'alert-form__dir-btn--active' : ''}`}
              onClick={() => setDirection('above')}
            >
              ▲ Above
            </button>
            <button
              type="button"
              className={`alert-form__dir-btn alert-form__dir-btn--below ${direction === 'below' ? 'alert-form__dir-btn--active' : ''}`}
              onClick={() => setDirection('below')}
            >
              ▼ Below
            </button>
          </div>
        </div>

        <Button type="submit" variant="primary" size="md" loading={loading} className="alert-form__submit">
          Add alert
        </Button>
      </div>
      {error && <p className="alert-form__error">{error}</p>}
    </form>
  )
}

// ── Alert row actions ─────────────────────────────────────────────────────────

function AlertActions({ threshold, onToggle, onReset, onDelete }) {
  const [loadToggle, setLoadToggle] = useState(false)
  const [loadReset, setLoadReset] = useState(false)
  const [loadDelete, setLoadDelete] = useState(false)

  const status = deriveStatus(threshold)

  const wrap = (fn, setL) => async () => {
    setL(true)
    try { await fn() } finally { setL(false) }
  }

  return (
    <div className="alert-actions">
      <button
        className={`alert-actions__btn ${loadToggle ? 'alert-actions__btn--loading' : ''}`}
        onClick={wrap(() => onToggle(threshold.id, threshold.is_active), setLoadToggle)}
        disabled={loadToggle}
        title={status === 'active' ? 'Pause alert' : 'Resume alert'}
      >
        {status === 'active' ? 'Pause' : 'Resume'}
      </button>
      <button
        className={`alert-actions__btn ${loadReset ? 'alert-actions__btn--loading' : ''}`}
        onClick={wrap(() => onReset(threshold.id), setLoadReset)}
        disabled={loadReset || status !== 'triggered'}
        title="Reset triggered state"
      >
        Reset
      </button>
      <button
        className={`alert-actions__btn alert-actions__btn--danger ${loadDelete ? 'alert-actions__btn--loading' : ''}`}
        onClick={wrap(() => onDelete(threshold.id), setLoadDelete)}
        disabled={loadDelete}
        title="Delete alert"
      >
        Delete
      </button>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function DashboardTab() {
  const navigate = useNavigate()
  const { holdings, tickers, loading: portLoading, error: portError, fetchPortfolio } = usePortfolio()
  const { thresholds, loading: alertLoading, error: alertError, fetchThresholds, addThreshold, removeThreshold, toggleStatus, resetTrigger } = useNotifications()

  useEffect(() => {
    fetchPortfolio()
    fetchThresholds()
  }, [fetchPortfolio, fetchThresholds])

  // Portfolio metrics
  const totalStocks = holdings.length
  const validPrices = holdings.filter((h) => h.current_price !== 'N/A' && h.current_price != null)
  const totalValue = validPrices.reduce((sum, h) => sum + Number(h.current_price), 0)
  const avgPrice = validPrices.length > 0 ? totalValue / validPrices.length : null

  // Alert table columns
  const ALERT_COLS = [
    {
      key: 'ticker',
      label: 'Ticker',
      render: (r) => <strong className="dash__symbol">{r.ticker}</strong>,
    },
    {
      key: 'threshold_price',
      label: 'Alert price',
      render: (r) => fmtPrice(r.threshold_price),
    },
    {
      key: 'threshold_type',
      label: 'Direction',
      render: (r) => <StatusBadge status={r.threshold_type} />,
    },
    {
      key: 'status',
      label: 'Status',
      render: (r) => <StatusBadge status={deriveStatus(r)} />,
    },
    {
      key: '_actions',
      label: '',
      render: (r) => (
        <AlertActions
          threshold={r}
          onToggle={toggleStatus}
          onReset={resetTrigger}
          onDelete={removeThreshold}
        />
      ),
    },
  ]

  return (
    <div className="dash">
      <div className="dash__header">
        <h1 className="dash__title">Dashboard</h1>
        <p className="dash__subtitle">Your portfolio at a glance</p>
      </div>

      {/* Metric cards */}
      <div className="dash__metrics">
        <MetricCard value={totalStocks} label="Positions" icon="📊" />
        <MetricCard
          value={
            totalValue > 0
              ? `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : '—'
          }
          label="Sum of Prices"
          icon="💰"
        />
        <MetricCard
          value={avgPrice != null ? `$${avgPrice.toFixed(2)}` : '—'}
          label="Avg Price"
          icon="📈"
        />
      </div>

      {/* Holdings summary */}
      <Card title="Holdings">
        {portError && <p className="dash__error">{portError}</p>}
        {totalStocks === 0 && !portLoading ? (
          <EmptyState
            icon="📭"
            title="No stocks yet"
            description="Add stocks to your portfolio to see them here."
            action={
              <Button variant="primary" onClick={() => navigate('/portfolio')}>
                Add stocks
              </Button>
            }
          />
        ) : (
          <Table columns={HOLDING_COLS} data={holdings} loading={portLoading} />
        )}
      </Card>

      {/* Notifications panel */}
      <Card
        title="Price Alerts"
        action={
          <Button variant="text" size="sm" onClick={fetchThresholds} disabled={alertLoading}>
            Refresh
          </Button>
        }
      >
        <AlertForm tickers={tickers} onAdd={addThreshold} />

        <div className="dash__alerts-divider" />

        {alertError && (
          <p className="dash__error dash__error--note">
            {alertError} — alert endpoint may not be deployed yet.
          </p>
        )}

        {thresholds.length === 0 && !alertLoading ? (
          <EmptyState
            icon="🔔"
            title="No price alerts"
            description="Add an alert above to get notified when a stock hits your target price."
          />
        ) : (
          <Table
            columns={ALERT_COLS}
            data={thresholds}
            loading={alertLoading}
            emptyText="No alerts set"
          />
        )}
      </Card>
    </div>
  )
}
