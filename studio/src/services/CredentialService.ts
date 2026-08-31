/**
 * OKP Credential + model preference storage (browser localStorage, Closed Beta).
 */

import {
  PROVIDERS,
  ProviderId,
  DEFAULT_MODEL_ID,
  getModelById,
} from './ModelRegistry';

const MODEL_STORAGE_KEY = 'okp_selected_model_id';
const PROVIDER_STORAGE_KEY = 'okp_selected_provider';

// Backward-compatible Gemini key alias
const LEGACY_GEMINI_KEY = 'okp_gemini_api_key';

export const CredentialService = {
  getApiKey(provider: ProviderId): string | null {
    const def = PROVIDERS[provider];
    if (!def) return null;
    try {
      const stored = localStorage.getItem(def.storageKey);
      if (stored && stored.trim()) return stored.trim();
    } catch (e) {
      console.warn('[CREDENTIALS] Failed to read localStorage:', e);
    }
    if (provider === 'gemini') {
      const envKey = (import.meta as any).env?.VITE_GEMINI_API_KEY;
      if (envKey && typeof envKey === 'string' && envKey.trim()) return envKey.trim();
    }
    return null;
  },

  setApiKey(provider: ProviderId, key: string): void {
    const def = PROVIDERS[provider];
    if (!def) return;
    try {
      if (key && key.trim()) {
        localStorage.setItem(def.storageKey, key.trim());
      } else {
        localStorage.removeItem(def.storageKey);
      }
    } catch (e) {
      console.error('[CREDENTIALS] Failed to save key:', e);
    }
  },

  clearApiKey(provider: ProviderId): void {
    const def = PROVIDERS[provider];
    if (!def) return;
    try {
      localStorage.removeItem(def.storageKey);
    } catch (e) {
      console.error('[CREDENTIALS] Failed to clear key:', e);
    }
  },

  hasApiKey(provider: ProviderId): boolean {
    return Boolean(this.getApiKey(provider));
  },

  /** @deprecated use getApiKey('gemini') */
  getGeminiApiKey(): string | null {
    return this.getApiKey('gemini');
  },

  /** @deprecated use setApiKey('gemini', key) */
  setGeminiApiKey(key: string): void {
    this.setApiKey('gemini', key);
  },

  /** @deprecated */
  clearGeminiApiKey(): void {
    this.clearApiKey('gemini');
  },

  /** @deprecated */
  hasGeminiApiKey(): boolean {
    return this.hasApiKey('gemini');
  },

  getMaskedKey(provider: ProviderId = 'gemini'): string | null {
    const key = this.getApiKey(provider);
    if (!key) return null;
    if (key.length <= 8) return '••••••••';
    return `${key.slice(0, 6)}••••${key.slice(-4)}`;
  },

  getSelectedProvider(): ProviderId {
    try {
      const p = localStorage.getItem(PROVIDER_STORAGE_KEY) as ProviderId | null;
      if (p && PROVIDERS[p]) return p;
    } catch {
      /* ignore */
    }
    return 'gemini';
  },

  setSelectedProvider(provider: ProviderId): void {
    try {
      localStorage.setItem(PROVIDER_STORAGE_KEY, provider);
    } catch (e) {
      console.error('[CREDENTIALS] Failed to save provider:', e);
    }
  },

  getSelectedModelId(): string {
    try {
      const id = localStorage.getItem(MODEL_STORAGE_KEY);
      if (id && getModelById(id)) return id;
    } catch {
      /* ignore */
    }
    return DEFAULT_MODEL_ID;
  },

  setSelectedModelId(modelId: string): void {
    try {
      localStorage.setItem(MODEL_STORAGE_KEY, modelId);
      const model = getModelById(modelId);
      if (model) {
        localStorage.setItem(PROVIDER_STORAGE_KEY, model.provider);
      }
    } catch (e) {
      console.error('[CREDENTIALS] Failed to save model:', e);
    }
  },
};
