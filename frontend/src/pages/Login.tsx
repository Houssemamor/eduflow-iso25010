import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Alert } from '../components/Alert';
import { FormField } from '../components/FormField';
import { Spinner } from '../components/Spinner';

interface LocationState {
  from?: string;
}

export function Login() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (isLoading) {
    return (
      <div className="center-screen" data-testid="loading">
        <Spinner label="Checking session" />
      </div>
    );
  }

  if (isAuthenticated) {
    const from = (location.state as LocationState | null)?.from ?? '/dashboard';
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      const from = (location.state as LocationState | null)?.from ?? '/dashboard';
      navigate(from, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__brand">
          <span className="login-card__logo" aria-hidden="true">E</span>
          <h1>EduFlow</h1>
          <p>E-learning management</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form" noValidate={false}>
          {error ? <Alert variant="error" testId="login-error">{error}</Alert> : null}

          <FormField label="Email address" htmlFor="login-email">
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              data-testid="login-email"
            />
          </FormField>

          <FormField label="Password" htmlFor="login-password">
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              data-testid="login-password"
            />
          </FormField>

          <button
            type="submit"
            className="button button--primary button--block"
            disabled={submitting}
            data-testid="login-submit"
          >
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="login-hint" data-testid="demo-credentials">
          <strong>Demo hint</strong>
          <p>
            Accounts follow the pattern <code>admin@eduflow.com</code>,{' '}
            <code>formateur@eduflow.com</code> or <code>apprenant@eduflow.com</code>.
            Use the password supplied with your environment setup.
          </p>
        </div>
      </div>
    </div>
  );
}
