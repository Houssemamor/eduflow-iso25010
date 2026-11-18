import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api, asPaginated, getErrorMessage } from '../api/client';
import { Alert } from '../components/Alert';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import { Modal } from '../components/Modal';
import { Spinner } from '../components/Spinner';
import type { Paginated, Tag } from '../types';

export function Tags() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Tag | null>(null);
  const [name, setName] = useState('');
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Tag | null>(null);

  const loadTags = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<Tag[] | Paginated<Tag>>('/tags');
      setTags(asPaginated(data).items);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTags();
  }, [loadTags]);

  const openCreate = () => {
    setEditing(null);
    setName('');
    setFormError('');
    setFormOpen(true);
  };

  const openEdit = (tag: Tag) => {
    setEditing(tag);
    setName(tag.name);
    setFormError('');
    setFormOpen(true);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    setSaving(true);
    try {
      if (editing) {
        await api.patch(`/tags/${editing.id}`, { name: name.trim() });
        setSuccess('Tag updated.');
      } else {
        await api.post('/tags', { name: name.trim() });
        setSuccess('Tag created.');
      }
      setFormOpen(false);
      await loadTags();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/tags/${deleteTarget.id}`);
      setSuccess('Tag deleted.');
      setDeleteTarget(null);
      await loadTags();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Tags</h1>
          <p className="page__subtitle">Categories used to classify courses.</p>
        </div>
        <button type="button" className="button button--primary" onClick={openCreate} data-testid="tag-create">New tag</button>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success" onDismiss={() => setSuccess('')}>{success}</Alert> : null}

      <div className="table-panel">
        {loading ? (
          <div className="table-loading"><Spinner label="Loading tags" /></div>
        ) : tags.length === 0 ? (
          <p className="empty-state" data-testid="tags-empty">No tags found.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {tags.map((tag) => (
                  <tr key={tag.id} data-testid={`tag-row-${tag.id}`}>
                    <td className="cell-strong">{tag.name}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="button button--secondary button--small"
                          onClick={() => openEdit(tag)}
                          data-testid={`tag-edit-${tag.id}`}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="button button--danger button--small"
                          onClick={() => setDeleteTarget(tag)}
                          data-testid={`tag-delete-${tag.id}`}
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

      <Modal
        open={formOpen}
        title={editing ? 'Edit tag' : 'New tag'}
        onClose={() => setFormOpen(false)}
        testId="tag-form-modal"
        footer={
          <>
            <button type="button" className="button button--secondary" onClick={() => setFormOpen(false)} data-testid="tag-cancel">Cancel</button>
            <button type="submit" form="tag-form" className="button button--primary" disabled={saving} data-testid="tag-submit">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </>
        }
      >
        <form id="tag-form" onSubmit={handleSubmit} className="form-grid">
          {formError ? <Alert variant="error">{formError}</Alert> : null}
          <FormField label="Name" htmlFor="tag-field-name">
            <input
              id="tag-field-name"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              data-testid="tag-field-name"
            />
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete tag"
        message={`Delete "${deleteTarget?.name ?? ''}"? This action cannot be undone.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}
