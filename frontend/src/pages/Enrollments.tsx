import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api, asPaginated, getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Alert } from '../components/Alert';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import { Modal } from '../components/Modal';
import { Pagination } from '../components/Pagination';
import { Spinner } from '../components/Spinner';
import { StatusBadge } from '../components/StatusBadge';
import type { Course, Enrollment, EnrollmentCreate, Paginated, Session } from '../types';
import { ENROLLMENT_STATUSES } from '../types';

const PAGE_SIZE = 10;

interface AppliedFilters {
  q: string;
  status: string;
  course_id: string;
  date_from: string;
  date_to: string;
}

const EMPTY_FILTERS: AppliedFilters = { q: '', status: '', course_id: '', date_from: '', date_to: '' };
const EMPTY_FORM: EnrollmentCreate = { course_id: 0, session_id: 0 };

export function Enrollments() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const isStaff = user?.role === 'admin' || user?.role === 'formateur';

  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [courses, setCourses] = useState<Course[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [formSessions, setFormSessions] = useState<Session[]>([]);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [courseFilter, setCourseFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [applied, setApplied] = useState<AppliedFilters>(EMPTY_FILTERS);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<EnrollmentCreate>(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Enrollment | null>(null);

  useEffect(() => {
    let active = true;
    api.get<Course[] | { items: Course[] }>('/courses', { limit: 100 })
      .then((data) => { if (active) setCourses(asPaginated(data).items); })
      .catch(() => { /* Optional lookup. */ });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    api.get<Session[] | { items: Session[] }>('/sessions', { limit: 100 })
      .then((data) => { if (active) setSessions(asPaginated(data).items); })
      .catch(() => { /* Optional lookup. */ });
    return () => { active = false; };
  }, []);

  const loadEnrollments = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<Paginated<Enrollment>>('/enrollments', {
        q: applied.q,
        status: applied.status,
        course_id: applied.course_id,
        date_from: applied.date_from,
        date_to: applied.date_to,
        skip,
        limit: PAGE_SIZE,
      });
      setEnrollments(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applied, skip]);

  useEffect(() => {
    void loadEnrollments();
  }, [loadEnrollments]);

  // Load the sessions available for the course chosen in the creation form.
  useEffect(() => {
    if (!form.course_id) {
      setFormSessions([]);
      return;
    }
    let active = true;
    api.get<Session[] | { items: Session[] }>('/sessions', { course_id: form.course_id })
      .then((data) => {
        if (!active) return;
        const items = asPaginated(data).items;
        setFormSessions(items);
        setForm((previous) => (
          previous.session_id && items.some((item) => item.id === previous.session_id)
            ? previous
            : { ...previous, session_id: items[0]?.id ?? 0 }
        ));
      })
      .catch(() => { if (active) setFormSessions([]); });
    return () => { active = false; };
  }, [form.course_id]);

  const handleApply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setApplied({ q: search, status: statusFilter, course_id: courseFilter, date_from: dateFrom, date_to: dateTo });
    setSkip(0);
  };

  const handleReset = () => {
    setSearch('');
    setStatusFilter('');
    setCourseFilter('');
    setDateFrom('');
    setDateTo('');
    setApplied(EMPTY_FILTERS);
    setSkip(0);
  };

  const openCreate = () => {
    setForm({ ...EMPTY_FORM, course_id: courses[0]?.id ?? 0 });
    setFormError('');
    setFormOpen(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!form.course_id || !form.session_id) {
      setFormError('Select a course and a session.');
      return;
    }
    setSaving(true);
    try {
      await api.post('/enrollments', form);
      setSuccess('Enrollment created.');
      setFormOpen(false);
      await loadEnrollments();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (enrollment: Enrollment, status: string) => {
    setError('');
    try {
      await api.patch(`/enrollments/${enrollment.id}/status`, { status });
      setSuccess(`Enrollment ${status}.`);
      await loadEnrollments();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/enrollments/${deleteTarget.id}`);
      setSuccess('Enrollment deleted.');
      setDeleteTarget(null);
      await loadEnrollments();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const courseTitle = (enrollment: Enrollment) =>
    enrollment.course?.title ?? courses.find((course) => course.id === enrollment.course_id)?.title ?? `Course ${enrollment.course_id}`;

  const sessionLabel = (enrollment: Enrollment) => {
    const session = enrollment.session ?? sessions.find((item) => item.id === enrollment.session_id);
    return session ? `${session.room || 'Session'} - ${session.starts_at.substring(0, 16).replace('T', ' ')}` : `Session ${enrollment.session_id}`;
  };

  const learnerLabel = (enrollment: Enrollment) =>
    enrollment.user?.full_name ?? enrollment.user?.email ?? `User ${enrollment.user_id}`;

  const isCancellable = (enrollment: Enrollment) =>
    enrollment.status === 'pending' || enrollment.status === 'validated';

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Enrollments</h1>
          <p className="page__subtitle">Track registrations and manage their lifecycle.</p>
        </div>
        <button type="button" className="button button--primary" onClick={openCreate} data-testid="enrollment-create">New enrollment</button>
      </header>

      <form className="filter-bar" onSubmit={handleApply} data-testid="enrollments-filters">
        <FormField label="Search" htmlFor="enrollments-search">
          <input
            id="enrollments-search"
            type="search"
            placeholder="Learner or course"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            data-testid="enrollments-search"
          />
        </FormField>
        <FormField label="Status" htmlFor="enrollments-filter-status">
          <select
            id="enrollments-filter-status"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            data-testid="enrollments-filter-status"
          >
            <option value="">All statuses</option>
            {ENROLLMENT_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </FormField>
        <FormField label="Course" htmlFor="enrollments-filter-course">
          <select
            id="enrollments-filter-course"
            value={courseFilter}
            onChange={(event) => setCourseFilter(event.target.value)}
            data-testid="enrollments-filter-course"
          >
            <option value="">All courses</option>
            {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
          </select>
        </FormField>
        <FormField label="From" htmlFor="enrollments-filter-date-from">
          <input
            id="enrollments-filter-date-from"
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            data-testid="enrollments-filter-date-from"
          />
        </FormField>
        <FormField label="To" htmlFor="enrollments-filter-date-to">
          <input
            id="enrollments-filter-date-to"
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            data-testid="enrollments-filter-date-to"
          />
        </FormField>
        <div className="filter-bar__actions">
          <button type="submit" className="button button--primary" data-testid="enrollments-apply">Apply</button>
          <button type="button" className="button button--secondary" onClick={handleReset} data-testid="enrollments-reset">Reset</button>
        </div>
      </form>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success" onDismiss={() => setSuccess('')}>{success}</Alert> : null}

      <div className="table-panel">
        {loading ? (
          <div className="table-loading"><Spinner label="Loading enrollments" /></div>
        ) : enrollments.length === 0 ? (
          <p className="empty-state" data-testid="enrollments-empty">No enrollments found.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Learner</th>
                  <th scope="col">Course</th>
                  <th scope="col">Session</th>
                  <th scope="col">Status</th>
                  <th scope="col">Created</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {enrollments.map((enrollment) => (
                  <tr key={enrollment.id} data-testid={`enrollment-row-${enrollment.id}`}>
                    <td className="cell-strong">{learnerLabel(enrollment)}</td>
                    <td>{courseTitle(enrollment)}</td>
                    <td>{sessionLabel(enrollment)}</td>
                    <td><StatusBadge status={enrollment.status} /></td>
                    <td>{enrollment.created_at ? enrollment.created_at.substring(0, 10) : '-'}</td>
                    <td>
                      <div className="row-actions">
                        {isStaff && enrollment.status === 'pending' ? (
                          <button
                            type="button"
                            className="button button--primary button--small"
                            onClick={() => void changeStatus(enrollment, 'validated')}
                            data-testid={`enrollment-validate-${enrollment.id}`}
                          >
                            Validate
                          </button>
                        ) : null}
                        {isStaff && enrollment.status === 'validated' ? (
                          <button
                            type="button"
                            className="button button--primary button--small"
                            onClick={() => void changeStatus(enrollment, 'completed')}
                            data-testid={`enrollment-complete-${enrollment.id}`}
                          >
                            Complete
                          </button>
                        ) : null}
                        {(isStaff || enrollment.user_id === user?.id) && isCancellable(enrollment) ? (
                          <button
                            type="button"
                            className="button button--secondary button--small"
                            onClick={() => void changeStatus(enrollment, 'cancelled')}
                            data-testid={`enrollment-cancel-${enrollment.id}`}
                          >
                            Cancel
                          </button>
                        ) : null}
                        {isAdmin ? (
                          <button
                            type="button"
                            className="button button--danger button--small"
                            onClick={() => setDeleteTarget(enrollment)}
                            data-testid={`enrollment-delete-${enrollment.id}`}
                          >
                            Delete
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Pagination total={total} skip={skip} limit={PAGE_SIZE} onPageChange={setSkip} testIdPrefix="enrollments" />

      <Modal
        open={formOpen}
        title="New enrollment"
        onClose={() => setFormOpen(false)}
        testId="enrollment-form-modal"
        footer={
          <>
            <button type="button" className="button button--secondary" onClick={() => setFormOpen(false)} data-testid="enrollment-cancel-create">Cancel</button>
            <button type="submit" form="enrollment-form" className="button button--primary" disabled={saving} data-testid="enrollment-submit">
              {saving ? 'Saving...' : 'Create'}
            </button>
          </>
        }
      >
        <form id="enrollment-form" onSubmit={handleSubmit} className="form-grid">
          {formError ? <Alert variant="error">{formError}</Alert> : null}
          <FormField label="Course" htmlFor="enrollment-field-course">
            <select
              id="enrollment-field-course"
              required
              value={form.course_id}
              onChange={(event) => setForm({ course_id: Number(event.target.value), session_id: 0 })}
              data-testid="enrollment-field-course"
            >
              <option value={0} disabled>Select a course</option>
              {courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}
            </select>
          </FormField>
          <FormField label="Session" htmlFor="enrollment-field-session">
            <select
              id="enrollment-field-session"
              required
              value={form.session_id}
              onChange={(event) => setForm({ ...form, session_id: Number(event.target.value) })}
              data-testid="enrollment-field-session"
            >
              <option value={0} disabled>Select a session</option>
              {formSessions.map((session) => (
                <option key={session.id} value={session.id}>
                  {session.room || 'Session'} - {session.starts_at.substring(0, 16).replace('T', ' ')}
                </option>
              ))}
            </select>
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete enrollment"
        message="Delete this enrollment? This action cannot be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}
