/**
 * Local SQLite API client for Studio when VITE_OKP_DATA_MODE=local.
 * Talks to okc/server/app.py on the configured base URL.
 */

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:5000/api";

const TENANT =
  ((import.meta as any).env?.VITE_OKP_TENANT_ID as string | undefined) || "default";
const SILO =
  ((import.meta as any).env?.VITE_OKP_SILO_ID as string | undefined) || "default";

export interface LocalDashboardStats {
  platforms: number;
  conversations: number;
  knowledge_objects: number;
  updated_at?: string | null;
}

export interface LocalKnowledgeObject {
  id: string;
  object_id?: string;
  title: string;
  content: string;
  source_platform: string;
  type?: string;
  tenant_id?: string;
  silo_id?: string;
  created_at?: string;
}

export interface LocalSearchResult {
  id: string;
  type: string;
  title: string;
  snippet: string;
  content?: string;
  source_platform?: string;
  created_at?: string;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(`Local API ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const LocalApiStore = {
  tenantId(): string {
    return TENANT;
  },
  siloId(): string {
    return SILO;
  },

  async getDashboardStats(): Promise<LocalDashboardStats> {
    const qs = new URLSearchParams({
      tenant_id: TENANT,
      silo_id: SILO,
    });
    return getJson<LocalDashboardStats>(`/dashboard?${qs.toString()}`);
  },

  async getKnowledgeObjects(limitCount = 100): Promise<LocalKnowledgeObject[]> {
    const qs = new URLSearchParams({
      tenant_id: TENANT,
      silo_id: SILO,
      limit: String(limitCount),
    });
    const data = await getJson<{ objects: LocalKnowledgeObject[]; count: number }>(
      `/knowledge-objects?${qs.toString()}`
    );
    return data.objects || [];
  },

  async search(searchTerm: string): Promise<LocalSearchResult[]> {
    const data = await getJson<{ results: LocalSearchResult[]; count: number }>(
      `/search`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: searchTerm,
          tenant_id: TENANT,
          silo_id: SILO,
          limit: 50,
        }),
      }
    );
    return data.results || [];
  },

  async health(): Promise<Record<string, unknown>> {
    return getJson<Record<string, unknown>>(`/health`);
  },
};
