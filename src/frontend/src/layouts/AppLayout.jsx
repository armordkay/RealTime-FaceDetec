import { navigate } from '../routes/router'

export default function AppLayout({ currentPath, user, navItems, onLogout, children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h2>Face Attendance</h2>
          <p>FastAPI + React</p>
        </div>

        <nav className="nav-list">
          {navItems.map((route) => (
            <button
              key={route.path}
              className={`nav-item ${currentPath.startsWith(route.path) ? 'active' : ''}`}
              onClick={() => navigate(route.path)}
              type="button"
            >
              {route.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p>{user?.username || 'Unknown'}</p>
          <small>{user?.role || 'guest'}</small>
          <a className="btn secondary" href="#/kiosk">
            Open Kiosk
          </a>
          <button type="button" className="btn secondary" onClick={onLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="content">{children}</main>
    </div>
  )
}
