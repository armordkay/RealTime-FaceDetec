import { useEffect, useRef, useState } from 'react'

import { API_BASE_URL } from '../api/client'
import { attendanceApi } from '../api/attendanceApi'
import StatusBadge from '../components/common/StatusBadge'
import { formatDateTime } from '../utils/time'

const DEVICE_ID = 'kiosk_front_gate_1'
const STREAM_INTERVAL_MS = 200

function getKioskWebSocketUrl() {
  const explicitUrl = import.meta.env.VITE_KIOSK_WS_URL
  if (explicitUrl) return explicitUrl

  const apiUrl = new URL(API_BASE_URL)
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, '')}/attendance/kiosk-ws`
  apiUrl.search = ''
  return apiUrl.toString()
}

export default function KioskCheckinPage() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const runningRef = useRef(false)
  const socketRef = useRef(null)
  const streamIntervalRef = useRef(null)

  const [cameraOn, setCameraOn] = useState(false)
  const [error, setError] = useState('')
  const [lastResult, setLastResult] = useState(null)
  const [logs, setLogs] = useState([])
  const [requesting, setRequesting] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')

  async function startCamera() {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      runningRef.current = true
      setCameraOn(true)
      connectWebSocket()
    } catch (err) {
      setError(err.message || 'Cannot access camera')
    }
  }

  function stopCamera() {
    runningRef.current = false
    stopStreaming()
    const stream = videoRef.current?.srcObject
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraOn(false)
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
      try {
        const payload = JSON.parse(event.data)
        if (payload.success === false) {
          setError(payload.error?.message || 'Recognition failed')
          return
        }

        setLastResult(payload.data)
      } catch {
        setError('Invalid recognition response')
      }
    }

    socket.onerror = () => {
      setError('Kiosk WebSocket connection failed')
      setConnectionStatus('error')
    }

    socket.onclose = () => {
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

    if (closeSocket && socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }
    setRequesting(false)
  }

  function captureFrameBase64() {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return null
    if (!video.videoWidth || !video.videoHeight) return null

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.72)
  }

  function sendCheckinFrame() {
    if (!runningRef.current) return
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return

    const frame = captureFrameBase64()
    if (!frame) return

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
          <video ref={videoRef} className="kiosk-video" muted playsInline />
          <canvas ref={canvasRef} className="hidden" />
          <p>{requesting ? `Streaming (${connectionStatus})` : connectionStatus}</p>
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
            </div>
          ) : (
            <p>No result yet.</p>
          )}
        </div>
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
