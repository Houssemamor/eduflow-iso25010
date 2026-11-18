import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api, asPaginated, getErrorMessage } from '../api/client';
import { Alert } from '../components/Alert';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import { Modal } from '../components/Modal';
import { Pagination } from '../components/Pagination';
import { Spinner } from '../components/Spinner';
import type { Paginated, Role, User, UserCreate } from '../types';
import { ROLES } from '../types';

const PAGE_SIZE = 10;
const EMPTY_FORM: UserCreate = { email: '', password: '', full_name: '', role: 'apprenant' };

export function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<UserCreate>(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<User[] | Paginated<User>>('/users');
      setUsers(asPaginated(data).items);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError('');
    setFormOpen(true);
  };

  const openEdit = (user: User) => {
    setEditing(user);
    setForm({ email: user.email, password: '', full_name: user.full_name, role: user.role });
    setFormError('');
    setFormOpen(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!editing && !form.password) {
      setFormError('A password is required for new users.');
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        // An empty password means "keep the existing one" on update.
        const payload = {
          email: form.email,
          full_name: form.full_name,
          role: form.role,
          ...(form.password ? { password: form.password } : {}),
        };
        await api.patch(`/users/${editing.id}`, payload);
        setSuccess('User updated.');
      } else {
        await api.post('/users', form);
        setSuccess('User created.');
      }
      setFormOpen(false);
      await loadUsers();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/users/${deleteTarget.id}`);
      setSuccess('User deleted.');
      setDeleteTarget(null);
      await loadUsers();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const visibleUsers = users.slice(skip, skip + PAGE_SIZE);

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Users</h1>
          <p className="page__subtitle">Manage accounts and role assignments.</p>
        </div>
        <button type="button" className="button button--primary" onClick={openCreate} data-testid="user-create">New user</button>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success" onDismiss={() => setSuccess('')}>{success}</Alert> : null}

      <div className="table-panel">
        {loading ? (
          <div className="table-loading"><Spinner label="Loading users" /></div>
        ) : visibleUsers.length === 0 ? (
          <p className="empty-state" data-testid="users-empty">No users found.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Email</th>
                  <th scope="col">Role</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleUsers.map((user) => (
                  <tr key={user.id} data-testid={`user-row-${user.id}`}>
                    <td className="cell-strong">{user.full_name}</td>
                    <td>{user.email}</td>
                    <td><span className="badge badge--info">{user.role}</span></td>
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="button button--secondary button--small"
                          onClick={() => openEdit(user)}
                          data-testid={`user-edit-${user.id}`}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="button button--danger button--small"
                          onClick={() => setDeleteTarget(user)}
                          data-testid={`user-delete-${user.id}`}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Pagination total={users.length} skip={skip} limit={PAGE_SIZE} onPageChange={setSkip} testIdPrefix="users" />

      <Modal
        open={formOpen}
        title={editing ? 'Edit user' : 'New user'}
        onClose={() => setFormOpen(false)}
        testId="user-form-modal"
        footer={
          <>
            <button type="button" className="button button--secondary" onClick={() => setFormOpen(false)} data-testid="user-cancel">Cancel</button>
            <button type="submit" form="user-form" className="button button--primary" disabled={saving} data-testid="user-submit">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </>
        }
      >
        <form id="user-form" onSubmit={handleSubmit} className="form-grid">
          {formError ? <Alert variant="error">{formError}</Alert> : null}
          <FormField label="Full name" htmlFor="user-field-full-name">
            <input
              id="user-field-full-name"
              required
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
              data-testid="user-field-full-name"
            />
          </FormField>
          <FormField label="Email address" htmlFor="user-field-email">
            <input
              id="user-field-email"
              type="email"
              required
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              data-testid="user-field-email"
            />
          </FormField>
          <FormField
            label="Password"
            htmlFor="user-field-password"
            hint={editing ? 'Leave blank to keep the current password.' : undefined}
          >
            <input
              id="user-field-password"
              type="password"
              autoComplete="new-password"
              required={!editing}
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              data-testid="user-field-password"
            />
          </FormField>
          <FormField label="Role" htmlFor="user-field-role">
            <select
              id="user-field-role"
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value as Role })}
              data-testid="user-field-role"
            >
              {ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
            </select>
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete user"
        message={`Delete "${deleteTarget?.full_name ?? ''}"? This action cannot be undone.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}
