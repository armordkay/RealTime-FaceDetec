export const roles = ['admin', 'manager', 'viewer']

export const navRoutes = [
  {
    path: '/admin',
    label: 'IT Administration',
    roles: ['admin'],
  },
  {
    path: '/employees',
    label: 'Employees & Enrollment',
    roles: ['admin', 'manager'],
  },
  {
    path: '/attendance-logs',
    label: 'Attendance Logs',
    roles: ['admin', 'manager'],
  },
  {
    path: '/reports',
    label: 'Reports',
    roles: ['admin', 'manager', 'viewer'],
  },
]

export function getHashPath() {
  const hash = window.location.hash.replace('#', '')
  return hash || '/kiosk'
}

export function resolveRoute(path) {
  if (!path || path === '/') {
    return { key: 'login', path: '/login', params: {} }
  }

  if (path.startsWith('/employees/')) {
    const id = Number(path.replace('/employees/', ''))
    return {
      key: 'employee-detail',
      path,
      params: { id: Number.isNaN(id) ? null : id },
    }
  }

  const map = {
    '/kiosk': 'kiosk',
    '/login': 'login',
    '/admin': 'admin',
    '/employees': 'employees',
    '/attendance-logs': 'attendance-logs',
    '/reports': 'reports',
  }

  return {
    key: map[path] || 'not-found',
    path,
    params: {},
  }
}

export function navigate(path) {
  window.location.hash = path
}

export function getNavRoutesByRole(role) {
  return navRoutes.filter((route) => route.roles.includes(role))
}

export function getDefaultPathByRole(role) {
  if (role === 'admin') return '/admin'
  if (role === 'manager') return '/employees'
  if (role === 'viewer') return '/reports'
  return '/login'
}

export function isRouteAllowed(path, role) {
  if (path === '/login' || path === '/kiosk') return true
  if (path.startsWith('/employees/')) {
    return ['admin', 'manager'].includes(role)
  }
  const route = navRoutes.find((item) => item.path === path)
  if (!route) return false
  return route.roles.includes(role)
}
