import { NavLink } from 'react-router-dom'
import './Navigation.css'

const TABS = [
  { path: '/dashboard', label: 'Dashboard', icon: '◼' },
  { path: '/portfolio', label: 'Portfolio', icon: '◈' },
  { path: '/charts', label: 'Charts', icon: '◉' },
  { path: '/news', label: 'News', icon: '◎', soon: true },
  { path: '/notifications', label: 'Notifications', icon: '◇', soon: true },
  { path: '/learn', label: 'Learn', icon: '◌', soon: true },
]

export default function Navigation({ mobile = false, onClose }) {
  return (
    <nav className={`nav ${mobile ? 'nav--mobile' : 'nav--desktop'}`}>
      {TABS.map(({ path, label, icon, soon }) => (
        <NavLink
          key={path}
          to={path}
          className={({ isActive }) =>
            `nav__tab ${isActive ? 'nav__tab--active' : ''} ${soon ? 'nav__tab--soon' : ''}`
          }
          onClick={mobile && !soon ? onClose : undefined}
          title={soon ? 'Coming soon' : undefined}
        >
          <span className="nav__icon" aria-hidden="true">{icon}</span>
          <span className="nav__label">{label}</span>
          {soon && <span className="nav__soon">Soon</span>}
        </NavLink>
      ))}
    </nav>
  )
}
