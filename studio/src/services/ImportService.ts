export interface ImportFile {
  path: string;
  status: 'Pending' | 'Importing' | 'Done' | 'Error';
  type: string;
}

export interface PipelineStatus {
  status: string;
  progress: number;
}

export const ImportService = {
  async getDashboardStats() {
    const res = await fetch('/api/dashboard');
    return res.json();
  },

  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/import/upload', {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  async getQueue(): Promise<ImportFile[]> {
    const res = await fetch('/api/import/queue');
    return res.json();
  },

  async compile() {
    const res = await fetch('/api/compile', {
      method: 'POST',
    });
    return res.json();
  },

  async getPipelineStatus(): Promise<PipelineStatus> {
    const res = await fetch('/api/pipeline/status');
    return res.json();
  }
};
