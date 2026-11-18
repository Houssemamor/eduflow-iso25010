import type { ReactNode } from 'react';

type AlertVariant = 'error' | 'success' | 'info';

interface AlertProps {
  variant?: AlertVariant;
  children: ReactNode;
  testId?: string;
  onDismiss?: () => void;
}

export function Alert({ variant = 'info', children, testId, onDismiss }: AlertProps) {
  return (
    <div
      className={`alert alert--${variant}`}
      role={variant === 'error' ? 'alert' : 'status'}
      data-testid={testId ?? `alert-${variant}`}
    >
      <span className="alert__message">{children}</span>
      {onDismiss ? (
        <button type="button" className="alert__dismiss" onClick={onDismiss} aria-label="Dismiss message">
          &times;
        </button>
      ) : null}
    </div>
  );
}
