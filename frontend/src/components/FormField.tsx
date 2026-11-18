import type { ReactNode } from 'react';

interface FormFieldProps {
  label: string;
  htmlFor: string;
  children: ReactNode;
  hint?: string;
  error?: string;
}

/** Consistent label/control pairing so every field is keyboard and screen-reader accessible. */
export function FormField({ label, htmlFor, children, hint, error }: FormFieldProps) {
  return (
    <div className="form-field">
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {hint ? <small className="form-field__hint">{hint}</small> : null}
      {error ? <small className="form-field__error">{error}</small> : null}
    </div>
  );
}
