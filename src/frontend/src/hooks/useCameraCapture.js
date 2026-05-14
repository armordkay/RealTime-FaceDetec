import { useCallback, useRef, useState } from 'react'

export function useCameraCapture({ maxWidth = null, quality = 0.8, onError } = {}) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [cameraOn, setCameraOn] = useState(false)

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setCameraOn(true)
      return true
    } catch (err) {
      onError?.(err.message || 'Cannot access camera')
      return false
    }
  }, [onError])

  const stopCamera = useCallback(() => {
    const stream = videoRef.current?.srcObject
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraOn(false)
  }, [])

  const captureFrameBase64 = useCallback(() => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) return null

    const scale = maxWidth ? Math.min(1, maxWidth / video.videoWidth) : 1
    canvas.width = Math.round(video.videoWidth * scale)
    canvas.height = Math.round(video.videoHeight * scale)
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', quality)
  }, [maxWidth, quality])

  return {
    videoRef,
    canvasRef,
    cameraOn,
    startCamera,
    stopCamera,
    captureFrameBase64,
  }
}
