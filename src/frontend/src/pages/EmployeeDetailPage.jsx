import { useEffect, useState } from 'react'

import { API_BASE_URL } from '../api/client'
import { employeeApi } from '../api/employeeApi'
import { faceEnrollmentApi } from '../api/faceEnrollmentApi'
import { useCameraCapture } from '../hooks/useCameraCapture'
import { navigate } from '../routes/router'
import { formatDateTime } from '../utils/time'

function resolveMediaUrl(url) {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url

  const apiUrl = new URL(API_BASE_URL)
  return `${apiUrl.origin}${url}`
}

export default function EmployeeDetailPage({ employeeId }) {
  const [employee, setEmployee] = useState(null)
  const [samples, setSamples] = useState([])
  const [capturedFrames, setCapturedFrames] = useState([])
  const [saving, setSaving] = useState(false)
  const [enrolling, setEnrolling] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    position: '',
    department: '',
    status: '',
  })
  const {
    videoRef,
    canvasRef,
    cameraOn,
    startCamera,
    stopCamera,
    captureFrameBase64,
  } = useCameraCapture({ onError: setError })

  async function loadDetail() {
    if (!employeeId) return
    setError('')
    try {
      const [employeeResponse, sampleResponse] = await Promise.all([
        employeeApi.getById(employeeId),
        faceEnrollmentApi.listSamples(employeeId),
      ])
      setEmployee(employeeResponse.data)
      setSamples(sampleResponse.data)
      setForm({
        full_name: employeeResponse.data.full_name || '',
        email: employeeResponse.data.email || '',
        phone: employeeResponse.data.phone || '',
        position: employeeResponse.data.position || '',
        department: employeeResponse.data.department || '',
        status: employeeResponse.data.status || 'active',
      })
    } catch (err) {
      setError(err.message || 'Cannot load employee detail')
    }
  }

  useEffect(() => {
    loadDetail()
    return () => {
      stopCamera()
    }
    // This effect owns the employee-detail lifecycle; camera cleanup must only run on page exit/id change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId])

  function handleChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSave(event) {
    event.preventDefault()
    if (!employee) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const response = await employeeApi.update(employee.id, form)
      setEmployee(response.data)
      setMessage('Employee updated')
    } catch (err) {
      setError(err.message || 'Cannot update employee')
    } finally {
      setSaving(false)
    }
  }

  function captureFaceSample() {
    const frame = captureFrameBase64()
    if (!frame) {
      setError('Camera is not ready')
      return
    }

    setCapturedFrames((prev) => [...prev, frame])
    setMessage(`Captured ${capturedFrames.length + 1} sample(s)`)
  }

  function removeCaptured(index) {
    setCapturedFrames((prev) => prev.filter((_, idx) => idx !== index))
  }

  async function handleFileSamples(event) {
    const files = Array.from(event.target.files || [])
    if (files.length === 0) return

    setError('')
    setMessage('')

    try {
      const frames = await Promise.all(
        files.map((file) => (
          new Promise((resolve, reject) => {
            const reader = new FileReader()
            reader.onload = () => resolve(reader.result)
            reader.onerror = () => reject(new Error(`Cannot read ${file.name}`))
            reader.readAsDataURL(file)
          })
        )),
      )
      setCapturedFrames((prev) => [...prev, ...frames])
      setMessage(`Added ${frames.length} image sample(s)`)
    } catch (err) {
      setError(err.message || 'Cannot add image samples')
    } finally {
      event.target.value = ''
    }
  }

  async function submitEnrollment() {
    if (!employee) return
    if (capturedFrames.length === 0) {
      setError('Capture at least one face sample before submit')
      return
    }

    setEnrolling(true)
    setError('')
    setMessage('Processing face samples. The first enrollment can take a few minutes while the recognition model loads.')
    try {
      const response = await faceEnrollmentApi.enroll({
        employee_id: employee.id,
        samples: capturedFrames.map((frame) => ({ image_base64: frame })),
      })
      const failureText = response.data.failure_reasons?.length
        ? ` Failed: ${response.data.failure_reasons.join('; ')}`
        : ''

      if (response.data.saved_samples === 0) {
        setError(`${response.data.message}.${failureText}`)
        return
      }

      setMessage(`Enrollment done. Saved ${response.data.saved_samples} sample(s).${failureText}`)
      setCapturedFrames([])
      await loadDetail()
    } catch (err) {
      setError(err.message || 'Enrollment failed')
    } finally {
      setEnrolling(false)
    }
  }

  async function handleDeactivate() {
    if (!employee) return
    setError('')
    setMessage('')
    try {
      const response = await employeeApi.deactivate(employee.id)
      setEmployee(response.data)
      setForm((prev) => ({ ...prev, status: response.data.status }))
      setMessage('Employee deactivated')
    } catch (err) {
      setError(err.message || 'Cannot deactivate employee')
    }
  }

  return (
    <section className="page">
      <button type="button" className="btn secondary" onClick={() => navigate('/employees')}>
        Back
      </button>
      <h1>Employee Detail</h1>

      {error && <p className="error-text">{error}</p>}
      {message && <p>{message}</p>}
      {!employee && !error && <p>Loading...</p>}

      {employee && (
        <>
          <div className="card detail-grid">
            <div>
              <strong>Code:</strong> {employee.employee_code}
            </div>
            <div>
              <strong>Name:</strong> {employee.full_name}
            </div>
            <div>
              <strong>Email:</strong> {employee.email}
            </div>
            <div>
              <strong>Department:</strong> {employee.department}
            </div>
            <div>
              <strong>Position:</strong> {employee.position || '-'}
            </div>
            <div>
              <strong>Status:</strong> {employee.status}
            </div>
          </div>

          <form className="card" onSubmit={handleSave}>
            <h3>Edit Employee</h3>

            <label>
              Full Name
              <input value={form.full_name} onChange={(event) => handleChange('full_name', event.target.value)} />
            </label>

            <label>
              Email
              <input value={form.email} onChange={(event) => handleChange('email', event.target.value)} />
            </label>

            <label>
              Phone
              <input value={form.phone} onChange={(event) => handleChange('phone', event.target.value)} />
            </label>

            <label>
              Position
              <input value={form.position} onChange={(event) => handleChange('position', event.target.value)} />
            </label>

            <label>
              Department
              <input value={form.department} onChange={(event) => handleChange('department', event.target.value)} />
            </label>

            <label>
              Status
              <select value={form.status} onChange={(event) => handleChange('status', event.target.value)}>
                <option value="active">active</option>
                <option value="inactive">inactive</option>
              </select>
            </label>

            <div className="inline-form">
              <button type="submit" className="btn" disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              {employee.status !== 'inactive' && (
                <button type="button" className="btn secondary" onClick={handleDeactivate}>
                  Deactivate Employee
                </button>
              )}
            </div>
          </form>

          <div className="card">
            <h3>Face Enrollment (Camera)</h3>
            <p>Capture 3-5 clear frames, then submit enrollment for this employee.</p>

            <div className="inline-form">
              {!cameraOn ? (
                <button className="btn" type="button" onClick={startCamera}>
                  Start Camera
                </button>
              ) : (
                <button className="btn secondary" type="button" onClick={stopCamera}>
                  Stop Camera
                </button>
              )}

              <button className="btn" type="button" onClick={captureFaceSample} disabled={!cameraOn}>
                Capture Sample
              </button>

              <label className="btn secondary">
                Add Images
                <input className="hidden" type="file" accept="image/*" multiple onChange={handleFileSamples} />
              </label>

              <button className="btn" type="button" onClick={submitEnrollment} disabled={enrolling || capturedFrames.length === 0}>
                {enrolling ? 'Processing...' : 'Submit Enrollment'}
              </button>
            </div>

            <video ref={videoRef} className="video-preview" muted playsInline />
            <canvas ref={canvasRef} className="hidden" />

            <h4>Captured Queue ({capturedFrames.length})</h4>
            <ul className="simple-list">
              {capturedFrames.map((sample, index) => (
                <li key={`${sample.slice(0, 30)}-${index}`}>
                  Sample #{index + 1}
                  <button className="btn-link" onClick={() => removeCaptured(index)}>
                    remove
                  </button>
                </li>
              ))}
              {capturedFrames.length === 0 && <li>No captured sample yet.</li>}
            </ul>
          </div>

          <div className="card">
            <h3>Saved Face Samples</h3>
            <p>Total: {samples.length}</p>
            <ul className="simple-list face-sample-list">
              {samples.map((sample) => (
                <li key={sample.id}>
                  <img src={resolveMediaUrl(sample.cropped_face_url)} alt={`Face sample ${sample.id}`} />
                  <span>
                    #{sample.id} | quality {sample.quality_score.toFixed(2)} | {formatDateTime(sample.created_at)}
                  </span>
                </li>
              ))}
              {samples.length === 0 && <li>No saved samples.</li>}
            </ul>
          </div>
        </>
      )}
    </section>
  )
}
