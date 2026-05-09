import { apiRequest } from './client'

function toQuery(params) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      query.set(key, String(value))
    }
  })
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ''
}

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
      body: {
        device_id: deviceId,
        cropped_image_base64: croppedImageBase64,
      },
      auth: false,
    }),
  kioskLogs: (limit = 20) =>
    apiRequest(`/attendance/kiosk-logs?limit=${limit}`, {
      auth: false,
    }),
}
