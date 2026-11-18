import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { Layout } from './components/Layout';
import { AccessDenied } from './pages/AccessDenied';
import { Audit } from './pages/Audit';
import { Courses } from './pages/Courses';
import { Dashboard } from './pages/Dashboard';
import { Enrollments } from './pages/Enrollments';
import { Login } from './pages/Login';
import { NotFound } from './pages/NotFound';
import { Sessions } from './pages/Sessions';
import { Tags } from './pages/Tags';
import { Users } from './pages/Users';

// Routes are grouped so that every application screen except /login inherits
// the authenticated shell. Role gates are enforced both here (navigation)
// and by the backend (data access); the UI gate avoids confusing forbidden views.
export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="courses" element={<Courses />} />
        <Route path="sessions" element={<Sessions />} />
        <Route path="enrollments" element={<Enrollments />} />
        <Route path="users" element={<ProtectedRoute roles={['admin']}><Users /></ProtectedRoute>} />
        <Route path="tags" element={<ProtectedRoute roles={['admin']}><Tags /></ProtectedRoute>} />
        <Route path="audit" element={<ProtectedRoute roles={['admin']}><Audit /></ProtectedRoute>} />
        <Route path="access-denied" element={<AccessDenied />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
