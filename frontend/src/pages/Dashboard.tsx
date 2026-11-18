import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api, asPaginated, getErrorMessage } from '../api/client';
import { Alert } from '../components/Alert';
import { FormField } from '../components/FormField';
import type { Course, DashboardMetrics, EnrollmentStatus } from '../types';
import { ENROLLMENT_STATUSES } from '../types';

const METRIC_LABELS: Record<string, string> = {
  total_courses: 'Total courses',
  total_enrollments: 'Total enrollments',
  total_users: 'Total users',
  total_sessions: 'Total sessions',
  active_courses: 'Active courses',
  pending_enrollments: 'Pending enrollments',
  validated_enrollments: 'Validated enrollments',
  completed_enrollments: 'Completed enrollments',
  cancelled_enrollments: 'Cancelled enrollments',
  occupancy_rate: 'Occupancy rate (%)',
};

interface AppliedFilters {
  course_id: string;
  status: string;
  date_from: string;
  date_to: string;
}

const EMPTY_FILTERS: AppliedFilters = { course_id: '', status: '', date_from: '', date_to: '' };

interface BreakdownRow {
  label: string;
  count: number;
}

function buildBreakdown(metrics: DashboardMetrics): BreakdownRow[] {
  if (metrics.enrollments_by_status) {
    return metrics.enrollments_by_status.map((entry) => ({ label: entry.status, count: entry.count }));
  }
  if (metrics.courses_by_status) {
    return metrics.courses_by_status.map((entry) => ({ label: entry.status, count: entry.count }));
  }
  if (metrics.enrollments_by_course) {
    return metrics.enrollments_by_course.map((entry) => ({
      label: entry.title ?? entry.course ?? `Course ${entry.course_id ?? ''}`.trim(),
      count: entry.count,
    }));
  }
  return [];
}

export function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics>({});
  const [courses, setCourses] = useState<Course[]>([]);
  const [draft, setDraft] = useState<AppliedFilters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<AppliedFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api.get<Course[] | { items: Course[] }>('/courses', { limit: 100 })
      .then((data) => {
        if (active) setCourses(asPaginated(data).items);
      })
      .catch(() => {
        // The course filter is optional; metrics still load if this lookup fails.
      });
    return () => { active = false; };
  }, []);

  const loadMetrics = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.get<DashboardMetrics>('/dashboard', {
        course_id: applied.course_id,
        status: applied.status,
        date_from: applied.date_from,
        date_to: applied.date_to,
      });
      setMetrics(data ?? {});
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applied]);

  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  const handleApply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setApplied({ ...draft });
  };

  const handleReset = () => {
    setDraft(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
  };

  const metricKeys = Object.keys(METRIC_LABELS).filter(
    (key) => typeof metrics[key] === 'number',
  );
  const breakdown = buildBreakdown(metrics);
  const maxCount = Math.max(1, ...breakdown.map((row) => row.count));

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Dashboard</h1>
          <p className="page__subtitle">Overview of training activity and enrollment metrics.</p>
        </div>
      </header>

      <form className="filter-bar" onSubmit={handleApply} data-testid="dashboard-filters">
        <FormField label="Course" htmlFor="dashboard-filter-course">
          <select
            id="dashboard-filter-course"
            value={draft.course_id}
            onChange={(event) => setDraft({ ...draft, course_id: event.target.value })}
            data-testid="dashboard-filter-course"
          >
            <option value="">All courses</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>{course.title}</option>
            ))}
          </select>
        </FormField>

        <FormField label="Status" htmlFor="dashboard-filter-status">
          <select
            id="dashboard-filter-status"
            value={draft.status}
            onChange={(event) => setDraft({ ...draft, status: event.target.value })}
            data-testid="dashboard-filter-status"
          >
            <option value="">All statuses</option>
            {ENROLLMENT_STATUSES.map((status: EnrollmentStatus) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
        </FormField>

        <FormField label="From" htmlFor="dashboard-filter-date-from">
          <input
            id="dashboard-filter-date-from"
            type="date"
            value={draft.date_from}
            onChange={(event) => setDraft({ ...draft, date_from: event.target.value })}
            data-testid="dashboard-filter-date-from"
          />
        </FormField>

        <FormField label="To" htmlFor="dashboard-filter-date-to">
          <input
            id="dashboard-filter-date-to"
            type="date"
            value={draft.date_to}
            onChange={(event) => setDraft({ ...draft, date_to: event.target.value })}
            data-testid="dashboard-filter-date-to"
          />
        </FormField>

        <div className="filter-bar__actions">
          <button type="submit" className="button button--primary" data-testid="dashboard-apply">Apply</button>
          <button type="button" className="button button--secondary" onClick={handleReset} data-testid="dashboard-reset">Reset</button>
        </div>
      </form>

      {error ? <Alert variant="error">{error}</Alert> : null}

      {loading ? (
        <p className="muted" data-testid="dashboard-loading">Loading metrics...</p>
      ) : (
        <>
          <div className="metric-grid">
            {metricKeys.map((key) => (
              <article className="metric-card" key={key} data-testid={`metric-card-${key}`}>
                <span className="metric-card__label">{METRIC_LABELS[key]}</span>
                <span className="metric-card__value">{String(metrics[key])}</span>
              </article>
            ))}
            {metricKeys.length === 0 ? (
              <p className="muted">No metrics are available for the selected filters.</p>
            ) : null}
          </div>

          {breakdown.length > 0 ? (
            <section className="panel" aria-labelledby="breakdown-heading">
              <h2 id="breakdown-heading" className="panel__title">Breakdown</h2>
              <div className="bar-chart">
                {breakdown.map((row, index) => (
                  <div className="bar-row" key={`${row.label}-${index}`} data-testid={`bar-row-${index}`}>
                    <span className="bar-row__label">{row.label}</span>
                    <div className="bar-row__track">
                      <div className="bar-row__fill" style={{ width: `${(row.count / maxCount) * 100}%` }} />
                    </div>
                    <span className="bar-row__value">{row.count}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}
    </section>
  );
}
