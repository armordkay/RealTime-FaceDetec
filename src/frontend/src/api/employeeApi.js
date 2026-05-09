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

export const employeeApi = {
  list: (params = {}) => apiRequest(`/employees${toQuery(params)}`),
  getById: (employeeId) => apiRequest(`/employees/${employeeId}`),
  create: (payload) => apiRequest('/employees', { method: 'POST', body: payload }),
  update: (employeeId, payload) =>
    apiRequest(`/employees/${employeeId}`, { method: 'PATCH', body: payload }),
  deactivate: (employeeId) =>
    apiRequest(`/employees/${employeeId}`, { method: 'DELETE' }),
  me: () => apiRequest('/employees/me'),
  updateMe: (payload) => apiRequest('/employees/me', { method: 'PATCH', body: payload }),
}
