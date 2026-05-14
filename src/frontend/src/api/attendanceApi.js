import { apiRequest, toQuery } from './client'

const KIOSK_API_KEY = import.meta.env.VITE_KIOSK_API_KEY || ''

export const attendanceApi = {
  recognize: (deviceId, croppedImageBase64) =>
    apiRequest('/attendance/recognize', {
      method: 'POST',
      body: {
        device_id: deviceId,
        cropped_image_base64: croppedImageBase64,
      },
    }),

  listLogs: (params = {}) => apiRequest(`/attendance/logs${toQuery(params)}`),

  myLogs: () => apiRequest('/attendance/my-logs'),
  myStatus: () => apiRequest('/attendance/my-status'),
  updateLog: (logId, payload) =>
    apiRequest(`/attendance/logs/${logId}`, { method: 'PATCH', body: payload }),
  kioskCheckin: (deviceId, croppedImageBase64) =>
    apiRequest('/attendance/kiosk-checkin', {
      method: 'POST',
      headers: KIOSK_API_KEY ? { 'X-Kiosk-Key': KIOSK_API_KEY } : {},
      body: {
        device_id: deviceId,
        cropped_image_base64: croppedImageBase64,
      },
      auth: false,
    }),
  confirmKioskAttendance: (payload) =>
    apiRequest('/attendance/kiosk-confirm', {
      method: 'POST',
      headers: KIOSK_API_KEY ? { 'X-Kiosk-Key': KIOSK_API_KEY } : {},
      body: payload,
      auth: false,
    }),
  kioskLogs: (limit = 20) =>
    apiRequest(`/attendance/kiosk-logs?limit=${limit}`, {
      headers: KIOSK_API_KEY ? { 'X-Kiosk-Key': KIOSK_API_KEY } : {},
      auth: false,
    }),
}
