import React, { useState, useEffect } from "react";
import { apiService, PipelineStatus } from "../services/apiService";

export const ImportPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [tenantId, setTenantId] = useState("tenant_default");
  const [siloId, setSiloId] = useState("silo_default");
  
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Polls backend status whenever an active job ID is set
  useEffect(() => {
    if (!activeJobId) return;

    const interval = setInterval(async () => {
      try {
        const status = await apiService.getPipelineStatus(activeJobId);
        setPipelineStatus(status);

        if (status.status === "completed" || status.status === "failed") {
          clearInterval(interval);
        }
      } catch (err: any) {
        setErrorMessage(err.message || "Failed to poll pipeline status");
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeJobId]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const handleStartIngestion = async () => {
    if (!file) return;

    setIsUploading(true);
    setErrorMessage(null);

    try {
      // Step 1: Upload file via REST API
      const ingestRes = await apiService.uploadFile(file, tenantId, siloId);
      
      // Step 2: Trigger OKC compilation pipeline
      const compileRes = await apiService.triggerCompilation(ingestRes.job_id, tenantId, siloId);
      setActiveJobId(compileRes.job_id);
    } catch (err: any) {
      setErrorMessage(err.message || "An error occurred during ingestion.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto text-slate-100">
      <h1 className="text-2xl font-bold mb-2">Local Knowledge Ingestion</h1>
      <p className="text-slate-400 mb-6">
        Ingest raw conversational exports, attachments, or PDFs directly into the local OKC engine.
      </p>

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Tenant ID</label>
            <input 
              type="text" 
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Silo ID</label>
            <input 
              type="text" 
              value={siloId}
              onChange={(e) => setSiloId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white"
            />
          </div>
        </div>

        <div className="border-2 border-dashed border-slate-700 rounded-lg p-8 text-center hover:border-slate-500 transition">
          <input 
            type="file" 
            id="file-input" 
            onChange={handleFileSelect} 
            className="hidden" 
          />
          <label htmlFor="file-input" className="cursor-pointer">
            <p className="text-sm font-medium text-slate-300">
              {file ? file.name : "Click or drag source file here to ingest"}
            </p>
            <p className="text-xs text-slate-500 mt-1">Supports JSON, PDF, PNG, JPG, MP3</p>
          </label>
        </div>

        {errorMessage && (
          <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded text-sm">
            {errorMessage}
          </div>
        )}

        <button
          onClick={handleStartIngestion}
          disabled={!file || isUploading || pipelineStatus?.status === "running"}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white font-medium rounded text-sm transition"
        >
          {isUploading ? "Uploading..." : pipelineStatus?.status === "running" ? "Processing Pipeline..." : "Process File"}
        </button>
      </div>

      {pipelineStatus && (
        <div className="mt-6 bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2">Compilation Pipeline Progress</h3>
          <p className="text-sm text-slate-400 mb-2">Status: <span className="capitalize text-white font-mono">{pipelineStatus.status}</span></p>
          
          <div className="w-full bg-slate-800 rounded-full h-2 mb-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300" 
              style={{ width: `${pipelineStatus.progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-400">{pipelineStatus.message}</p>
        </div>
      )}
    </div>
  );
};
