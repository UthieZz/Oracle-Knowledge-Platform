import React, { useState, useEffect } from 'react';
import { Upload, Play, CheckCircle, Loader2, FileText, AlertCircle } from 'lucide-react';
import { ImportService, ImportFile, PipelineStatus } from '../services/ImportService';

const ImportPage = () => {
  const [files, setFiles] = useState<ImportFile[]>([]);
  const [status, setStatus] = useState<PipelineStatus>({ status: 'Idle', progress: 0 });
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    refreshQueue();
    const interval = setInterval(async () => {
      const s = await ImportService.getPipelineStatus();
      setStatus(s);
      if (s.status === 'Running') {
        refreshQueue();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const refreshQueue = async () => {
    const q = await ImportService.getQueue();
    setFiles(q);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    setIsUploading(true);
    for (let i = 0; i < e.target.files.length; i++) {
      await ImportService.uploadFile(e.target.files[i]);
    }
    await refreshQueue();
    setIsUploading(false);
  };

  const handleCompile = async () => {
    setStatus({ status: 'Running', progress: 0 });
    await ImportService.compile();
    await refreshQueue();
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-3xl font-bold">Import Knowledge</h2>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg cursor-pointer transition-colors">
            <Upload size={20} />
            Choose Files
            <input type="file" multiple className="hidden" onChange={handleFileUpload} />
          </label>
          <button
            onClick={handleCompile}
            disabled={files.length === 0 || status.status === 'Running'}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            {status.status === 'Running' ? <Loader2 className="animate-spin" size={20} /> : <Play size={20} />}
            Compile
          </button>
        </div>
      </div>

      {status.status === 'Running' && (
        <div className="bg-blue-900/30 border border-blue-500/50 p-6 rounded-lg mb-8 animate-pulse">
          <h3 className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
            <Loader2 className="animate-spin" size={18} />
            Pipeline Executing...
          </h3>
          <div className="w-full bg-gray-800 rounded-full h-2.5">
            <div className="bg-blue-500 h-2.5 rounded-full w-1/2"></div>
          </div>
          <p className="text-sm text-gray-400 mt-2">Running Import Pass, Attachment Pass, and Analysis...</p>
        </div>
      )}

      <div className="bg-gray-900 rounded-xl overflow-hidden border border-gray-800">
        <table className="w-full text-left">
          <thead className="bg-gray-800/50 text-gray-400 text-sm uppercase">
            <tr>
              <th className="px-6 py-4">File</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Platform</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {files.length === 0 && !isUploading && (
              <tr>
                <td colSpan={3} className="px-6 py-10 text-center text-gray-500">
                  No files queued for import.
                </td>
              </tr>
            )}
            {isUploading && (
              <tr>
                <td colSpan={3} className="px-6 py-4 text-center text-blue-400 flex items-center justify-center gap-2">
                  <Loader2 className="animate-spin" size={18} /> Uploading...
                </td>
              </tr>
            )}
            {files.map((file, idx) => (
              <tr key={idx} className="hover:bg-gray-800/30 transition-colors">
                <td className="px-6 py-4 flex items-center gap-3">
                  <FileText className="text-gray-400" size={18} />
                  <span className="font-medium">{file.path.split('/').pop()}</span>
                </td>
                <td className="px-6 py-4">
                  {file.status === 'Done' ? (
                    <span className="flex items-center gap-1.5 text-green-500 text-sm font-medium">
                      <CheckCircle size={14} /> Success
                    </span>
                  ) : file.status === 'Error' ? (
                    <span className="flex items-center gap-1.5 text-red-500 text-sm font-medium">
                      <AlertCircle size={14} /> Error
                    </span>
                  ) : file.status === 'Importing' ? (
                    <span className="flex items-center gap-1.5 text-blue-400 text-sm font-medium">
                      <Loader2 className="animate-spin" size={14} /> Importing
                    </span>
                  ) : (
                    <span className="text-gray-400 text-sm">Pending</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded border border-gray-700">
                    {file.type || 'Auto-detect'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ImportPage;
