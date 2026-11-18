// Shared domain types. They mirror the backend API contract documented in the
// project brief; keeping them in one place prevents divergent shapes across screens.

export type Role = 'admin' | 'formateur' | 'apprenant';

export const ROLES: Role[] = ['admin', 'formateur', 'apprenant'];

export interface User {
  id: number;
  email: string;
  role: Role;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const COURSE_STATUSES = ['draft', 'published', 'archived'] as const;
export type CourseStatus = (typeof COURSE_STATUSES)[number];

export interface Tag {
  id: number;
  name: string;
}

export interface TagCreate {
  name: string;
}

export interface Course {
  id: number;
  title: string;
  description: string;
  capacity: number;
  status: string;
  tag_ids: number[];
  tags?: Tag[];
  owner_id?: number;
  created_at?: string;
}

export interface CourseCreate {
  title: string;
  description: string;
  capacity: number;
  status: CourseStatus;
  tag_ids: number[];
}

export type CourseUpdate = Partial<CourseCreate>;

export interface Session {
  id: number;
  course_id: number;
  starts_at: string;
  ends_at: string;
  room: string;
  capacity: number;
  course?: Course;
}

export interface SessionCreate {
  course_id: number;
  starts_at: string;
  ends_at: string;
  room: string;
  capacity: number;
}

export type SessionUpdate = Partial<SessionCreate>;

export const ENROLLMENT_STATUSES = ['pending', 'validated', 'completed', 'cancelled'] as const;
export type EnrollmentStatus = (typeof ENROLLMENT_STATUSES)[number];

export interface Enrollment {
  id: number;
  course_id: number;
  session_id: number;
  user_id: number;
  status: string;
  created_at?: string;
  user?: User;
  course?: Course;
  session?: Session;
}

export interface EnrollmentCreate {
  course_id: number;
  session_id: number;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name: string;
  role: Role;
}

export interface UserUpdate {
  email?: string;
  password?: string;
  full_name?: string;
  role?: Role;
}

// The dashboard payload is defined by the backend; optional fields plus an
// index signature let the UI render gracefully if extra metrics are returned.
export interface DashboardMetrics {
  total_courses?: number;
  total_enrollments?: number;
  total_users?: number;
  total_sessions?: number;
  active_courses?: number;
  pending_enrollments?: number;
  validated_enrollments?: number;
  completed_enrollments?: number;
  cancelled_enrollments?: number;
  occupancy_rate?: number;
  enrollments_by_status?: Array<{ status: string; count: number }>;
  enrollments_by_course?: Array<{ course_id?: number; title?: string; course?: string; count: number }>;
  courses_by_status?: Array<{ status: string; count: number }>;
  [key: string]: unknown;
}

export interface AuditEvent {
  id: number;
  actor_id: number;
  actor_email?: string;
  action: string;
  target_type?: string;
  target_id?: number | string;
  details?: string | Record<string, unknown>;
  created_at?: string;
  timestamp?: string;
  ip_address?: string;
  [key: string]: unknown;
}
