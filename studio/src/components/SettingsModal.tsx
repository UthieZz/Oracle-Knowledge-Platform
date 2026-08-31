import React, { useState, useEffect, useMemo } from 'react';
import { X, Key, CheckCircle, AlertCircle, Database, RefreshCw, Shield, ExternalLink } from 'lucide-react';
import { CredentialService } from '../services/CredentialService';
import { FirestoreService, DashboardStats } from '../services/FirestoreService';
import {
  PROVIDERS,
  MODELS,
  ProviderId,
  listModelsForProvider,
} from '../services/ModelRegistry';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStatsRefresh?: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onStatsRefresh }) => {
  const [provider, setProvider] = useState<ProviderId>('gemini');
  const [modelId, setModelId] = useState('gemini-flash-latest');
  const [apiKey, setApiKey] = useState('');
  const [hasKey, setHasKey] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const modelsForProvider = useMemo(() => listModelsForProvider(provider), [provider]);

  useEffect(() => {
    if (isOpen) {
      const p = CredentialService.getSelectedProvider();
      const m = CredentialService.getSelectedModelId();
      setProvider(p);
      setModelId(m);
      const existing = CredentialService.getApiKey(p);
      setApiKey(existing || '');
      setHasKey(CredentialService.hasApiKey(p));
      setSavedSuccess(false);
      loadStats();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const existing = CredentialService.getApiKey(provider);
    setApiKey(existing || '');
    setHasKey(CredentialService.hasApiKey(provider));
    const stillValid = modelsForProvider.some((m) => m.id === modelId);
    if (!stillValid && modelsForProvider[0]) {
      setModelId(modelsForProvider[0].id);
    }
  }, [provider, isOpen, modelsForProvider, modelId]);

  const loadStats = async () => {
    try {
      const data = await FirestoreService.getDashboardStats();
      setStats(data);
    } catch (e) {
      console.error('Error loading stats in settings:', e);
    }
  };

  const handleSave = () => {
    CredentialService.setSelectedProvider(provider);
    CredentialService.setSelectedModelId(modelId);
    if (apiKey.trim()) {
      CredentialService.setApiKey(provider, apiKey.trim());
      setHasKey(true);
    }
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleClearKey = () => {
    CredentialService.clearApiKey(provider);
    setApiKey('');
    setHasKey(false);
  };

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await loadStats();
    if (onStatsRefresh) onStatsRefresh();
    setIsRefreshing(false);
  };

  if (!isOpen) return null;

  const providerDef = PROVIDERS[provider];

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-950 border border-gray-800 rounded-2xl max-w-xl w-full flex flex-col shadow-2xl overflow-hidden">
        <div className="p-6 border-b border-gray-800 flex justify-between items-center">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-600/10 rounded-lg text-blue-500">
              <Shield size={20} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Platform Settings & Credentials</h3>
              <p className="text-xs text-gray-500">Provider keys, model selection, and Firestore status.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-900 rounded-lg transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto max-h-[75vh]">
          {/* Provider + model */}
          <div className="bg-gray-900/60 p-5 rounded-xl border border-gray-800 space-y-4">
            <label className="text-sm font-semibold text-white">Grounded Ask model</label>
            <p className="text-xs text-gray-400 leading-relaxed">
              Default is Gemini Flash latest. Free-tier text also works via Groq and OpenRouter.
              Image/audio models (Nano Banana, Omni, Lyria/TTS) are listed for later media wiring — most are paid or limited on free.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] text-gray-500 uppercase tracking-wide">Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as ProviderId)}
                  className="mt-1 w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {(Object.keys(PROVIDERS) as ProviderId[]).map((id) => (
                    <option key={id} value={id}>
                      {PROVIDERS[id].label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[11px] text-gray-500 uppercase tracking-wide">Model</label>
                <select
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  className="mt-1 w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {modelsForProvider.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}{m.freeTier ? ' · free' : ' · paid/limited'}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="text-[11px] text-gray-500">{providerDef.freeTierNotes}</p>
          </div>

          {/* API key for selected provider */}
          <div className="bg-gray-900/60 p-5 rounded-xl border border-gray-800 space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-white flex items-center gap-2">
                <Key size={16} className="text-blue-500" /> {providerDef.label} API Key
              </label>
              {hasKey ? (
                <span className="text-[11px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <CheckCircle size={12} /> Configured
                </span>
              ) : (
                <span className="text-[11px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <AlertCircle size={12} /> Missing
                </span>
              )}
            </div>

            <p className="text-xs text-gray-400 leading-relaxed">
              Stored only in this browser for Closed Beta. Required for the selected provider.
            </p>

            <div className="space-y-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Paste API key…"
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3.5 py-2 text-sm text-white font-mono placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <div className="flex justify-between items-center pt-1">
                <a
                  href={providerDef.keyUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  Get API key <ExternalLink size={11} />
                </a>
                <div className="flex gap-2">
                  {hasKey && (
                    <button
                      onClick={handleClearKey}
                      className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded-lg transition-colors"
                    >
                      Clear
                    </button>
                  )}
                  <button
                    onClick={handleSave}
                    className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg transition-colors"
                  >
                    Save
                  </button>
                </div>
              </div>
              {savedSuccess && (
                <p className="text-xs text-emerald-400 flex items-center gap-1 mt-1">
                  <CheckCircle size={13} /> Settings saved
                </p>
              )}
            </div>
          </div>

          {/* Firestore */}
          <div className="bg-gray-900/60 p-5 rounded-xl border border-gray-800 space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-white flex items-center gap-2">
                <Database size={15} className="text-blue-500" /> Firestore Knowledge Store
              </span>
              <span className="text-emerald-400 font-mono text-[11px] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Connected
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-gray-400 pt-1">
              <div>Project: <span className="font-mono text-gray-200">oracle-knowledge-platform</span></div>
              <div>Plan: <span className="font-mono text-gray-200">Firebase Spark (No-Cost)</span></div>
              <div>Conversations: <span className="font-mono text-gray-200">{stats?.conversations ?? '—'}</span></div>
              <div>Knowledge Objects: <span className="font-mono text-gray-200">{stats?.knowledge_objects ?? '—'}</span></div>
            </div>
            <div className="pt-2 flex justify-end">
              <button
                onClick={handleManualRefresh}
                disabled={isRefreshing}
                className="flex items-center gap-1.5 px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-xs transition-colors"
              >
                <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} />
                Refresh State
              </button>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-gray-800 bg-gray-900/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
