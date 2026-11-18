import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api, asPaginated, getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Alert } from '../components/Alert';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import { Modal } from '../components/Modal';
import { Spinner } from '../components/Spinner';
import type { Course, Session, SessionCreate } from '../types';

const EMPTY_FORM: SessionCreate = { course_id: 0, starts_at: '', ends_at: '', room: '', capacity: 1 };

/** Converts a backend datetime into the value expected by <input type="datetime-local">. */
function toDateTimeLocal(value: string): string {
  return value && value.length >= 16 ? value.substring(0, 16) : value;
}

/** Supplies the seconds component some API validators require. */
function toServerDateTime(value: string): string {
  return value.length === 16 ? `${value}:00` : value;
}

export function Sessions() {
  const { user } = useAuth();
  const canManage = user?.role === 'admin' || user?.role === 'formateur';

  const [sessions, setSessions] = useState<Session[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseFilter, setCourseFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [applied, setApplied] = useState({ course_id: '', date_from: '', date_to: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Session | null>(null);
  const [form, setForm] = useState<SessionCreate>(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Session | null>(null);

  useEffect(() => {
    let active = true;
    api.get<Course[] | { items: Course[] }>('/courses', { limit: 100 })
      .then((data) => { if (active) setCourses(asPaginated(data).items); })
      .catch(() => { /* Filters remain usable without the lookup. */ });
    return () => { active = false; };
  }, []);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<Session[] | { items: Session[] }>('/sessions', {
        course_id: applied.course_id,
        date_from: applied.date_from,
        date_to: applied.date_to,
      });
      setSessions(asPaginated(data).items);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applied]);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const handleApply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setApplied({ course_id: courseFilter, date_from: dateFrom, date_to: dateTo });
  };

  const handleReset = () => {
    setCourseFilter('');
    setDateFrom('');
    setDateTo('');
    setApplied({ course_id: '', date_from: '', date_to: '' });
  };

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, course_id: courses[0]?.id ?? 0 });
    setFormError('');
    setFormOpen(true);
  };

  const openEdit = (session: Session) => {
    setEditing(session);
    setForm({
      course_id: session.course_id,
      starts_at: toDateTimeLocal(session.starts_at),
      ends_at: toDateTimeLocal(session.ends_at),
      room: session.room ?? '',
      capacity: session.capacity,
    });
    setFormError('');
    setFormOpen(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (form.starts_at && form.ends_at && form.ends_at <= form.starts_at) {
      setFormError('End time must be after start time.');
      return;
    }
    setSaving(true);
    try {
      const payload: SessionCreate = {
        ...form,
        starts_at: toServerDateTime(form.starts_at),
        ends_at: toServerDateTime(form.ends_at),
      };
      if (editing) {
        await api.patch(`/sessions/${editing.id}`, payload);
        setSuccess('Session updated.');
      } else {
        await api.post('/sessions', payload);
        setSuccess('Session created.');
      }
      setFormOpen(false);
      await loadSessions();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/sessions/${deleteTarget.id}`);
      setSuccess('Session deleted.');
      setDeleteTarget(null);
      await loadSessions();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const courseTitle = (session: Session) =>
    session.course?.title ?? courses.find((course) => course.id === session.course_id)?.title ?? `Course ${session.course_id}`;

  const formatDate = (value: string) => {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  };

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Sessions</h1>
          <p className="page__subtitle">Schedule and manage individual course sessions.</p>
        </div>
        {canManage ? (
          <button type="button" className="button button--primary" onClick={openCreate} data-testid="session-create">New session</button>
        ) : null}
      </header>

      <form className="filter-bar" onSubmit={handleApply} data-testid="sessions-filters">
        <FormField label="Course" htmlFor="sessions-filter-course">
          <select
            id="sessions-filter-course"
            value={courseFilter}
            onChange={(event) => setCourseFilter(event.target.value)}
            data-testid="sessions-filter-course"
          >
            <option value="">All courses</option>
            {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
          </select>
        </FormField>
        <FormField label="From" htmlFor="sessions-filter-date-from">
          <input
            id="sessions-filter-date-from"
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            data-testid="sessions-filter-date-from"
          />
        </FormField>
        <FormField label="To" htmlFor="sessions-filter-date-to">
          <input
            id="sessions-filter-date-to"
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            data-testid="sessions-filter-date-to"
          />
        </FormField>
        <div className="filter-bar__actions">
          <button type="submit" className="button button--primary" data-testid="sessions-apply">Apply</button>
          <button type="button" className="button button--secondary" onClick={handleReset} data-testid="sessions-reset">Reset</button>
        </div>
      </form>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success" onDismiss={() => setSuccess('')}>{success}</Alert> : null}

      <div className="table-panel">
        {loading ? (
          <div className="table-loading"><Spinner label="Loading sessions" /></div>
        ) : sessions.length === 0 ? (
          <p className="empty-state" data-testid="sessions-empty">No sessions found.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Course</th>
                  <th scope="col">Starts</th>
                  <th scope="col">Ends</th>
                  <th scope="col">Room</th>
                  <th scope="col">Capacity</th>
                  {canManage ? <th scope="col">Actions</th> : null}
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id} data-testid={`session-row-${session.id}`}>
                    <td className="cell-strong">{courseTitle(session)}</td>
                    <td>{formatDate(session.starts_at)}</td>
                    <td>{formatDate(session.ends_at)}</td>
                    <td>{session.room || '-'}</td>
                    <td>{session.capacity}</td>
                    {canManage ? (
                      <td>
                        <div className="row-actions">
                          <button
                            type="button"
                            className="button button--secondary button--small"
                            onClick={() => openEdit(session)}
                            data-testid={`session-edit-${session.id}`}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="button button--danger button--small"
                            onClick={() => setDeleteTarget(session)}
                            data-testid={`session-delete-${session.id}`}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal
        open={formOpen}
        title={editing ? 'Edit session' : 'New session'}
        onClose={() => setFormOpen(false)}
        testId="session-form-modal"
        footer={
          <>
            <button type="button" className="button button--secondary" onClick={() => setFormOpen(false)} data-testid="session-cancel">Cancel</button>
            <button type="submit" form="session-form" className="button button--primary" disabled={saving} data-testid="session-submit">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </>
        }
      >
        <form id="session-form" onSubmit={handleSubmit} className="form-grid">
          {formError ? <Alert variant="error">{formError}</Alert> : null}
          <FormField label="Course" htmlFor="session-field-course">
            <select
              id="session-field-course"
              required
              value={form.course_id}
              onChange={(event) => setForm({ ...form, course_id: Number(event.target.value) })}
              data-testid="session-field-course"
            >
              <option value={0} disabled>Select a course</option>
              {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
            </select>
          </FormField>
          <div className="form-grid__row">
            <FormField label="Starts at" htmlFor="session-field-starts-at">
              <input
                id="session-field-starts-at"
                type="datetime-local"
                required
                value={form.starts_at}
                onChange={(event) => setForm({ ...form, starts_at: event.target.value })}
                data-testid="session-field-starts-at"
              />
            </FormField>
            <FormField label="Ends at" htmlFor="session-field-ends-at">
              <input
                id="session-field-ends-at"
                type="datetime-local"
                required
                value={form.ends_at}
                onChange={(event) => setForm({ ...form, ends_at: event.target.value })}
                data-testid="session-field-ends-at"
              />
            </FormField>
          </div>
          <div className="form-grid__row">
            <FormField label="Room" htmlFor="session-field-room">
              <input
                id="session-field-room"
                required
                value={form.room}
                onChange={(event) => setForm({ ...form, room: event.target.value })}
                data-testid="session-field-room"
              />
            </FormField>
            <FormField label="Capacity" htmlFor="session-field-capacity">
              <input
                id="session-field-capacity"
                type="number"
                min={1}
                required
                value={form.capacity}
                onChange={(event) => setForm({ ...form, capacity: Number(event.target.value) })}
                data-testid="session-field-capacity"
              />
            </FormField>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete session"
        message="Delete this session? This action cannot be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}
