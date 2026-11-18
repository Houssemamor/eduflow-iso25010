import type { AuthResponse } from '../types';
import type { Paginated } from '../types';

export const API_BASE = '/api/v1';

// Token persistence. A single well-known key keeps auth state recoverable
// across reloads while remaining isolated from other apps on the same origin.
const TOKEN_KEY = 'eduflow_access_token';

// Event broadcast when the backend rejects a token, so AuthContext can clear
// user state even if the 401 happens inside a page-level request.
export const UNAUTHORIZED_EVENT = 'eduflow:unauthorized';

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE';
type QueryValue = string | number | boolean | undefined | null;
type QueryParams = Record<string, QueryValue>;

interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  params?: QueryParams;
  signal?: AbortSignal;
  skipAuth?: boolean;
}

/** Error carrying the backend-supplied message and HTTP status. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function buildUrl(path: string, params?: QueryParams): string {
  const url = `${API_BASE}${path}`;
  if (!params) return url;
  const query = new URLSearchParams();
  Object.keys(params).forEach((key) => {
    const value = params[key];
    if (value !== undefined && value !== null && value !== '') {
      query.append(key, String(value));
    }
  });
  const encoded = query.toString();
  return encoded ? `${url}?${encoded}` : url;
}

function extractDetail(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
    // FastAPI validation errors expose an array of { msg } objects.
    if (Array.isArray(detail)) {
      const messages = detail
        .map((entry) => (entry && typeof entry === 'object' && 'msg' in entry ? String(entry.msg) : ''))
        .filter((message) => message.length > 0);
      if (messages.length > 0) return messages.join(', ');
    }
  }
  return fallback;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, signal, skipAuth = false } = options;

  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = getToken();
  // Login must never replay a stale token; every other call is authenticated.
  if (!skipAuth && token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    // Aborts are intentional (component unmount) and must not surface as errors.
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'Network error. Please check your connection and try again.');
  }

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      // A non-JSON error body still produces a usable status-based message.
    }
    const detail = extractDetail(payload, `Request failed with status ${response.status}`);
    if (response.status === 401) {
      clearToken();
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }
    throw new ApiError(response.status, detail);
  }

  // DELETE endpoints commonly answer 204 with no body.
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get<T>(path: string, params?: QueryParams, signal?: AbortSignal): Promise<T> {
    return request<T>(path, { params, signal });
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'POST', body });
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'PATCH', body });
  },
  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' });
  },
  login(email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
      skipAuth: true,
    });
  },
};

// Some lookup endpoints return only an `items` property, so the envelope is
// intentionally loose here and every optional field gets a safe default.
interface LoosePaginated<T> {
  items?: T[];
  total?: number;
  skip?: number;
  limit?: number;
}

/** Normalizes endpoints that may return either a bare array or a paginated envelope. */
export function asPaginated<T>(data: T[] | LoosePaginated<T>, fallbackLimit = 20): Paginated<T> {
  if (!data) {
    return { items: [], total: 0, skip: 0, limit: fallbackLimit };
  }
  if (Array.isArray(data)) {
    return { items: data, total: data.length, skip: 0, limit: fallbackLimit };
  }
  return {
    items: Array.isArray(data.items) ? data.items : [],
    total: typeof data.total === 'number' ? data.total : (Array.isArray(data.items) ? data.items.length : 0),
    skip: typeof data.skip === 'number' ? data.skip : 0,
    limit: typeof data.limit === 'number' ? data.limit : fallbackLimit,
  };
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred.';
}
