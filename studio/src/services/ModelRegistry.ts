/**
 * OKP model registry — free-tier oriented catalog for Studio grounded Ask.
 * Media generation (image/audio) is marked as capability; wiring comes later.
 *
 * Notes (2026-08):
 * - Gemini 2.0 Flash family is shut down / replaced — do not hardcode it.
 * - Prefer gemini-2.5-flash, gemini-3.x-flash, or gemini-flash-latest aliases.
 * - True free image/audio generation is thinner than free text; Gemini image/
 *   TTS/Omni/Lyria and OpenRouter/Groq free text are the practical beta path.
 */

export type ModelCapability = 'text' | 'vision' | 'image_gen' | 'audio_in' | 'audio_out' | 'video';

export type ProviderId =
  | 'gemini'
  | 'groq'
  | 'openrouter'
  | 'deepseek'
  | 'xai'
  | 'openai';

export interface ModelDefinition {
  id: string;
  label: string;
  provider: ProviderId;
  /** API model string sent to the provider */
  apiModel: string;
  capabilities: ModelCapability[];
  freeTier: boolean;
  notes?: string;
}

export interface ProviderDefinition {
  id: ProviderId;
  label: string;
  /** Where the user gets a key */
  keyUrl: string;
  /** localStorage key for the API key */
  storageKey: string;
  /** OpenAI-compatible base URL when applicable */
  baseUrl?: string;
  freeTierNotes: string;
}

export const PROVIDERS: Record<ProviderId, ProviderDefinition> = {
  gemini: {
    id: 'gemini',
    label: 'Google Gemini',
    keyUrl: 'https://aistudio.google.com/app/apikey',
    storageKey: 'okp_gemini_api_key',
    freeTierNotes: 'Best free multimodal text path. Flash models rate-limited; image/TTS often paid or watermarked on free.',
  },
  groq: {
    id: 'groq',
    label: 'Groq',
    keyUrl: 'https://console.groq.com/keys',
    storageKey: 'okp_groq_api_key',
    baseUrl: 'https://api.groq.com/openai/v1',
    freeTierNotes: 'Strong free text + Whisper STT. No credit card. Fast.',
  },
  openrouter: {
    id: 'openrouter',
    label: 'OpenRouter',
    keyUrl: 'https://openrouter.ai/keys',
    storageKey: 'okp_openrouter_api_key',
    baseUrl: 'https://openrouter.ai/api/v1',
    freeTierNotes: 'One key, many :free models. ~20 RPM / 50 RPD on free unless topped up.',
  },
  deepseek: {
    id: 'deepseek',
    label: 'DeepSeek',
    keyUrl: 'https://platform.deepseek.com/api_keys',
    storageKey: 'okp_deepseek_api_key',
    baseUrl: 'https://api.deepseek.com/v1',
    freeTierNotes: 'Signup credits / cheap text. Not a permanent unlimited free tier.',
  },
  xai: {
    id: 'xai',
    label: 'xAI Grok',
    keyUrl: 'https://console.x.ai/',
    storageKey: 'okp_xai_api_key',
    baseUrl: 'https://api.x.ai/v1',
    freeTierNotes: 'Signup credit, not permanent free. Text-first for API.',
  },
  openai: {
    id: 'openai',
    label: 'OpenAI',
    keyUrl: 'https://platform.openai.com/api-keys',
    storageKey: 'okp_openai_api_key',
    baseUrl: 'https://api.openai.com/v1',
    freeTierNotes: 'No lasting free API tier for flagship models. Keep optional for paid keys.',
  },
};

export const MODELS: ModelDefinition[] = [
  // --- Gemini text (free-tier oriented) ---
  {
    id: 'gemini-flash-latest',
    label: 'Gemini Flash (latest alias)',
    provider: 'gemini',
    apiModel: 'gemini-flash-latest',
    capabilities: ['text', 'vision', 'audio_in'],
    freeTier: true,
    notes: 'Stable alias; tracks current Flash. Preferred default.',
  },
  {
    id: 'gemini-2.5-flash',
    label: 'Gemini 2.5 Flash',
    provider: 'gemini',
    apiModel: 'gemini-2.5-flash',
    capabilities: ['text', 'vision', 'audio_in'],
    freeTier: true,
    notes: 'Still listed; prefer 3.x Flash if available in your project.',
  },
  {
    id: 'gemini-3.5-flash',
    label: 'Gemini 3.5 Flash',
    provider: 'gemini',
    apiModel: 'gemini-3.5-flash',
    capabilities: ['text', 'vision', 'audio_in'],
    freeTier: true,
  },
  {
    id: 'gemini-3.6-flash',
    label: 'Gemini 3.6 Flash',
    provider: 'gemini',
    apiModel: 'gemini-3.6-flash',
    capabilities: ['text', 'vision', 'audio_in'],
    freeTier: true,
  },
  {
    id: 'gemini-3.7-flash',
    label: 'Gemini 3.7 Flash',
    provider: 'gemini',
    apiModel: 'gemini-3.7-flash',
    capabilities: ['text', 'vision', 'audio_in'],
    freeTier: true,
  },
  {
    id: 'gemini-2.5-flash-lite',
    label: 'Gemini 2.5 Flash-Lite',
    provider: 'gemini',
    apiModel: 'gemini-2.5-flash-lite',
    capabilities: ['text', 'vision'],
    freeTier: true,
    notes: 'Higher RPM free path for light grounded asks.',
  },
  // --- Gemini media-capable (often limited on free) ---
  {
    id: 'gemini-2.5-flash-image',
    label: 'Nano Banana (Gemini 2.5 Flash Image)',
    provider: 'gemini',
    apiModel: 'gemini-2.5-flash-image',
    capabilities: ['text', 'vision', 'image_gen'],
    freeTier: false,
    notes: 'Native image gen/edit. Free tier often unavailable or watermarked.',
  },
  {
    id: 'gemini-omni-1.1-flash',
    label: 'Gemini Omni 1.1 Flash',
    provider: 'gemini',
    apiModel: 'gemini-omni-1.1-flash',
    capabilities: ['text', 'vision', 'audio_in', 'audio_out', 'video'],
    freeTier: false,
    notes: 'Omni multimodal; paid path for full audio/video out.',
  },
  {
    id: 'gemini-3.1-flash-tts',
    label: 'Gemini 3.1 Flash TTS',
    provider: 'gemini',
    apiModel: 'gemini-3.1-flash-tts-preview',
    capabilities: ['text', 'audio_out'],
    freeTier: true,
    notes: 'TTS preview; free of charge listed for some TTS previews — verify in AI Studio.',
  },
  // --- Groq free text / STT ---
  {
    id: 'groq-llama-3.3-70b',
    label: 'Llama 3.3 70B (Groq)',
    provider: 'groq',
    apiModel: 'llama-3.3-70b-versatile',
    capabilities: ['text'],
    freeTier: true,
  },
  {
    id: 'groq-llama-3.1-8b',
    label: 'Llama 3.1 8B Instant (Groq)',
    provider: 'groq',
    apiModel: 'llama-3.1-8b-instant',
    capabilities: ['text'],
    freeTier: true,
  },
  {
    id: 'groq-gpt-oss-120b',
    label: 'GPT-OSS 120B (Groq)',
    provider: 'groq',
    apiModel: 'openai/gpt-oss-120b',
    capabilities: ['text'],
    freeTier: true,
  },
  // --- OpenRouter free aggregates ---
  {
    id: 'openrouter-free-router',
    label: 'OpenRouter Free Router',
    provider: 'openrouter',
    apiModel: 'openrouter/free',
    capabilities: ['text', 'vision'],
    freeTier: true,
    notes: 'Routes across free upstream models. Rate limits apply.',
  },
  {
    id: 'openrouter-deepseek-v3-free',
    label: 'DeepSeek Chat free (OpenRouter)',
    provider: 'openrouter',
    apiModel: 'deepseek/deepseek-chat-v3.1:free',
    capabilities: ['text'],
    freeTier: true,
  },
  // --- DeepSeek direct ---
  {
    id: 'deepseek-chat',
    label: 'DeepSeek Chat',
    provider: 'deepseek',
    apiModel: 'deepseek-chat',
    capabilities: ['text'],
    freeTier: true,
    notes: 'Uses account credits; cheap after trial.',
  },
  {
    id: 'deepseek-reasoner',
    label: 'DeepSeek Reasoner',
    provider: 'deepseek',
    apiModel: 'deepseek-reasoner',
    capabilities: ['text'],
    freeTier: true,
  },
  // --- xAI ---
  {
    id: 'xai-grok-fast',
    label: 'Grok Fast (xAI)',
    provider: 'xai',
    apiModel: 'grok-4.1-fast',
    capabilities: ['text'],
    freeTier: false,
    notes: 'Signup credit. Not permanent free.',
  },
  // --- OpenAI optional paid ---
  {
    id: 'openai-gpt-4o-mini',
    label: 'GPT-4o mini',
    provider: 'openai',
    apiModel: 'gpt-4o-mini',
    capabilities: ['text', 'vision'],
    freeTier: false,
  },
];

export const DEFAULT_MODEL_ID = 'gemini-flash-latest';

export function getModelById(id: string): ModelDefinition | undefined {
  return MODELS.find((m) => m.id === id);
}

export function listModelsForProvider(provider: ProviderId): ModelDefinition[] {
  return MODELS.filter((m) => m.provider === provider);
}

export function listFreeTextModels(): ModelDefinition[] {
  return MODELS.filter((m) => m.freeTier && m.capabilities.includes('text'));
}
