import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, FileText, Upload } from 'lucide-react';
import {
  fetchImportQueue,
  isAllowedSourceFile,
  uploadSourceFile,
  type QueuedImport,
} from '../services/importApi';

type RowStatus = 'uploading' | 'queued' | 'error';

type Row = {
  name: string;
  status: RowStatus;
  detail?: string;
};

const ImportPage = () => {
  const [rows, setRows] = useState<Row[]>([]);
  const [queue, setQueue] = useState<QueuedImport[]>([]);
  const [busy, setBusy] = useState(false);

  const refreshQueue = useCallback(async () => {
    setQueue(await fetchImportQueue());
  }, []);

  useEffect(() => {
    void refreshQueue();
  }, [refreshQueue]);

  const onFiles = async (list: FileList | null) => {
    if (!list || list.length === 0) return;
    const files = Array.from(list);
    setBusy(true);
    setRows(files.map((f) => ({ name: f.name, status: 'uploading' as const })));

    for (const file of files) {
      if (!isAllowedSourceFile(file.name)) {
        setRows((prev) =>
          prev.map((r) =>
            r.name === file.name
              ? { ...r, status: 'error', detail: 'Only .json and .zip exports' }
              : r,
          ),
        );
        continue;
      }
      const result = await uploadSourceFile(file);
      setRows((prev) =>
        prev.map((r) =>
          r.name === file.name
            ? {
                ...r,
                status: result.ok ? 'queued' : 'error',
                detail: result.ok
                  ? `Saved to uploads/${result.filename}`
                  : result.error,
              }
            : r,
        ),
      );
    }

    await refreshQueue();
    setBusy(false);
  };

  return (
    <div className="max-w-4xl mx-auto p-8 bg-gray-900 rounded-xl border border-gray-800">
      <div className="flex items-center gap-4 mb-6 text-blue-400">
        <AlertCircle size={32} />
        <h2 className="text-3xl font-bold text-white">Import Knowledge</h2>
      </div>

      <label className={`flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg cursor-pointer transition-colors w-fit font-bold mb-8 ${
        busy ? 'opacity-60 pointer-events-none' : ''
      }`}>
        <Upload size={20} />
        {busy ? 'Uploading…' : 'Import AI Export Files'}
        <input
          type="file"
          multiple
          accept=".json,.zip"
          className="hidden"
          disabled={busy}
          onChange={(e) => {
            void onFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </label>

      <p className="text-gray-300 mb-6">
        The browser only delivers files into the local <code>uploads/</code> folder.
        Compilation stays on the Python compiler so provenance and dispatcher rules are preserved.
      </p>

      {rows.length > 0 && (
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700 mb-6 space-y-2">
          <h3 className="font-semibold text-white">This session</h3>
          {rows.map((r) => (
            <div key={r.name} className="text-sm text-gray-300">
              <span className="font-mono">{r.name}</span>{' '}
              <span
                className={
                  r.status === 'queued'
                    ? 'text-green-400'
                    : r.status === 'error'
                      ? 'text-red-400'
                      : 'text-yellow-400'
                }
              >
                {r.status}
              </span>
              {r.detail ? <span className="text-gray-500"> — {r.detail}</span> : null}
            </div>
          ))}
        </div>
      )}

      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 space-y-4">
        <h3 className="font-semibold text-white">Then compile locally</h3>
        <ol className="list-decimal list-inside text-gray-300 space-y-2">
          <li>Keep Flask running so Studio can reach <code>/api/import/upload</code>.</li>
          <li>After files show as queued, run the canonical compiler: <code>python run.py</code></li>
          <li>The compiler writes KnowledgePackage + Firestore. Refresh Studio to view objects.</li>
        </ol>
        {queue.length > 0 && (
          <p className="text-gray-400 text-sm">
            Server queue: {queue.length} file(s) known to ImportService this process.
          </p>
        )}
      </div>

      <div className="mt-8 flex items-center gap-3 text-gray-500 text-sm">
        <FileText size={16} />
        <span>No KnowledgePackage is mutated in the browser. Flask only saves files.</span>
      </div>
    </div>
  );
};

export default ImportPage;
