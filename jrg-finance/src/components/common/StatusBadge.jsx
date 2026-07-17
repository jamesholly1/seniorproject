import './StatusBadge.css'

const META = {
  active:    { label: 'Active',    icon: null },
  triggered: { label: 'Triggered', icon: null },
  inactive:  { label: 'Inactive',  icon: null },
  above:     { label: 'Above',     icon: '▲' },
  below:     { label: 'Below',     icon: '▼' },
}

export default function StatusBadge({ status = 'inactive', label: labelOverride }) {
  const { label, icon } = META[status] ?? { label: status, icon: null }
  return (
    <span className={`status-badge status-badge--${status}`}>
      {icon ? (
        <span className="status-badge__icon">{icon}</span>
      ) : (
        <span className="status-badge__dot" />
      )}
      {labelOverride ?? label}
    </span>
  )
}
