import { apiRequest, toQuery } from './client'

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
