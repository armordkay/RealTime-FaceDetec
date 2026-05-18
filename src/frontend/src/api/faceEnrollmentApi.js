import { apiRequest } from './client'

export const faceEnrollmentApi = {
  enroll: (payload) =>
    apiRequest('/face-enrollments', {
      method: 'POST',
      body: payload,
    }),

  listSamples: (employeeId) =>
    apiRequest(`/face-enrollments/employees/${employeeId}/face-samples`),
}
