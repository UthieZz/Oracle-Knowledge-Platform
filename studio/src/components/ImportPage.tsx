import React from 'react';
import { AlertCircle, FileText, Upload } from 'lucide-react';

const ImportPage = () => {
  return (
    <div className="max-w-4xl mx-auto p-8 bg-gray-900 rounded-xl border border-gray-800">
      <div className="flex items-center gap-4 mb-6 text-blue-400">
        <AlertCircle size={32} />
        <h2 className="text-3xl font-bold text-white">Import Knowledge</h2>
      </div>

      <label className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg cursor-pointer transition-colors w-fit font-bold mb-8">
        <Upload size={20} />
        Import AI Export Files
        <input
          type="file"
          multiple
          accept=".json,.zip"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              alert(`Selected ${e.target.files.length} file(s). Please move these to the 'uploads/' directory to continue with the local compilation workflow.`);
            }
          }}
        />
      </label>

      <p className="text-gray-300 mb-6">
        To maintain knowledge provenance and deterministic processing, compilation is performed locally using the canonical OKP Python compiler.
      </p>

      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 space-y-4">
        <h3 className="font-semibold text-white">Follow these steps:</h3>
        <ol className="list-decimal list-inside text-gray-300 space-y-2">
          <li>Place your source AI export files into the local <code>uploads/</code> directory.</li>
          <li>Run the canonical compiler: <code>python run.py</code></li>
          <li>The compiler will process the data, generate the KnowledgePackage, and update Firestore directly.</li>
          <li>Refresh Oracle Studio to view the compiled knowledge.</li>
        </ol>
      </div>

      <div className="mt-8 flex items-center gap-3 text-gray-500 text-sm">
        <FileText size={16} />
        <span>Browser-based ingestion is limited to local-file selection.</span>
      </div>
    </div>
  );
};

export default ImportPage;
