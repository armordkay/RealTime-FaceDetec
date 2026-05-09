import { useState } from 'react'

import { attendanceApi } from '../api/attendanceApi'
import StatusBadge from '../components/common/StatusBadge'
import { formatDateTime } from '../utils/time'

export default function AttendanceLogsPage() {
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState('')
  const [actionType, setActionType] = useState('')
  const [editingLogId, setEditingLogId] = useState(null)
  const [editStatus, setEditStatus] = useState('recorded')
  const [editAction, setEditAction] = useState('check_in')
  const [editReason, setEditReason] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function fetchLogs() {
    setError('')
    setMessage('')
    try {
      const response = await attendanceApi.listLogs({ status, action_type: actionType })
      setLogs(response.data)
    } catch (err) {
      setError(err.message || 'Cannot load attendance logs')
    }
  }

  function openEdit(item) {
    setEditingLogId(item.id)
    setEditStatus(item.status || 'recorded')
    setEditAction(item.action_type || 'check_in')
    setEditReason(item.reason || '')
    setMessage('')
    setError('')
  }

  async function saveEdit() {
    if (!editingLogId) return
    setError('')
    setMessage('')
    try {
      const response = await attendanceApi.updateLog(editingLogId, {
        status: editStatus,
        action_type: editAction,
        reason: editReason,
      })
      if (response.data.updated) {
        setMessage('Log updated')
        setEditingLogId(null)
        await fetchLogs()
      } else {
        setError(response.data.message || 'Cannot update log')
      }
    } catch (err) {
      setError(err.message || 'Cannot update attendance log')
    }
  }

  return (
    <section className="page">
      <h1>Attendance Logs</h1>
      <p>Manager mode: full logs with edit permission.</p>

      <div className="inline-form">
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All Status</option>
          <option value="recorded">recorded</option>
          <option value="duplicate_blocked">duplicate_blocked</option>
          <option value="review_required">review_required</option>
          <option value="rejected">rejected</option>
        </select>

        <select value={actionType} onChange={(event) => setActionType(event.target.value)}>
          <option value="">All Action</option>
          <option value="check_in">check_in</option>
          <option value="check_out">check_out</option>
          <option value="ignored">ignored</option>
        </select>

        <button className="btn" type="button" onClick={fetchLogs}>
          Load Logs
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}
      {message && <p>{message}</p>}

      {editingLogId && (
        <div className="card">
          <h3>Edit Log #{editingLogId}</h3>
          <div className="inline-form">
            <select value={editAction} onChange={(event) => setEditAction(event.target.value)}>
              <option value="check_in">check_in</option>
              <option value="check_out">check_out</option>
              <option value="ignored">ignored</option>
              <option value="manual_adjustment">manual_adjustment</option>
            </select>

            <select value={editStatus} onChange={(event) => setEditStatus(event.target.value)}>
              <option value="recorded">recorded</option>
              <option value="duplicate_blocked">duplicate_blocked</option>
              <option value="review_required">review_required</option>
              <option value="rejected">rejected</option>
            </select>

            <input
              placeholder="Reason"
              value={editReason}
              onChange={(event) => setEditReason(event.target.value)}
            />

            <button className="btn" type="button" onClick={saveEdit}>
              Save
            </button>
            <button className="btn secondary" type="button" onClick={() => setEditingLogId(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Employee</th>
              <th>Device</th>
              <th>Action</th>
              <th>Status</th>
              <th>Score</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((item) => (
              <tr key={item.id}>
                <td>{formatDateTime(item.event_time)}</td>
                <td>{item.employee_name}</td>
                <td>{item.device_id}</td>
                <td>
                  <StatusBadge value={item.action_type} />
                </td>
                <td>
                  <StatusBadge value={item.status} />
                </td>
                <td>{item.score}</td>
                <td>
                  <button className="btn-link" onClick={() => openEdit(item)}>
                    Edit
                  </button>
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan="7">No logs loaded.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
