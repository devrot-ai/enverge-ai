// API client for ForgeLab backend
const API_BASE = '/api/v1';

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getTemplates() {
  const data = await fetchApi<{ templates: string[] }>('/templates');
  return data.templates;
}

export async function getMutations() {
  const data = await fetchApi<{ mutations: Array<{ mutation_id: string; name: string; description: string }> }>('/mutations');
  return data.mutations;
}

export async function generateWorld(templateName: string, mutationId?: string | null) {
  return fetchApi<any>('/worlds/generate', {
    method: 'POST',
    body: JSON.stringify({ template_name: templateName, mutation_id: mutationId || null }),
  });
}

export async function getExperiments() {
  const data = await fetchApi<{ experiments: Array<{ id: string; name: string; description: string }> }>('/experiments');
  return data.experiments;
}

export async function getBenchmark() {
  return fetchApi<any>('/benchmark');
}

export async function getDocs() {
  const data = await fetchApi<{ endpoints: Array<{ method: string; path: string; description: string }> }>('/docs');
  return data.endpoints;
}

export async function checkHealth() {
  const res = await fetch('/health');
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
