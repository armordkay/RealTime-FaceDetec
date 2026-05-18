import { useEffect, useState } from 'react'

import { employeeApi } from '../api/employeeApi'
import { navigate } from '../routes/router'
import StatusBadge from '../components/common/StatusBadge'

const initialForm = {
  employee_code: '',
  full_name: '',
  email: '',
  phone: '',
  department: '',
  position: '',
}

export default function EmployeesPage() {
  const [search, setSearch] = useState('')
  const [data, setData] = useState({ items: [], pagination: null })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [form, setForm] = useState(initialForm)

  async function fetchEmployees(query = '') {
    setLoading(true)
    setError('')
    try {
      const response = await employeeApi.list({ page: 1, page_size: 30, search: query })
      setData(response.data)
    } catch (err) {
      setError(err.message || 'Cannot load employees')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEmployees()
  }, [])

  function handleSearch(event) {
    event.preventDefault()
    fetchEmployees(search)
  }

  function handleFormChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleCreate(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')

    try {
      const response = await employeeApi.create(form)
      setMessage(`Employee ${response.data.full_name} created`)
      setForm(initialForm)
      await fetchEmployees(search)
    } catch (err) {
      setError(err.message || 'Cannot create employee')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="page">
      <h1>Employees & Enrollment Setup</h1>
      <p>Create employee first, then open detail page to capture face images from camera.</p>

      {error && <p className="error-text">{error}</p>}
      {message && <p className="success-text">{message}</p>}

      <form className="card" onSubmit={handleCreate}>
        <h3>Create New Employee</h3>
        <div className="detail-grid">
          <label>
            Employee Code
            <input value={form.employee_code} onChange={(event) => handleFormChange('employee_code', event.target.value)} required />
          </label>

          <label>
            Full Name
            <input value={form.full_name} onChange={(event) => handleFormChange('full_name', event.target.value)} required />
          </label>

          <label>
            Email
            <input value={form.email} onChange={(event) => handleFormChange('email', event.target.value)} required />
          </label>

          <label>
            Phone
            <input value={form.phone} onChange={(event) => handleFormChange('phone', event.target.value)} />
          </label>

          <label>
            Department
            <input value={form.department} onChange={(event) => handleFormChange('department', event.target.value)} required />
          </label>

          <label>
            Position
            <input value={form.position} onChange={(event) => handleFormChange('position', event.target.value)} />
          </label>
        </div>

        <button type="submit" className="btn" disabled={saving}>
          {saving ? 'Creating...' : 'Create Employee'}
        </button>
      </form>

      <form className="inline-form" onSubmit={handleSearch}>
        <input
          placeholder="Search by name, code, email"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <button type="submit" className="btn" disabled={loading}>
          {loading ? 'Loading...' : 'Search'}
        </button>
      </form>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Department</th>
              <th>Status</th>
              <th>Face Samples</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((employee) => (
              <tr key={employee.id}>
                <td>{employee.employee_code}</td>
                <td>{employee.full_name}</td>
                <td>{employee.department}</td>
                <td>
                  <StatusBadge value={employee.status} />
                </td>
                <td>{employee.enrolled_samples}</td>
                <td>
                  <button className="btn-link" onClick={() => navigate(`/employees/${employee.id}`)}>
                    Open Detail / Enroll Face
                  </button>
                </td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr>
                <td colSpan="6">No employees found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
