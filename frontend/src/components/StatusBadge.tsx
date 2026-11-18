interface StatusBadgeProps {
  status: string;
  testId?: string;
}

const STATUS_TONES: Record<string, string> = {
  pending: 'warning',
  draft: 'warning',
  validated: 'info',
  published: 'success',
  completed: 'success',
  active: 'success',
  cancelled: 'danger',
  archived: 'muted',
};

export function StatusBadge({ status, testId }: StatusBadgeProps) {
  const tone = STATUS_TONES[status.toLowerCase()] ?? 'muted';
  return (
    <span className={`badge badge--${tone}`} data-testid={testId}>
      {status}
    </span>
  );
}
