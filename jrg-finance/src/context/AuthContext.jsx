import { createContext, useState, useEffect } from 'react'
import apiClient from '../api/client'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('auth_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setLoading(false)
      return
    }
    apiClient
      .get('/api/auth/me')
      .then((res) => {
        const u = { id: res.data.id, username: res.data.username, email: res.data.email }
        setUser(u)
        localStorage.setItem('auth_user', JSON.stringify(u))
      })
      .catch(() => {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_user')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = async (username, password) => {
    const res = await apiClient.post('/api/auth/login', { username, password })
    const { token, user_id, username: uname } = res.data
    localStorage.setItem('auth_token', token)
    const u = { id: user_id, username: uname }
    localStorage.setItem('auth_user', JSON.stringify(u))
    setUser(u)
    return u
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
