const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export interface PipelineStatus {
  job_id: string;
  status: "idle" | "running" | "completed" | "failed";
  progress: number;
  message: string;
}

export interface IngestResponse {
  job_id: string;
  file_path: string;
  tenant_id: string;
  silo_id: string;
  message: string;
}

export const apiService = {
  /**
   * Uploads a raw media or JSON export file to the backend ingest endpoint.
   */
  async uploadFile(file: File, tenantId: string = "default", siloId: string = "default"): Promise<IngestResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("tenant_id", tenantId);
    formData.append("silo_id", siloId);

    const response = await fetch(`${API_BASE_URL}/import/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `Upload failed with status ${response.status}`);
    }

    return response.json();
  },

  /**
   * Triggers the OKC compilation pipeline for an ingested package.
   */
  async triggerCompilation(jobId: string, tenantId: string, siloId: string): Promise<{ job_id: string; status: string }> {
    const response = await fetch(`${API_BASE_URL}/compile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: jobId,
        tenant_id: tenantId,
        silo_id: siloId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to initiate compilation: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Polls the status of an active compilation job.
   */
  async getPipelineStatus(jobId: string): Promise<PipelineStatus> {
    const response = await fetch(`${API_BASE_URL}/pipeline/status?job_id=${encodeURIComponent(jobId)}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch status: ${response.statusText}`);
    }

    return response.json();
  }
};
