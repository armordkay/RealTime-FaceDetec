import { useMemo } from 'react'

import { authApi } from './api/authApi'
import AppLayout from './layouts/AppLayout'
import { useHashPath } from './hooks/useHashPath'
import { clearAuthSession, setAuthSession, useAuthStore } from './store/authStore'
import {
  getDefaultPathByRole,
  getNavRoutesByRole,
  isRouteAllowed,
  navigate,
  resolveRoute,
} from './routes/router'

import LoginPage from './pages/LoginPage'
import EmployeesPage from './pages/EmployeesPage'
import EmployeeDetailPage from './pages/EmployeeDetailPage'
import AttendanceLogsPage from './pages/AttendanceLogsPage'
import ReportsPage from './pages/ReportsPage'
import KioskCheckinPage from './pages/KioskCheckinPage'
import AdminPage from './pages/AdminPage'

function NotFoundPage() {
  return (
    <section className="page">
      <h1>Page Not Found</h1>
      <button className="btn" onClick={() => navigate('/kiosk')} type="button">
        Go to Kiosk
      </button>
    </section>
  )
}

export default function App() {
  const path = useHashPath()
  const route = useMemo(() => resolveRoute(path), [path])
  const auth = useAuthStore()
  const role = auth.user?.role || null
  const navItems = useMemo(() => (role ? getNavRoutesByRole(role) : []), [role])

  async function handleLogin(username, password, requestedRole) {
    const response = await authApi.login(username, password, requestedRole)
    setAuthSession(response.data.access_token, response.data.user)
    navigate(getDefaultPathByRole(response.data.user.role))
  }

  function handleLogout() {
    clearAuthSession()
    navigate('/login')
  }

  // Public kiosk screen for continuous employee check-in, no login required.
  if (route.key === 'kiosk') {
    return <KioskCheckinPage />
  }

  if (!auth.token && route.key !== 'login') {
    navigate('/login')
    return null
  }

  if (auth.token && role && !isRouteAllowed(route.path, role)) {
    navigate(getDefaultPathByRole(role))
    return null
  }

  if (route.key === 'login') {
    return (
      <LoginPage
        onSubmit={handleLogin}
        currentUser={auth.user}
        onForceLogout={handleLogout}
      />
    )
  }

  let content = <NotFoundPage />

  if (route.key === 'admin') content = <AdminPage />
  if (route.key === 'employees') content = <EmployeesPage />
  if (route.key === 'employee-detail') content = <EmployeeDetailPage employeeId={route.params.id} />
  if (route.key === 'attendance-logs') content = <AttendanceLogsPage />
  if (route.key === 'reports') content = <ReportsPage />

  return (
    <AppLayout currentPath={route.path} user={auth.user} navItems={navItems} onLogout={handleLogout}>
      {content}
    </AppLayout>
  )
}
