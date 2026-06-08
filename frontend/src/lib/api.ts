const BASE = '/api';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API Error: ${res.status}${body ? ` - ${body.slice(0, 300)}` : ''}`);
  }
  return res.json();
}

// Runs
export const createRun = (data: {
  user_request: string;
  style_id?: string;
  target_platform?: string;
  mock?: boolean;
  config?: Record<string, any>;
}) => apiFetch<{ run_id: string; status: string }>('/runs', { method: 'POST', body: JSON.stringify(data) });

export const getRun = (id: string) => apiFetch<any>(`/runs/${id}`);

export const listRuns = (status?: string, limit?: number) =>
  apiFetch<{ runs: any[]; total: number }>(`/runs?${new URLSearchParams({ ...(status ? { status } : {}), ...(limit ? { limit: String(limit) } : {}) })}`);

export const interruptRun = (id: string) =>
  apiFetch<any>(`/runs/${id}/interrupt`, { method: 'POST' });

export const resumeRun = (id: string, statePatch?: Record<string, any>) =>
  apiFetch<any>(`/runs/${id}/resume`, { method: 'POST', body: JSON.stringify({ state_patch: statePatch || {} }) });

export const abortRun = (id: string) =>
  apiFetch<any>(`/runs/${id}/abort`, { method: 'POST' });

export const updateArticle = (runId: string, data: { draft_md?: string; final_md?: string }) =>
  apiFetch<any>(`/runs/${runId}/article`, { method: 'PUT', body: JSON.stringify(data) });

export const completeRun = (runId: string) =>
  apiFetch<any>(`/runs/${runId}/complete`, { method: 'POST' });

export const exportRun = (runId: string) =>
  fetch(`${BASE}/runs/${runId}/export`).then(r => r.text());

export const getRunEvents = (runId: string, afterId = 0) =>
  apiFetch<{ events: any[]; run_id: string }>(`/runs/${runId}/events?after_id=${afterId}`);

export const regenerateImage = (runId: string, index: number) =>
  apiFetch<{ run_id: string; index: number; image: any }>(`/runs/${runId}/regenerate-image`, {
    method: 'POST',
    body: JSON.stringify({ index }),
  });

// Topics
export const getCandidates = () =>
  apiFetch<{ candidates: any[]; fetched_at?: string; cached?: boolean; count?: number; refresh_id?: number; source_counts?: Record<string, number>; error?: string | null }>('/topics/candidates');

export const refreshCandidates = () =>
  apiFetch<{ refreshed: boolean; changed?: boolean; count: number; candidates: any[]; fetched_at?: string; refresh_id?: number; source_counts?: Record<string, number>; error?: string | null }>('/topics/refresh', { method: 'POST' });

// Styles
export const listStyles = () => apiFetch<{ styles: any[] }>('/styles');
export const createStyle = (data: { name: string; description?: string }) =>
  apiFetch<{ id: string; name: string }>('/styles', { method: 'POST', body: JSON.stringify(data) });
export const getStyle = (id: string) => apiFetch<any>(`/styles/${id}`);
export const analyzeStyle = (styleId: string, urls: string[]) =>
  apiFetch<any>(`/styles/${styleId}/analyze`, { method: 'POST', body: JSON.stringify({ urls }) });

// Stats
export const getDashboard = () => apiFetch<any>('/stats/dashboard');
export const getCostTrend = () => apiFetch<any>('/stats/cost');

// Settings
export const getSettings = () => apiFetch<any>('/settings');
export const updateSettings = (data: any) =>
  apiFetch<any>('/settings', { method: 'PUT', body: JSON.stringify(data) });
