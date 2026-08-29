/**
 * Oracle Knowledge Platform — Credential Management Service
 *
 * NOTE: For Closed Beta on Firebase Spark (client-side PWA), this module manages
 * user-provided credentials via browser localStorage with an optional build-time
 * env fallback (VITE_GEMINI_API_KEY).
 *
 * In a future stage with server-side proxy/backend, this interface can be seamlessly
 * replaced with session token or backend proxy calls without modifying consumers.
 */

const STORAGE_KEY = 'okp_gemini_api_key';

export const CredentialService = {
  /**
   * Retrieve the configured Gemini API key (localStorage first, then Vite env).
   */
  getGeminiApiKey(): string | null {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && stored.trim()) {
        return stored.trim();
      }
    } catch (e) {
      console.warn('[CREDENTIALS] Failed to read from localStorage:', e);
    }

    const envKey = (import.meta as any).env?.VITE_GEMINI_API_KEY;
    if (envKey && typeof envKey === 'string' && envKey.trim()) {
      return envKey.trim();
    }

    return null;
  },

  /**
   * Store user-supplied Gemini API key into localStorage.
   */
  setGeminiApiKey(key: string): void {
    try {
      if (key && key.trim()) {
        localStorage.setItem(STORAGE_KEY, key.trim());
      } else {
        this.clearGeminiApiKey();
      }
    } catch (e) {
      console.error('[CREDENTIALS] Failed to save to localStorage:', e);
    }
  },

  /**
   * Clear user-supplied Gemini API key from localStorage.
   */
  clearGeminiApiKey(): void {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      console.error('[CREDENTIALS] Failed to clear from localStorage:', e);
    }
  },

  /**
   * Check if a valid API key is currently configured.
   */
  hasGeminiApiKey(): boolean {
    return Boolean(this.getGeminiApiKey());
  },

  /**
   * Get a masked representation of the configured key for UI display (e.g. "AIzaSy...4Eedg").
   */
  getMaskedKey(): string | null {
    const key = this.getGeminiApiKey();
    if (!key) return null;
    if (key.length <= 8) return '••••••••';
    return `${key.slice(0, 6)}••••${key.slice(-4)}`;
  }
};
