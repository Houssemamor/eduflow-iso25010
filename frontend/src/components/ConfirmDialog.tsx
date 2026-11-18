import { useEffect, useRef } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Accessible confirmation modal used before destructive actions. */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    confirmRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onMouseDown={onCancel}>
      <div
        className="modal modal--small"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        data-testid="confirm-dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 id="confirm-dialog-title" className="modal__title">{title}</h2>
        <p id="confirm-dialog-message" className="modal__text">{message}</p>
        <div className="modal__actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={onCancel}
            data-testid="confirm-cancel"
          >
            Cancel
          </button>
          <button
            ref={confirmRef}
            type="button"
            className={destructive ? 'button button--danger' : 'button button--primary'}
            onClick={onConfirm}
            data-testid="confirm-accept"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
