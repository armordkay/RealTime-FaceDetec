import { useState } from 'react'

export default function LoginPage({ onSubmit, currentUser, onForceLogout }) {
  const defaultsByRole = {
    admin: { username: 'admin', password: 'admin123' },
    manager: { username: 'manager', password: 'manager123' },
  }

  const [role, setRole] = useState('admin')
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleRoleChange(nextRole) {
    setRole(nextRole)
    const defaults = defaultsByRole[nextRole]
    if (defaults) {
      setUsername(defaults.username)
      setPassword(defaults.password)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onSubmit(username, password, role)
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h1>Face Attendance</h1>
        <p>Admin and manager portal login</p>

        <label>
          Portal Role
          <select value={role} onChange={(event) => handleRoleChange(event.target.value)}>
            <option value="admin">Admin</option>
            <option value="manager">Manager</option>
            <option value="viewer">Viewer</option>
          </select>
        </label>

        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} required />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="btn" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign in'}
        </button>

        {currentUser && (
          <button type="button" className="btn secondary" onClick={onForceLogout}>
            Logout current account ({currentUser.username})
          </button>
        )}

        <small>admin/admin123 | manager/manager123</small>
        <small>
          Employee check-in screen: <a href="#/kiosk">#/kiosk</a>
        </small>
      </form>
    </div>
  )
}
