import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import Input from '../components/common/Input'
import Button from '../components/common/Button'
import './AuthPage.css'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.username || !form.email || !form.password) {
      setError('Please fill in all fields.')
      return
    }
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setLoading(true)
    try {
      await apiClient.post('/api/auth/register', {
        username: form.username,
        email: form.email,
        password: form.password,
      })
      navigate('/login', { state: { registered: true } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span className="auth-card__brand-mark">JRG</span>
          <span className="auth-card__brand-text">Trading</span>
        </div>
        <h1 className="auth-card__title">Create account</h1>
        <p className="auth-card__subtitle">Start tracking your portfolio</p>

        {error && <div className="auth-card__error">{error}</div>}

        <form className="auth-card__form" onSubmit={handleSubmit} noValidate>
          <Input
            label="Username"
            type="text"
            placeholder="choose a username"
            value={form.username}
            onChange={set('username')}
            autoComplete="username"
            required
          />
          <Input
            label="Email"
            type="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={set('email')}
            autoComplete="email"
            required
          />
          <Input
            label="Password"
            type="password"
            placeholder="at least 6 characters"
            value={form.password}
            onChange={set('password')}
            autoComplete="new-password"
            required
          />
          <Input
            label="Confirm password"
            type="password"
            placeholder="repeat password"
            value={form.confirm}
            onChange={set('confirm')}
            autoComplete="new-password"
            required
          />
          <Button type="submit" variant="primary" size="lg" loading={loading} className="auth-card__submit">
            Create account
          </Button>
        </form>

        <p className="auth-card__footer">
          Already have an account?{' '}
          <Link to="/login" className="auth-card__link">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
