import { useEffect, useState } from 'react'

import { adminApi } from '../api/adminApi'
import StatusBadge from '../components/common/StatusBadge'
import { formatDateTime } from '../utils/time'

const initialUserForm = {
  username: '',
  email: '',
  password: '',
  role: 'viewer',
  employee_id: '',
}

export default function AdminPage() {
  const [overview, setOverview] = useState(null)
  const [logs, setLogs] = useState([])
  const [users, setUsers] = useState([])
  const [config, setConfig] = useState({
    recognition_threshold: 0.65,
    kiosk_allowed_devices: '',
  })
  const [userForm, setUserForm] = useState(initialUserForm)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function loadAdminData() {
    setLoading(true)
    setError('')
    try {
      const [overviewRes, logsRes, usersRes, configRes] = await Promise.all([
        adminApi.overview(),
        adminApi.accessLogs(80),
        adminApi.users(),
        adminApi.config(),
      ])
      setOverview(overviewRes.data)
      setLogs(logsRes.data)
      setUsers(usersRes.data)
      setConfig(configRes.data)
    } catch (err) {
      setError(err.message || 'Cannot load admin data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAdminData()
  }, [])

  function updateUserForm(field, value) {
    setUserForm((prev) => ({ ...prev, [field]: value }))
  }

  async function createUser(event) {
    event.preventDefault()
    setError('')
    setMessage('')

    try {
      await adminApi.createUser({
        ...userForm,
        employee_id: userForm.employee_id ? Number(userForm.employee_id) : null,
      })
      setUserForm(initialUserForm)
      setMessage('User created')
      await loadAdminData()
    } catch (err) {
      setError(err.message || 'Cannot create user')
    }
  }

  async function toggleUser(user) {
    setError('')
    setMessage('')
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active })
      setMessage(`${user.username} ${user.is_active ? 'disabled' : 'enabled'}`)
      await loadAdminData()
    } catch (err) {
      setError(err.message || 'Cannot update user')
    }
  }

  async function changeUserRole(user, role) {
    setError('')
    setMessage('')
    try {
      await adminApi.updateUser(user.id, { role })
      setMessage(`${user.username} role updated`)
      await loadAdminData()
    } catch (err) {
      setError(err.message || 'Cannot update user role')
    }
  }

  function updateConfigField(field, value) {
    setConfig((prev) => ({ ...prev, [field]: value }))
  }

  async function saveConfig(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      const response = await adminApi.updateConfig({
        recognition_threshold: Number(config.recognition_threshold),
        kiosk_allowed_devices: config.kiosk_allowed_devices || '',
      })
      setConfig(response.data)
      setMessage('System config saved')
    } catch (err) {
      setError(err.message || 'Cannot save system config')
    }
  }

  return (
    <section className="page">
      <div className="page-title-row">
        <div>
          <h1>IT Administration</h1>
          <p>Monitor access events, manage accounts, and tune kiosk recognition settings.</p>
        </div>
        <button className="btn secondary" type="button" onClick={loadAdminData} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}
      {message && <p>{message}</p>}

      {overview && (
        <div className="grid stats-grid">
          <div className="card stat-card">
            <h3>Active Employees</h3>
            <p>{overview.employees_active}</p>
            <small>Total {overview.employees_total}</small>
          </div>
          <div className="card stat-card">
            <h3>Active Users</h3>
            <p>{overview.users_active}</p>
            <small>Total {overview.users_total}</small>
          </div>
          <div className="card stat-card">
            <h3>Check In</h3>
            <p>{overview.check_in_events}</p>
            <small>Recorded events</small>
          </div>
          <div className="card stat-card">
            <h3>Devices</h3>
            <p>{overview.devices_seen}</p>
            <small>Seen in logs</small>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Employee Access Logs</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Employee</th>
              <th>Code</th>
              <th>Action</th>
              <th>Status</th>
              <th>Device</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((item) => (
              <tr key={item.id}>
                <td>{formatDateTime(item.event_time)}</td>
                <td>{item.employee_name}</td>
                <td>{item.employee_code}</td>
                <td><StatusBadge value={item.action_type} /></td>
                <td><StatusBadge value={item.status} /></td>
                <td>{item.device_id}</td>
                <td>{item.score.toFixed ? item.score.toFixed(2) : item.score}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan="7">No access logs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <form className="card" onSubmit={saveConfig}>
        <h3>System Config</h3>
        <div className="detail-grid">
          <label>
            Recognition Threshold
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={config.recognition_threshold}
              onChange={(event) => updateConfigField('recognition_threshold', event.target.value)}
            />
          </label>
          <label>
            Allowed Kiosk Device IDs
            <input
              value={config.kiosk_allowed_devices}
              onChange={(event) => updateConfigField('kiosk_allowed_devices', event.target.value)}
              placeholder="kiosk_front_gate_1,camera_front_door_1"
            />
          </label>
        </div>
        <button className="btn" type="submit">Save Config</button>
      </form>

      <form className="card" onSubmit={createUser}>
        <h3>Create User</h3>
        <div className="detail-grid">
          <label>
            Username
            <input value={userForm.username} onChange={(event) => updateUserForm('username', event.target.value)} required />
          </label>
          <label>
            Email
            <input value={userForm.email} onChange={(event) => updateUserForm('email', event.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={userForm.password} onChange={(event) => updateUserForm('password', event.target.value)} required />
          </label>
          <label>
            Role
            <select value={userForm.role} onChange={(event) => updateUserForm('role', event.target.value)}>
              <option value="viewer">viewer</option>
              <option value="manager">manager</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <label>
            Linked Employee ID
            <input value={userForm.employee_id} onChange={(event) => updateUserForm('employee_id', event.target.value)} />
          </label>
        </div>
        <button className="btn" type="submit">Create User</button>
      </form>

      <div className="card">
        <h3>User Accounts</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Employee ID</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>{user.email}</td>
                <td>
                  <select value={user.role} onChange={(event) => changeUserRole(user, event.target.value)}>
                    <option value="viewer">viewer</option>
                    <option value="manager">manager</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td><StatusBadge value={user.is_active ? 'active' : 'inactive'} /></td>
                <td>{user.employee_id || '-'}</td>
                <td>
                  <button className="btn-link" type="button" onClick={() => toggleUser(user)}>
                    {user.is_active ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
