/**
 * Shared API client for the CampaignIQ frontend.
 * Automatically attaches the JWT Bearer token from localStorage on every request.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiRequest<T>(
  path: string,
  options?: RequestInit & { noAuth?: boolean }
): Promise<T> {
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('campaigniq_token') : null;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  if (token && !options?.noAuth) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const { noAuth: _noAuth, ...fetchOptions } = options ?? {};

  const res = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err?.detail?.message || err?.detail || `HTTP ${res.status}`
    );
  }

  return res.json() as Promise<T>;
}
