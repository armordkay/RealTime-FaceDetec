import { apiRequest } from './client'

export const adminApi = {
  overview: () => apiRequest('/admin/overview'),
  accessLogs: (limit = 50) => apiRequest(`/admin/access-logs?limit=${limit}`),
  users: () => apiRequest('/admin/users'),
  createUser: (payload) => apiRequest('/admin/users', { method: 'POST', body: payload }),
  updateUser: (userId, payload) =>
    apiRequest(`/admin/users/${userId}`, { method: 'PATCH', body: payload }),
  config: () => apiRequest('/admin/config'),
  updateConfig: (payload) => apiRequest('/admin/config', { method: 'PATCH', body: payload }),
}
