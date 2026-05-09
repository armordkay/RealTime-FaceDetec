import { apiRequest } from './client'

export const authApi = {
  login: (username, password, requestedRole) =>
    apiRequest('/auth/login', {
      method: 'POST',
      body: { username, password, requested_role: requestedRole },
      auth: false,
    }),

  me: () => apiRequest('/auth/me'),

  changePassword: (oldPassword, newPassword) =>
    apiRequest('/auth/change-password', {
      method: 'POST',
      body: {
        old_password: oldPassword,
        new_password: newPassword,
      },
    }),
}
