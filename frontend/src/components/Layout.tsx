import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import type { Role } from '../types';

interface NavItem {
  to: string;
  label: string;
  testId: string;
  roles?: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', testId: 'nav-dashboard' },
  { to: '/courses', label: 'Courses', testId: 'nav-courses' },
  { to: '/sessions', label: 'Sessions', testId: 'nav-sessions' },
  { to: '/enrollments', label: 'Enrollments', testId: 'nav-enrollments' },
  { to: '/users', label: 'Users', testId: 'nav-users', roles: ['admin'] },
  { to: '/tags', label: 'Tags', testId: 'nav-tags', roles: ['admin'] },
  { to: '/audit', label: 'Audit log', testId: 'nav-audit', roles: ['admin'] },
];

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role)));

  return (
    <div className="app-shell">
      {sidebarOpen ? (
        <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-hidden="true" />
      ) : null}

      <aside className={`sidebar${sidebarOpen ? ' sidebar--open' : ''}`} aria-label="Main navigation">
        <div className="sidebar__brand">
          <span className="sidebar__logo" aria-hidden="true">E</span>
          <span className="sidebar__brand-name">EduFlow</span>
          <button
            type="button"
            className="sidebar__close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
            data-testid="sidebar-close"
          >
            &times;
          </button>
        </div>
        <nav className="sidebar__nav">
          <ul>
            {visibleItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
                  onClick={() => setSidebarOpen(false)}
                  data-testid={item.testId}
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button
            type="button"
            className="topbar__menu"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label="Toggle navigation"
            aria-expanded={sidebarOpen}
            data-testid="menu-toggle"
          >
            <span aria-hidden="true">&#9776;</span>
          </button>
          <div className="topbar__spacer" />
          <div className="topbar__user">
            <span className="topbar__name">{user?.full_name ?? user?.email}</span>
            {user ? (
              <span className="topbar__role" data-testid="user-role">{user.role}</span>
            ) : null}
          </div>
          <button
            type="button"
            className="button button--secondary button--small"
            onClick={handleLogout}
            data-testid="logout-button"
          >
            Log out
          </button>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
