import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <section className="status-page" data-testid="not-found">
      <span className="status-page__code">404</span>
      <h1>Page not found</h1>
      <p>The page you are looking for does not exist.</p>
      <Link to="/dashboard" className="button button--primary" data-testid="not-found-home">Back to dashboard</Link>
    </section>
  );
}
