import { useState } from 'react'
import { reportApi } from '../api/reportApi'

export default function ReportsPage() {
  const [daily, setDaily] = useState([])
  const [monthly, setMonthly] = useState(null)
  const [lateEmployees, setLateEmployees] = useState([])
  const [error, setError] = useState('')

  async function loadReports() {
    setError('')
    try {
      const [dailyRes, monthlyRes, lateRes] = await Promise.all([
        reportApi.daily(),
        reportApi.monthly(),
        reportApi.lateEmployees(),
      ])
      setDaily(dailyRes.data)
      setMonthly(monthlyRes.data)
      setLateEmployees(lateRes.data)
    } catch (err) {
      setError(err.message || 'Cannot load reports')
    }
  }

  async function exportCsv() {
    setError('')
    try {
      const response = await reportApi.exportCsv()
      const blob = new Blob([response.raw], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'attendance_report.csv'
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message || 'CSV export failed')
    }
  }

  return (
    <section className="page">
      <h1>Reports</h1>

      <div className="inline-form">
        <button className="btn" type="button" onClick={loadReports}>
          Load Reports
        </button>
        <button className="btn secondary" type="button" onClick={exportCsv}>
          Export CSV
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {monthly && (
        <div className="card">
          <h3>Monthly Summary</h3>
          <p>Month: {monthly.month}</p>
          <p>Recorded events: {monthly.recorded_events}</p>
          <p>Active employees: {monthly.employee_active}</p>
        </div>
      )}

      <div className="card">
        <h3>Daily Attendance</h3>
        <ul className="simple-list">
          {daily.map((item) => (
            <li key={item.employee_id}>
              {item.employee_name}: IN {item.check_in_count} / OUT {item.check_out_count}
            </li>
          ))}
          {daily.length === 0 && <li>No daily data loaded.</li>}
        </ul>
      </div>

      <div className="card">
        <h3>Late Employees</h3>
        <ul className="simple-list">
          {lateEmployees.map((item) => (
            <li key={item.employee_id}>
              {item.employee_name} ({item.late_count})
            </li>
          ))}
          {lateEmployees.length === 0 && <li>No late employee data loaded.</li>}
        </ul>
      </div>
    </section>
  )
}
