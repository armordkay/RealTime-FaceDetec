import { useEffect, useRef, useState } from 'react'

import { API_BASE_URL } from '../api/client'
import { attendanceApi } from '../api/attendanceApi'
import StatusBadge from '../components/common/StatusBadge'
import { useCameraCapture } from '../hooks/useCameraCapture'
import { formatDateTime } from '../utils/time'

const DEVICE_ID = 'kiosk_front_gate_1'
const STREAM_INTERVAL_MS = 900
const FRAME_MAX_WIDTH = 640
const KIOSK_API_KEY = import.meta.env.VITE_KIOSK_API_KEY || ''

function getKioskWebSocketUrl() {
  const explicitUrl = import.meta.env.VITE_KIOSK_WS_URL
  if (explicitUrl) return explicitUrl

  const apiUrl = new URL(API_BASE_URL)
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, '')}/attendance/kiosk-ws`
  apiUrl.search = ''
  if (KIOSK_API_KEY) {
    apiUrl.searchParams.set('kiosk_key', KIOSK_API_KEY)
  }
  return apiUrl.toString()
}

export default function KioskCheckinPage() {
  const runningRef = useRef(false)
  const socketRef = useRef(null)
  const streamIntervalRef = useRef(null)
  const frameInFlightRef = useRef(false)
  const lastSentFrameRef = useRef('')
  const currentPersonFrameRef = useRef('')
  const lastResultFrameRef = useRef('')
  const lastResultRef = useRef(null)
  const overlayRef = useRef(null)

  const [error, setError] = useState('')
  const [currentPerson, setCurrentPerson] = useState(null)
  const [lastResult, setLastResult] = useState(null)
  const [lastResultHasFrame, setLastResultHasFrame] = useState(false)
  const [logs, setLogs] = useState([])
  const [requesting, setRequesting] = useState(false)
  const [recordingAttendance, setRecordingAttendance] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const {
    videoRef,
    canvasRef,
    cameraOn,
    startCamera: startCameraCapture,
    stopCamera: stopCameraCapture,
    captureFrameBase64,
  } = useCameraCapture({
    maxWidth: FRAME_MAX_WIDTH,
    quality: 0.92,
    onError: setError,
  })

  function updateLastResult(nextResult, frame) {
    lastResultRef.current = nextResult
    lastResultFrameRef.current = frame || ''
    setLastResultHasFrame(Boolean(frame))
    setLastResult(nextResult)
  }

  function clearOverlay() {
    const overlay = overlayRef.current
    if (!overlay) return
    const ctx = overlay.getContext('2d')
    ctx.clearRect(0, 0, overlay.width, overlay.height)
  }

  // Vẽ khung quanh khuôn mặt phát hiện được trong camera.
  // Xanh = nhận diện hợp lệ; Đỏ = có mặt nhưng không khớp / không hợp lệ.
  function drawFaceBox(result) {
    const overlay = overlayRef.current
    const video = videoRef.current
    if (!overlay || !video) return

    const dw = video.clientWidth
    const dh = video.clientHeight
    if (!dw || !dh) return
    if (overlay.width !== dw) overlay.width = dw
    if (overlay.height !== dh) overlay.height = dh

    const ctx = overlay.getContext('2d')
    ctx.clearRect(0, 0, dw, dh)

    const fa = result?.facial_area
    const iw = result?.image_width
    const ih = result?.image_height
    if (!fa || !iw || !ih || (fa.w <= 0 && fa.h <= 0)) return

    // Map toạ độ mặt từ ảnh phân tích sang khung hiển thị (object-fit: cover).
    const scale = Math.max(dw / iw, dh / ih)
    const offsetX = (iw * scale - dw) / 2
    const offsetY = (ih * scale - dh) / 2
    const x = fa.x * scale - offsetX
    const y = fa.y * scale - offsetY
    const w = fa.w * scale
    const h = fa.h * scale

    const ok =
      result.match_found &&
      result.attendance_status !== 'rejected' &&
      result.is_live !== false
    const color = ok ? '#16a34a' : '#dc2626'

    ctx.lineWidth = 3
    ctx.strokeStyle = color
    ctx.strokeRect(x, y, w, h)

    const label = ok
      ? result.employee_name || 'Nhan dien OK'
      : result.is_live === false
        ? 'Mat gia'
        : 'Khong khop'
    ctx.font = '16px sans-serif'
    const tw = ctx.measureText(label).width + 12
    const ty = y - 24 >= 0 ? y - 24 : y + h
    ctx.fillStyle = color
    ctx.fillRect(x, ty, tw, 22)
    ctx.fillStyle = '#ffffff'
    ctx.fillText(label, x + 6, ty + 16)
  }

  async function startCamera() {
    setError('')
    const started = await startCameraCapture()
    if (started) {
      runningRef.current = true
      connectWebSocket()
    }
  }

  function stopCamera() {
    runningRef.current = false
    stopStreaming()
    stopCameraCapture()
    clearOverlay()
  }

  function connectWebSocket() {
    if (socketRef.current && socketRef.current.readyState <= WebSocket.OPEN) return

    setConnectionStatus('connecting')
    const socket = new WebSocket(getKioskWebSocketUrl())
    socketRef.current = socket

    socket.onopen = () => {
      setConnectionStatus('connected')
      setRequesting(true)
      startStreaming()
    }

    socket.onmessage = (event) => {
      frameInFlightRef.current = false
      try {
        const payload = JSON.parse(event.data)
        if (payload.success === false) {
          setError(payload.error?.message || 'Recognition failed')
          clearOverlay()
          return
        }

        setCurrentPerson(payload.data)
        drawFaceBox(payload.data)
        currentPersonFrameRef.current = lastSentFrameRef.current
        if (
          payload.data.match_found
          && payload.data.attendance_status !== 'rejected'
          && !lastResultRef.current
        ) {
          updateLastResult(payload.data, currentPersonFrameRef.current)
        }
      } catch {
        setError('Invalid recognition response')
      }
    }

    socket.onerror = () => {
      frameInFlightRef.current = false
      setError('Kiosk WebSocket connection failed')
      setConnectionStatus('error')
    }

    socket.onclose = () => {
      frameInFlightRef.current = false
      setRequesting(false)
      setConnectionStatus('disconnected')
      stopStreaming(false)
    }
  }

  function startStreaming() {
    if (streamIntervalRef.current) return

    streamIntervalRef.current = setInterval(() => {
      sendCheckinFrame()
    }, STREAM_INTERVAL_MS)
  }

  function stopStreaming(closeSocket = true) {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current)
      streamIntervalRef.current = null
    }
    frameInFlightRef.current = false

    if (closeSocket && socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }
    setRequesting(false)
  }

  function sendCheckinFrame() {
    if (!runningRef.current) return
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return
    if (frameInFlightRef.current) return

    const frame = captureFrameBase64()
    if (!frame) return

    frameInFlightRef.current = true
    lastSentFrameRef.current = frame
    socketRef.current.send(JSON.stringify({
      device_id: DEVICE_ID,
      cropped_image_base64: frame,
    }))
  }

  async function loadLogs(limit = 12) {
    try {
      const response = await attendanceApi.kioskLogs(limit)
      setLogs(response.data)
    } catch {
      // keep kiosk running even if log polling fails
    }
  }

  function reloadLastResult() {
    if (!currentPerson?.match_found || currentPerson.attendance_status === 'rejected') {
      updateLastResult(null, '')
      return
    }
    updateLastResult(currentPerson, currentPersonFrameRef.current)
  }

  async function recordAttendance() {
    if (!lastResult?.employee_id || !lastResultFrameRef.current) return

    setRecordingAttendance(true)
    setError('')
    try {
      const response = await attendanceApi.confirmKioskAttendance({
        employee_id: lastResult.employee_id,
        device_id: DEVICE_ID,
        cropped_image_base64: lastResultFrameRef.current,
        score: lastResult.score,
        threshold: lastResult.threshold,
        is_live: lastResult.is_live,
      })
      updateLastResult(response.data, lastResultFrameRef.current)
      await loadLogs(12)
    } catch (err) {
      setError(err.message || 'Cannot record attendance')
    } finally {
      setRecordingAttendance(false)
    }
  }

  useEffect(() => {
    startCamera()
    loadLogs(12)

    const logsInterval = setInterval(() => {
      loadLogs(12)
    }, 3500)

    return () => {
      clearInterval(logsInterval)
      stopCamera()
    }
    // Kiosk bootstraps camera and polling once for the page lifecycle.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <section className="kiosk-page">
      <header className="kiosk-header">
        <div>
          <h1>Employee Face Check-In Kiosk</h1>
          <p>Stand in front of camera. System auto check-ins continuously.</p>
        </div>
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
          <a className="btn secondary" href="#/login">
            Manager Portal
          </a>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}

      <div className="kiosk-grid">
        <div className="card kiosk-video-card">
          <div className="kiosk-video-frame">
            <video ref={videoRef} className="kiosk-video" muted playsInline />
            <canvas ref={overlayRef} className="kiosk-face-overlay" />
          </div>
          <canvas ref={canvasRef} className="hidden" />
          <p>{requesting ? `Streaming (${connectionStatus})` : connectionStatus}</p>
        </div>

        <div className="card">
          <h3>Current Person</h3>
          <div className="detail-grid">
            <div>
              <strong>Employee:</strong> {currentPerson?.employee_name || 'Unknown'}
            </div>
            <div>
              <strong>Match:</strong> {currentPerson?.match_found ? 'Yes' : 'No'}
            </div>
            <div>
              <strong>Score:</strong> {currentPerson?.score ?? 0}
            </div>
            <div>
              <strong>Message:</strong> {currentPerson?.message || 'No face recognized'}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Last Result</h3>
        {lastResult ? (
          <div className="detail-grid">
            <div>
              <strong>Employee:</strong> {lastResult.employee_name || 'Unknown'}
            </div>
            <div>
              <strong>Match:</strong> {lastResult.match_found ? 'Yes' : 'No'}
            </div>
            <div>
              <strong>Action:</strong> <StatusBadge value={lastResult.action_suggested} />
            </div>
            <div>
              <strong>Status:</strong> <StatusBadge value={lastResult.attendance_status} />
            </div>
            <div>
              <strong>Score:</strong> {lastResult.score}
            </div>
            <div>
              <strong>Message:</strong> {lastResult.message}
            </div>
            <div className="inline-form">
              <button
                className="btn"
                type="button"
                onClick={recordAttendance}
                disabled={recordingAttendance || !lastResult?.employee_id || !lastResultHasFrame}
              >
                {recordingAttendance ? 'Recording...' : 'Submit'}
              </button>
              <button
                className="btn secondary"
                type="button"
                onClick={reloadLastResult}
              >
                Reload
              </button>
            </div>
          </div>
        ) : (
          <div className="detail-grid">
            <div>
              <strong>Employee:</strong> Unknown
            </div>
            <div>
              <strong>Match:</strong> No
            </div>
            <div>
              <strong>Score:</strong> 0
            </div>
            <div>
              <strong>Message:</strong> No result yet
            </div>
            <div className="inline-form">
              <button
                className="btn"
                type="button"
                onClick={recordAttendance}
                disabled
              >
                Ghi nhận
              </button>
              <button
                className="btn secondary"
                type="button"
                onClick={reloadLastResult}
              >
                Reload
              </button>
            </div>
          </div>
        )}
        </div>

      <div className="card">
        <h3>Recent Check-In Logs</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Employee</th>
              <th>Action</th>
              <th>Status</th>
              <th>Device</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((item) => (
              <tr key={item.id}>
                <td>{formatDateTime(item.event_time)}</td>
                <td>{item.employee_name}</td>
                <td><StatusBadge value={item.action_type} /></td>
                <td><StatusBadge value={item.status} /></td>
                <td>{item.device_id}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan="5">No check-in logs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
