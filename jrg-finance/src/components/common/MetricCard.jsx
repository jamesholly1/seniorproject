import './MetricCard.css'

export default function MetricCard({ value, label, icon, trend, trendLabel }) {
  const isPositive = trend > 0
  const isNegative = trend < 0

  return (
    <div className="metric-card">
      {icon && <div className="metric-card__icon">{icon}</div>}
      <div className="metric-card__value">{value}</div>
      <div className="metric-card__label">{label}</div>
      {trend !== undefined && trend !== null && (
        <div
          className={`metric-card__trend ${
            isPositive ? 'metric-card__trend--up' : isNegative ? 'metric-card__trend--down' : ''
          }`}
        >
          {isPositive ? '▲' : isNegative ? '▼' : '—'}{' '}
          {trendLabel ?? `${Math.abs(trend).toFixed(2)}%`}
        </div>
      )}
    </div>
  )
}
