/**
 * API client for the Voice Assistant backend.
 * Sends X-API-Key header with every authenticated request.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function getApiKey(): string {
  return localStorage.getItem('va_api_key') || '';
}

export function setApiKey(key: string): void {
  localStorage.setItem('va_api_key', key);
}

export function getStoredApiKey(): string {
  return getApiKey();
}

export function clearApiKey(): void {
  localStorage.removeItem('va_api_key');
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const apiKey = getApiKey();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  // Don't set Content-Type for FormData (file uploads)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// --- Tenant API ---

export interface TenantSettings {
  system_prompt: string;
  tts_voice_id: string;
  assistant_name: string;
  max_concurrent_calls: number;
}

export interface Tenant {
  id: string;
  name: string;
  settings: TenantSettings;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenantWithApiKey {
  tenant: Tenant;
  api_key: string;
}

export const tenantApi = {
  create: (name: string, settings?: Partial<TenantSettings>) =>
    request<TenantWithApiKey>('/api/tenants/', {
      method: 'POST',
      body: JSON.stringify({ name, settings }),
    }),

  getMe: () => request<Tenant>('/api/tenants/me'),

  updateMe: (data: { name?: string; settings?: TenantSettings }) =>
    request<Tenant>('/api/tenants/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};

// --- Document API ---

export interface Document {
  id: string;
  tenant_id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  chunk_count: number;
  status: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  documents: Document[];
  total: number;
}

export const documentApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<Document>('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });
  },

  list: () => request<DocumentList>('/api/documents/'),

  get: (id: string) => request<Document>(`/api/documents/${id}`),

  delete: (id: string) =>
    request<void>(`/api/documents/${id}`, { method: 'DELETE' }),
};

// --- Call Logs API ---

export interface TranscriptEntry {
  role: string;
  text?: string;
  content?: string;
  timestamp?: string;
}

export interface CallLog {
  id: string;
  tenant_id: string;
  twilio_call_sid: string;
  caller_number: string | null;
  direction: string;
  duration_seconds: number | null;
  status: string;
  transcript: TranscriptEntry[];
  started_at: string;
  ended_at: string | null;
  created_at: string;
}

export interface CallLogList {
  call_logs: CallLog[];
  total: number;
}

// --- API Key API ---

export interface ApiKey {
  id: string;
  tenant_id: string;
  key_prefix: string;
  name: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated {
  id: string;
  key: string;
  key_prefix: string;
  name: string;
}

export const apiKeyApi = {
  list: () => request<ApiKey[]>('/api/tenants/me/api-keys'),

  create: (name: string = 'New API Key') =>
    request<ApiKeyCreated>('/api/tenants/me/api-keys', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  deactivate: (keyId: string) =>
    request<void>(`/api/tenants/me/api-keys/${keyId}`, { method: 'DELETE' }),
};
