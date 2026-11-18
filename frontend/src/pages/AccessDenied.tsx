import { Link } from 'react-router-dom';

export function AccessDenied() {
  return (
    <section className="status-page" data-testid="access-denied">
      <span className="status-page__code">403</span>
      <h1>Access denied</h1>
      <p>You do not have permission to view this page.</p>
      <Link to="/dashboard" className="button button--primary" data-testid="access-denied-home">Back to dashboard</Link>
    </section>
  );
}
