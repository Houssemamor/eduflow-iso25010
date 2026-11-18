interface PaginationProps {
  total: number;
  skip: number;
  limit: number;
  onPageChange: (newSkip: number) => void;
  testIdPrefix: string;
}

export function Pagination({ total, skip, limit, onPageChange, testIdPrefix }: PaginationProps) {
  const safeLimit = limit > 0 ? limit : 20;
  const page = Math.floor(skip / safeLimit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / safeLimit));
  const previousDisabled = skip <= 0;
  const nextDisabled = skip + safeLimit >= total;

  return (
    <nav className="pagination" aria-label="Pagination" data-testid={`${testIdPrefix}-pagination`}>
      <button
        type="button"
        className="button button--secondary button--small"
        onClick={() => onPageChange(Math.max(0, skip - safeLimit))}
        disabled={previousDisabled}
        data-testid={`${testIdPrefix}-prev`}
      >
        Previous
      </button>
      <span className="pagination__info" data-testid={`${testIdPrefix}-page-info`}>
        Page {page} of {pageCount} &middot; {total} total
      </span>
      <button
        type="button"
        className="button button--secondary button--small"
        onClick={() => onPageChange(skip + safeLimit)}
        disabled={nextDisabled}
        data-testid={`${testIdPrefix}-next`}
      >
        Next
      </button>
    </nav>
  );
}
