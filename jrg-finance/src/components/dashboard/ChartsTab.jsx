/**
 * ChartsTab — two chart sections:
 *   1. Per-ticker price history (line + optional volume bars + optional S&P 500 overlay)
 *   2. Portfolio vs S&P 500 normalized % return comparison (all tickers + benchmark)
 *
 * Chart library: Recharts — chosen because it's a first-class React library that
 * integrates cleanly with Vite (ESM-native, no canvas polyfills needed).
 */

import { useEffect, useState, useCallback } from 'react'
import {
  ComposedChart,
  LineChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { getHistoricalData, getSP500History } from '../../api/client'
import { usePortfolio } from '../../hooks/usePortfolio'
import Card from '../common/Card'
import Button from '../common/Button'
import EmptyState from '../common/EmptyState'
import './ChartsTab.css'

const PERIODS = [
  { value: '1d',  label: '1D' },
  { value: '5d',  label: '5D' },
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y',  label: '1Y' },
]

// Palette for comparison chart lines (first entry = first portfolio ticker, etc.)
const LINE_COLORS = ['#0D5C6A', '#F59E0B', '#10B981', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4']
const SP500_COLOR = '#94A3B8'  // slate-gray — visually distinct from all portfolio colors

function fmtPrice(v) {
  if (v == null) return ''
  return `$${Number(v).toFixed(2)}`
}

function fmtPct(v) {
  if (v == null) return ''
  return `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`
}

// Normalise a series of {Close, Date} records to % return from the first close
function normalise(data) {
  const first = data.find((d) => d.Close != null)?.Close
  if (!first) return {}
  return Object.fromEntries(
    data.map((d) => [d.Date, d.Close != null ? Number(((d.Close - first) / first) * 100) : null])
  )
}

// ── Price-history tooltip ─────────────────────────────────────────────────────

function PriceTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart__tooltip">
      <p className="chart__tooltip-date">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} style={{ color: entry.color }}>
          {entry.name}:{' '}
          {entry.dataKey === 'Volume'
            ? Number(entry.value).toLocaleString()
            : fmtPrice(entry.value)}
        </p>
      ))}
    </div>
  )
}

// ── Comparison tooltip ────────────────────────────────────────────────────────

function CompTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart__tooltip">
      <p className="chart__tooltip-date">{label}</p>
      {payload
        .filter((e) => e.value != null)
        .map((entry) => (
          <p key={entry.dataKey} style={{ color: entry.color }}>
            {entry.name}: {fmtPct(entry.value)}
          </p>
        ))}
    </div>
  )
}

// ── Period selector (shared) ──────────────────────────────────────────────────

function PeriodSelector({ value, onChange }) {
  return (
    <div className="charts__period-list">
      {PERIODS.map(({ value: v, label }) => (
        <button
          key={v}
          className={`charts__period-btn ${value === v ? 'charts__period-btn--active' : ''}`}
          onClick={() => onChange(v)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

// ── Section 1: Per-ticker price history ───────────────────────────────────────

function PriceHistoryChart({ tickers, portLoading }) {
  const [selectedTicker, setSelectedTicker] = useState('')
  const [period, setPeriod]     = useState('1mo')
  const [showSP500, setShowSP500]   = useState(false)
  const [showVolume, setShowVolume] = useState(true)

  const [chartData, setChartData] = useState([])
  const [sp500Raw, setSp500Raw]   = useState([])
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)

  useEffect(() => {
    if (tickers.length > 0 && !selectedTicker) setSelectedTicker(tickers[0])
  }, [tickers, selectedTicker])

  const fetchData = useCallback(async () => {
    if (!selectedTicker) return
    setLoading(true)
    setError(null)
    try {
      const [stockRes, spRes] = await Promise.all([
        getHistoricalData(selectedTicker, period),
        showSP500 ? getSP500History(period) : Promise.resolve({ data: [] }),
      ])
      const stock = stockRes.data || []
      const sp    = spRes.data    || []
      const spMap = Object.fromEntries(sp.map((d) => [d.Date, d.Close]))
      setChartData(stock.map((d) => ({ ...d, SP500: spMap[d.Date] ?? null })))
      setSp500Raw(sp)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load chart data')
    } finally {
      setLoading(false)
    }
  }, [selectedTicker, period, showSP500])

  useEffect(() => { fetchData() }, [fetchData])

  return (
    <Card
      title={
        selectedTicker
          ? `${selectedTicker} — ${PERIODS.find((p) => p.value === period)?.label}`
          : 'Price history'
      }
      action={
        <Button variant="text" size="sm" onClick={fetchData} disabled={loading}>
          Refresh
        </Button>
      }
    >
      {/* Controls */}
      <div className="charts__controls">
        <div className="charts__control-group">
          <label className="charts__control-label">Stock</label>
          <div className="charts__ticker-list">
            {portLoading ? (
              <span className="charts__loading-text">Loading…</span>
            ) : (
              tickers.map((t) => (
                <button
                  key={t}
                  className={`charts__ticker-btn ${selectedTicker === t ? 'charts__ticker-btn--active' : ''}`}
                  onClick={() => setSelectedTicker(t)}
                >
                  {t}
                </button>
              ))
            )}
          </div>
        </div>

        <div className="charts__control-group">
          <label className="charts__control-label">Period</label>
          <PeriodSelector value={period} onChange={setPeriod} />
        </div>

        <div className="charts__control-group charts__toggles">
          <button
            className={`charts__toggle ${showSP500 ? 'charts__toggle--on' : ''}`}
            onClick={() => setShowSP500((v) => !v)}
          >
            S&amp;P 500 overlay
          </button>
          <button
            className={`charts__toggle ${showVolume ? 'charts__toggle--on' : ''}`}
            onClick={() => setShowVolume((v) => !v)}
          >
            Volume
          </button>
        </div>
      </div>

      {/* Chart */}
      {error && <p className="charts__error">{error}</p>}
      {loading ? (
        <div className="charts__skeleton">
          <span className="charts__spinner" /> Loading chart data…
        </div>
      ) : chartData.length === 0 ? (
        <EmptyState icon="📊" title="No data" description="No price data available for this period." />
      ) : (
        <div className="charts__chart-wrap">
          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DDE5ED" vertical={false} />
              <XAxis
                dataKey="Date"
                tick={{ fontSize: 11, fontFamily: 'DM Sans', fill: '#5A7080' }}
                tickLine={false}
                axisLine={false}
                minTickGap={40}
              />
              <YAxis
                yAxisId="price"
                orientation="left"
                tickFormatter={(v) => `$${v.toFixed(0)}`}
                tick={{ fontSize: 11, fontFamily: 'DM Sans', fill: '#5A7080' }}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              {showVolume && (
                <YAxis
                  yAxisId="vol"
                  orientation="right"
                  tickFormatter={(v) =>
                    v >= 1e6 ? `${(v / 1e6).toFixed(0)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : v
                  }
                  tick={{ fontSize: 11, fontFamily: 'DM Sans', fill: '#5A7080' }}
                  tickLine={false}
                  axisLine={false}
                  width={50}
                />
              )}
              <Tooltip content={<PriceTooltip />} />
              <Legend wrapperStyle={{ fontFamily: 'DM Sans', fontSize: 13, paddingTop: 12 }} />
              {showVolume && (
                <Bar yAxisId="vol" dataKey="Volume" fill="#DDE5ED" name="Volume" opacity={0.6} radius={[2, 2, 0, 0]} />
              )}
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="Close"
                stroke="#0D5C6A"
                strokeWidth={2}
                dot={false}
                name={selectedTicker}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
              {showSP500 && sp500Raw.length > 0 && (
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="SP500"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={false}
                  strokeDasharray="6 3"
                  name="S&P 500"
                  activeDot={{ r: 4, strokeWidth: 0 }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}

// ── Section 2: Portfolio vs S&P 500 normalised % return ───────────────────────

function ComparisonChart({ tickers }) {
  const [period, setPeriod] = useState('1mo')
  const [compData, setCompData] = useState([])
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)

  const fetchComparison = useCallback(async () => {
    if (tickers.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const [spRes, ...tickerReses] = await Promise.all([
        getSP500History(period),
        ...tickers.map((t) => getHistoricalData(t, period)),
      ])

      const spRaw      = spRes.data      || []
      const tickerRaws = tickerReses.map((r) => r.data || [])

      // Normalise each series
      const spNorm      = normalise(spRaw)
      const tickerNorms = tickerRaws.map((raw) => normalise(raw))

      // Use S&P 500 dates as the reference timeline
      const merged = spRaw.map((d) => {
        const row = { date: d.Date, 'S&P 500': spNorm[d.Date] ?? null }
        tickers.forEach((t, i) => {
          row[t] = tickerNorms[i][d.Date] ?? null
        })
        return row
      })

      setCompData(merged)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load comparison data')
    } finally {
      setLoading(false)
    }
  }, [tickers, period])

  useEffect(() => { fetchComparison() }, [fetchComparison])

  const allKeys = ['S&P 500', ...tickers]
  const colorFor = (key) =>
    key === 'S&P 500' ? SP500_COLOR : LINE_COLORS[tickers.indexOf(key) % LINE_COLORS.length]

  return (
    <Card
      title="Portfolio vs S&P 500 — % return"
      action={
        <div className="charts__controls charts__controls--inline">
          <PeriodSelector value={period} onChange={setPeriod} />
          <Button variant="text" size="sm" onClick={fetchComparison} disabled={loading}>
            Refresh
          </Button>
        </div>
      }
    >
      <p className="charts__comp-note">
        Normalised to 0% at the start of the selected period. Each line shows cumulative % return.
      </p>

      {error && <p className="charts__error">{error}</p>}
      {loading ? (
        <div className="charts__skeleton">
          <span className="charts__spinner" /> Loading comparison data…
        </div>
      ) : compData.length === 0 ? (
        <EmptyState icon="📉" title="No data" description="No comparison data available for this period." />
      ) : (
        <div className="charts__chart-wrap">
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={compData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DDE5ED" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fontFamily: 'DM Sans', fill: '#5A7080' }}
                tickLine={false}
                axisLine={false}
                minTickGap={40}
              />
              <YAxis
                tickFormatter={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(0)}%`}
                tick={{ fontSize: 11, fontFamily: 'DM Sans', fill: '#5A7080' }}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              <ReferenceLine y={0} stroke="#DDE5ED" strokeWidth={1.5} />
              <Tooltip content={<CompTooltip />} />
              <Legend wrapperStyle={{ fontFamily: 'DM Sans', fontSize: 13, paddingTop: 12 }} />
              {allKeys.map((key) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={colorFor(key)}
                  strokeWidth={key === 'S&P 500' ? 1.5 : 2}
                  strokeDasharray={key === 'S&P 500' ? '6 3' : undefined}
                  dot={false}
                  connectNulls
                  activeDot={{ r: 4, strokeWidth: 0 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}

// ── Page shell ────────────────────────────────────────────────────────────────

export default function ChartsTab() {
  const { tickers, loading: portLoading, fetchPortfolio } = usePortfolio()

  useEffect(() => { fetchPortfolio() }, [fetchPortfolio])

  if (!portLoading && tickers.length === 0) {
    return (
      <div className="charts">
        <div className="charts__header">
          <h1 className="charts__title">Charts</h1>
        </div>
        <Card>
          <EmptyState
            icon="📉"
            title="No stocks in portfolio"
            description="Add stocks in the Portfolio tab to view their charts here."
          />
        </Card>
      </div>
    )
  }

  return (
    <div className="charts">
      <div className="charts__header">
        <h1 className="charts__title">Charts</h1>
        <p className="charts__subtitle">Price history and market comparison</p>
      </div>

      <PriceHistoryChart tickers={tickers} portLoading={portLoading} />
      <ComparisonChart tickers={tickers} />
    </div>
  )
}
