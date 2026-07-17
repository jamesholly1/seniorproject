import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { useAuth } from './hooks/useAuth'
import MainLayout from './components/layout/MainLayout'
import DashboardTab from './components/dashboard/DashboardTab'
import PortfolioTab from './components/dashboard/PortfolioTab'
import ChartsTab from './components/dashboard/ChartsTab'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

function ComingSoon({ name }) {
  return (
    <div style={{ padding: '48px 24px', textAlign: 'center' }}>
      <p style={{ fontSize: 40, marginBottom: 16 }}>🚧</p>
      <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 24, marginBottom: 8 }}>
        {name} — Coming Soon
      </h2>
      <p style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>
        This tab is under construction in Phase 3.
      </p>
    </div>
  )
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <span style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>Loading…</span>
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return null
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />

          {/* Protected shell */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardTab />} />
            <Route path="portfolio" element={<PortfolioTab />} />
            <Route path="charts" element={<ChartsTab />} />
            <Route path="news" element={<ComingSoon name="News" />} />
            <Route path="notifications" element={<ComingSoon name="Notifications" />} />
            <Route path="learn" element={<ComingSoon name="Learn" />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
