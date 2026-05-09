import { apiRequest } from './client'

export const reportApi = {
  daily: (date) => apiRequest(`/reports/attendance-daily${date ? `?date=${date}` : ''}`),
  monthly: (month) => apiRequest(`/reports/attendance-monthly${month ? `?month=${month}` : ''}`),
  lateEmployees: () => apiRequest('/reports/late-employees'),
  exportCsv: () => apiRequest('/reports/export?format=csv'),
}
