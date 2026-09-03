export type QueuedImport = {
  path: string;
  status?: string;
  type?: string;
};

export type UploadResult = {
  ok: boolean;
  filename?: string;
  path?: string;
  error?: string;
};

const ALLOWED = new Set(['.json', '.zip']);

export function isAllowedSourceFile(name: string): boolean {
  const lower = name.toLowerCase();
  return [...ALLOWED].some((ext) => lower.endsWith(ext));
}

export async function uploadSourceFile(file: File): Promise<UploadResult> {
  if (!isAllowedSourceFile(file.name)) {
    return { ok: false, error: `Rejected ${file.name}: only .json and .zip exports` };
  }

  const body = new FormData();
  body.append('file', file);

  try {
    const res = await fetch('/api/import/upload', {
      method: 'POST',
      body,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return { ok: false, error: data.error || `Upload failed (${res.status})` };
    }
    return {
      ok: true,
      filename: data.filename,
      path: data.path,
    };
  } catch (err) {
    return {
      ok: false,
      error:
        err instanceof Error
          ? `${err.message}. Is Flask running on :5000?`
          : 'Upload failed. Is Flask running on :5000?',
    };
  }
}

export async function fetchImportQueue(): Promise<QueuedImport[]> {
  try {
    const res = await fetch('/api/import/queue');
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}
