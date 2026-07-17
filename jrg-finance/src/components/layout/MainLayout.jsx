import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import Navigation from './Navigation'
import './MainLayout.css'

export default function MainLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="layout">
      {/* Header */}
      <header className="layout__header">
        <div className="layout__header-inner">
          <div className="layout__brand">
            <span className="layout__brand-mark">JRG</span>
            <span className="layout__brand-text">Trading</span>
          </div>

          <div className="layout__user">
            <span className="layout__username">{user?.username}</span>
            <button className="layout__logout" onClick={handleLogout}>
              Sign out
            </button>
            <button
              className="layout__hamburger"
              onClick={() => setMenuOpen((o) => !o)}
              aria-label="Toggle menu"
              aria-expanded={menuOpen}
            >
              <span />
              <span />
              <span />
            </button>
          </div>
        </div>
      </header>

      {/* Desktop tab navigation */}
      <div className="layout__nav-desktop">
        <Navigation />
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="layout__overlay" onClick={() => setMenuOpen(false)}>
          <div className="layout__drawer" onClick={(e) => e.stopPropagation()}>
            <div className="layout__drawer-header">
              <span className="layout__brand-mark">JRG</span>
              <span className="layout__brand-text">Trading</span>
              <button
                className="layout__drawer-close"
                onClick={() => setMenuOpen(false)}
                aria-label="Close menu"
              >
                ✕
              </button>
            </div>
            <Navigation mobile onClose={() => setMenuOpen(false)} />
            <div className="layout__drawer-footer">
              <span className="layout__username">{user?.username}</span>
              <button className="layout__logout" onClick={handleLogout}>
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Page content */}
      <main className="layout__main">
        <div className="layout__content">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
