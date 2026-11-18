import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api, asPaginated, getErrorMessage } from '../api/client';
import { Alert } from '../components/Alert';
import { FormField } from '../components/FormField';
import { Spinner } from '../components/Spinner';
import type { AuditEvent, Paginated } from '../types';

export function Audit() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [actorId, setActorId] = useState('');
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [applied, setApplied] = useState({ actor_id: '', action: '', date_from: '', date_to: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<AuditEvent[] | Paginated<AuditEvent>>('/audit', {
        actor_id: applied.actor_id,
        action: applied.action,
        date_from: applied.date_from,
        date_to: applied.date_to,
      });
      setEvents(asPaginated(data).items);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applied]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const handleApply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setApplied({ actor_id: actorId, action: action.trim(), date_from: dateFrom, date_to: dateTo });
  };

  const handleReset = () => {
    setActorId('');
    setAction('');
    setDateFrom('');
    setDateTo('');
    setApplied({ actor_id: '', action: '', date_from: '', date_to: '' });
  };

  const timestamp = (event: AuditEvent) => event.created_at ?? event.timestamp ?? '-';
  const actor = (event: AuditEvent) => event.actor_email ?? `User ${event.actor_id}`;
  const target = (event: AuditEvent) =>
    event.target_type ? `${event.target_type}${event.target_id !== undefined ? ` #${event.target_id}` : ''}` : '-';
  const details = (event: AuditEvent) => {
    if (event.details === undefined || event.details === null) return '-';
    return typeof event.details === 'string' ? event.details : JSON.stringify(event.details);
  };

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Audit log</h1>
          <p className="page__subtitle">Review security-relevant actions across the platform.</p>
        </div>
      </header>

      <form className="filter-bar" onSubmit={handleApply} data-testid="audit-filters">
        <FormField label="Actor ID" htmlFor="audit-filter-actor">
          <input
            id="audit-filter-actor"
            type="number"
            min={1}
            placeholder="Any"
            value={actorId}
            onChange={(event) => setActorId(event.target.value)}
            data-testid="audit-filter-actor"
          />
        </FormField>
        <FormField label="Action" htmlFor="audit-filter-action">
          <input
            id="audit-filter-action"
            type="search"
            placeholder="e.g. login"
            value={action}
            onChange={(event) => setAction(event.target.value)}
            data-testid="audit-filter-action"
          />
        </FormField>
        <FormField label="From" htmlFor="audit-filter-date-from">
          <input
            id="audit-filter-date-from"
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            data-testid="audit-filter-date-from"
          />
        </FormField>
        <FormField label="To" htmlFor="audit-filter-date-to">
          <input
            id="audit-filter-date-to"
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            data-testid="audit-filter-date-to"
          />
        </FormField>
        <div className="filter-bar__actions">
          <button type="submit" className="button button--primary" data-testid="audit-apply">Apply</button>
          <button type="button" className="button button--secondary" onClick={handleReset} data-testid="audit-reset">Reset</button>
        </div>
      </form>

      {error ? <Alert variant="error">{error}</Alert> : null}

      <div className="table-panel">
        {loading ? (
          <div className="table-loading"><Spinner label="Loading audit events" /></div>
        ) : events.length === 0 ? (
          <p className="empty-state" data-testid="audit-empty">No audit events found.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Actor</th>
                  <th scope="col">Action</th>
                  <th scope="col">Target</th>
                  <th scope="col">Details</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event, index) => (
                  <tr key={`${event.id}-${index}`} data-testid={`audit-row-${event.id}`}>
                    <td>{timestamp(event)}</td>
                    <td>{actor(event)}</td>
                    <td className="cell-strong">{event.action}</td>
                    <td>{target(event)}</td>
                    <td className="cell-muted">{details(event)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
