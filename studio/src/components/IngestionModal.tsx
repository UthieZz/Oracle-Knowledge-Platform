import React, { useState } from "react";

interface IngestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (manifest: any) => void;
}

export const IngestionModal: React.FC<IngestionModalProps> = ({ isOpen, onClose, onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/api/ingest", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      onUploadSuccess(result);
      onClose();
    } catch (err) {
      console.error("Failed to ingest file", err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-md w-full">
        <h2 className="text-xl font-bold text-white mb-4">Ingest Knowledge Source</h2>
        
        <input 
          type="file" 
          onChange={handleFileChange} 
          accept=".json,.pdf,.mp3,.png,.jpg"
          className="text-sm text-slate-400 mb-4 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-600 file:text-white"
        />

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-slate-400 hover:text-white text-sm">Cancel</button>
          <button 
            onClick={handleUpload} 
            disabled={!selectedFile || isProcessing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white rounded text-sm"
          >
            {isProcessing ? "Processing..." : "Start Import"}
          </button>
        </div>
      </div>
    </div>
  );
};
