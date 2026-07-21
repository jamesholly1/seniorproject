import { useEffect, useState } from 'react'
import { usePortfolio } from '../../hooks/usePortfolio'
import Card from '../common/Card'
import Table from '../common/Table'
import Input from '../common/Input'
import Button from '../common/Button'
import EmptyState from '../common/EmptyState'
import './PortfolioTab.css'

function fmt(val, prefix = '$') {
  if (val === 'N/A' || val == null) return '—'
  return `${prefix}${Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function PortfolioTab() {
  const { holdings, loading, error, fetchPortfolio, addTicker, removeTicker, clearAll } =
    usePortfolio()

  const [ticker, setTicker] = useState('')
  const [addError, setAddError] = useState('')
  const [addLoading, setAddLoading] = useState(false)
  const [removeLoading, setRemoveLoading] = useState(null)
  const [clearLoading, setClearLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    fetchPortfolio()
  }, [fetchPortfolio])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    const t = ticker.trim().toUpperCase()
    if (!t) { setAddError('Enter a ticker symbol.'); return }
    if (!/^[A-Z.\-^]{1,10}$/.test(t)) { setAddError('Invalid ticker format.'); return }
    setAddError('')
    setAddLoading(true)
    try {
      await addTicker(t)
      setTicker('')
      showToast(`${t} added to portfolio`)
    } catch (err) {
      setAddError(err.response?.data?.detail || 'Could not add ticker.')
    } finally {
      setAddLoading(false)
    }
  }

  const handleRemove = async (sym) => {
    setRemoveLoading(sym)
    try {
      await removeTicker(sym)
      showToast(`${sym} removed`, 'info')
    } catch {
      showToast('Failed to remove ticker', 'error')
    } finally {
      setRemoveLoading(null)
    }
  }

  const handleClearAll = async () => {
    setShowConfirm(false)
    setClearLoading(true)
    try {
      await clearAll()
      showToast('Portfolio cleared', 'info')
    } catch {
      showToast('Failed to clear portfolio', 'error')
    } finally {
      setClearLoading(false)
    }
  }

  const columns = [
    { key: 'symbol', label: 'Symbol', render: (r) => <strong className="port__symbol">{r.symbol}</strong> },
    { key: 'name', label: 'Company' },
    { key: 'current_price', label: 'Price', render: (r) => fmt(r.current_price) },
    { key: 'fifty_two_week_high', label: '52W High', render: (r) => fmt(r.fifty_two_week_high) },
    { key: 'fifty_two_week_low', label: '52W Low', render: (r) => fmt(r.fifty_two_week_low) },
    {
      key: '_actions',
      label: '',
      render: (r) => (
        <Button
          variant="danger"
          size="sm"
          loading={removeLoading === r.symbol}
          onClick={() => handleRemove(r.symbol)}
        >
          Remove
        </Button>
      ),
    },
  ]

  return (
    <div className="port">
      {/* Toast */}
      {toast && (
        <div className={`port__toast port__toast--${toast.type}`}>
          {toast.msg}
        </div>
      )}

      <div className="port__header">
        <div>
          <h1 className="port__title">Portfolio</h1>
          <p className="port__subtitle">Manage your stock watchlist</p>
        </div>
        {holdings.length > 0 && (
          <Button
            variant="danger"
            size="sm"
            loading={clearLoading}
            onClick={() => setShowConfirm(true)}
          >
            Clear all
          </Button>
        )}
      </div>

      {/* Confirm modal */}
      {showConfirm && (
        <div className="port__overlay" onClick={() => setShowConfirm(false)}>
          <div className="port__modal" onClick={(e) => e.stopPropagation()}>
            <h3>Clear portfolio?</h3>
            <p>This will remove all {holdings.length} stocks from your portfolio.</p>
            <div className="port__modal-actions">
              <Button variant="secondary" onClick={() => setShowConfirm(false)}>Cancel</Button>
              <Button variant="danger" onClick={handleClearAll}>Yes, clear all</Button>
            </div>
          </div>
        </div>
      )}

      {/* Add stock */}
      <Card title="Add stock">
        <form className="port__add-form" onSubmit={handleAdd} noValidate>
          <Input
            placeholder="e.g. AAPL, MSFT, TSLA"
            value={ticker}
            onChange={(e) => { setTicker(e.target.value); setAddError('') }}
            error={addError}
          />
          <Button type="submit" variant="primary" loading={addLoading}>
            Add
          </Button>
        </form>
      </Card>

      {/* Holdings table */}
      <Card
        title={`Holdings (${holdings.length})`}
        action={
          !loading && holdings.length > 0 && (
            <Button variant="text" size="sm" onClick={fetchPortfolio}>
              Refresh
            </Button>
          )
        }
      >
        {error && <p className="port__error">{error}</p>}
        {holdings.length === 0 && !loading ? (
          <EmptyState
            icon="📋"
            title="No stocks yet"
            description="Add a stock ticker above to start building your portfolio."
          />
        ) : (
          <Table columns={columns} data={holdings} loading={loading} />
        )}
      </Card>
    </div>
  )
}
