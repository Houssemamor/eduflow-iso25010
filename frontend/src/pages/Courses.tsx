import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, asPaginated, getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Alert } from '../components/Alert';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import { Modal } from '../components/Modal';
import { Pagination } from '../components/Pagination';
import { Spinner } from '../components/Spinner';
import { StatusBadge } from '../components/StatusBadge';
import type { Course, CourseCreate, CourseStatus, Paginated, Tag } from '../types';
import { COURSE_STATUSES } from '../types';

const PAGE_SIZE = 10;

interface AppliedFilters {
  q: string;
  status: string;
  tag_id: string;
}

const EMPTY_FILTERS: AppliedFilters = { q: '', status: '', tag_id: '' };
const EMPTY_FORM: CourseCreate = { title: '', description: '', capacity: 1, status: 'draft', tag_ids: [] };

export function Courses() {
  const { user } = useAuth();
  const canManage = user?.role === 'admin' || user?.role === 'formateur';
  const isAdmin = user?.role === 'admin';

  const [courses, setCourses] = useState<Course[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [tags, setTags] = useState<Tag[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [applied, setApplied] = useState<AppliedFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Course | null>(null);
  const [form, setForm] = useState<CourseCreate>(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Course | null>(null);

  const loadCourses = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<Paginated<Course>>('/courses', {
        q: applied.q,
        status: applied.status,
        tag_id: applied.tag_id,
        skip,
        limit: PAGE_SIZE,
      });
      setCourses(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applied, skip]);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  useEffect(() => {
    let active = true;
    api.get<Tag[] | Paginated<Tag>>('/tags')
      .then((data) => { if (active) setTags(asPaginated(data).items); })
      .catch(() => { /* Tag filter is optional if the lookup fails. */ });
    return () => { active = false; };
  }, []);

  const handleApply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setApplied({ q: search, status: statusFilter, tag_id: tagFilter });
    setSkip(0);
  };

  const handleReset = () => {
    setSearch('');
    setStatusFilter('');
    setTagFilter('');
    setApplied(EMPTY_FILTERS);
    setSkip(0);
  };

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError('');
    setFormOpen(true);
  };

  const openEdit = (course: Course) => {
    setEditing(course);
    setForm({
      title: course.title,
      description: course.description ?? '',
      capacity: course.capacity,
      status: (COURSE_STATUSES.includes(course.status as CourseStatus) ? course.status : 'draft') as CourseStatus,
      tag_ids: course.tag_ids ?? [],
    });
    setFormError('');
    setFormOpen(true);
  };

  const toggleTag = (tagId: number) => {
    setForm((previous) => ({
      ...previous,
      tag_ids: previous.tag_ids.includes(tagId)
        ? previous.tag_ids.filter((id) => id !== tagId)
        : [...previous.tag_ids, tagId],
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    setSaving(true);
    try {
      if (editing) {
        await api.patch(`/courses/${editing.id}`, form);
        setSuccess('Course updated.');
      } else {
        await api.post('/courses', form);
        setSuccess('Course created.');
      }
      setFormOpen(false);
      await loadCourses();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/courses/${deleteTarget.id}`);
      setSuccess('Course deleted.');
      setDeleteTarget(null);
      await loadCourses();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const statusOptions = editing && !COURSE_STATUSES.includes(editing.status as CourseStatus)
    ? [editing.status, ...COURSE_STATUSES]
    : COURSE_STATUSES;

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Courses</h1>
          <p className="page__subtitle">Browse and manage the training catalogue.</p>
        </div>
        <div className="page__header-actions">
          {isAdmin ? <Link to="/tags" className="button button--secondary" data-testid="manage-tags-link">Manage tags</Link> : null}
          {canManage ? (
            <button type="button" className="button button--primary" onClick={openCreate} data-testid="course-create">New course</button>
          ) : null}
        </div>
      </header>

      <form className="filter-bar" onSubmit={handleApply} data-testid="courses-filters">
        <FormField label="Search" htmlFor="courses-search">
          <input
            id="courses-search"
            type="search"
            placeholder="Title or description"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            data-testid="courses-search"
          />
        </FormField>
        <FormField label="Status" htmlFor="courses-status-filter">
          <select
            id="courses-status-filter"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            data-testid="courses-status-filter"
          >
            <option value="">All statuses</option>
            {COURSE_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </FormField>
        <FormField label="Tag" htmlFor="courses-tag-filter">
          <select
            id="courses-tag-filter"
            value={tagFilter}
            onChange={(event) => setTagFilter(event.target.value)}
            data-testid="courses-tag-filter"
          >
            <option value="">All tags</option>
            {tags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}
          </select>
        </FormField>
        <div className="filter-bar__actions">
          <button type="submit" className="button button--primary" data-testid="courses-apply">Apply</button>
          <button type="button" className="button button--secondary" onClick={handleReset} data-testid="courses-reset">Reset</button>
        </div>
      </form>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success" onDismiss={() => setSuccess('')}>{success}</Alert> : null}

      <div className="table-panel">
        {loading ? (
          <div className="table-loading"><Spinner label="Loading courses" /></div>
        ) : courses.length === 0 ? (
          <p className="empty-state" data-testid="courses-empty">No courses found.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Title</th>
                  <th scope="col">Status</th>
                  <th scope="col">Capacity</th>
                  <th scope="col">Tags</th>
                  {canManage ? <th scope="col">Actions</th> : null}
                </tr>
              </thead>
              <tbody>
                {courses.map((course) => (
                  <tr key={course.id} data-testid={`course-row-${course.id}`}>
                    <td>
                      <span className="cell-strong">{course.title}</span>
                      {course.description ? <span className="cell-muted">{course.description}</span> : null}
                    </td>
                    <td><StatusBadge status={course.status} /></td>
                    <td>{course.capacity}</td>
                    <td>
                      {course.tags && course.tags.length > 0
                        ? course.tags.map((tag) => <span className="tag-pill" key={tag.id}>{tag.name}</span>)
                        : <span className="muted">-</span>}
                    </td>
                    {canManage ? (
                      <td>
                        <div className="row-actions">
                          <button
                            type="button"
                            className="button button--secondary button--small"
                            onClick={() => openEdit(course)}
                            data-testid={`course-edit-${course.id}`}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="button button--danger button--small"
                            onClick={() => setDeleteTarget(course)}
                            data-testid={`course-delete-${course.id}`}
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

      <Pagination total={total} skip={skip} limit={PAGE_SIZE} onPageChange={setSkip} testIdPrefix="courses" />

      <Modal
        open={formOpen}
        title={editing ? 'Edit course' : 'New course'}
        onClose={() => setFormOpen(false)}
        testId="course-form-modal"
        footer={
          <>
            <button type="button" className="button button--secondary" onClick={() => setFormOpen(false)} data-testid="course-cancel">Cancel</button>
            <button type="submit" form="course-form" className="button button--primary" disabled={saving} data-testid="course-submit">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </>
        }
      >
        <form id="course-form" onSubmit={handleSubmit} className="form-grid">
          {formError ? <Alert variant="error">{formError}</Alert> : null}
          <FormField label="Title" htmlFor="course-field-title">
            <input
              id="course-field-title"
              required
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              data-testid="course-field-title"
            />
          </FormField>
          <FormField label="Description" htmlFor="course-field-description">
            <textarea
              id="course-field-description"
              rows={3}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              data-testid="course-field-description"
            />
          </FormField>
          <div className="form-grid__row">
            <FormField label="Capacity" htmlFor="course-field-capacity">
              <input
                id="course-field-capacity"
                type="number"
                min={1}
                required
                value={form.capacity}
                onChange={(event) => setForm({ ...form, capacity: Number(event.target.value) })}
                data-testid="course-field-capacity"
              />
            </FormField>
            <FormField label="Status" htmlFor="course-field-status">
              <select
                id="course-field-status"
                value={form.status}
                onChange={(event) => setForm({ ...form, status: event.target.value as CourseStatus })}
                data-testid="course-field-status"
              >
                {statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </FormField>
          </div>
          <fieldset className="form-fieldset">
            <legend>Tags</legend>
            <div className="checkbox-grid">
              {tags.length === 0 ? <span className="muted">No tags defined yet.</span> : null}
              {tags.map((tag) => (
                <label className="checkbox-label" key={tag.id}>
                  <input
                    type="checkbox"
                    checked={form.tag_ids.includes(tag.id)}
                    onChange={() => toggleTag(tag.id)}
                    data-testid={`course-field-tag-${tag.id}`}
                  />
                  <span>{tag.name}</span>
                </label>
              ))}
            </div>
          </fieldset>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete course"
        message={`Delete "${deleteTarget?.title ?? ''}"? This action cannot be undone.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}
