import { FirestoreService, SearchResult } from "./FirestoreService";
import { CredentialService } from "./CredentialService";
import {
  getModelById,
  PROVIDERS,
  DEFAULT_MODEL_ID,
  ModelDefinition,
} from "./ModelRegistry";

export interface Citation {
  id: string;
  title: string;
  platform: string;
  source_index: number;
  snippet?: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  hasError?: boolean;
  needsKey?: boolean;
  modelUsed?: string;
}

function buildPrompt(contextText: string, trimmedQuery: string): string {
  return `You are Oracle AI, the evidence-grounded reasoning layer of the Oracle Knowledge Platform (OKP).

EVIDENCE SOURCES FROM COMPILED KNOWLEDGE:
${contextText}

USER QUESTION:
${trimmedQuery}

STRICT GROUNDING INSTRUCTIONS:
1. Answer the question using ONLY the facts directly stated in the EVIDENCE SOURCES above.
2. If the evidence does not contain sufficient facts to answer the question, state:
   "I do not have sufficient evidence in the compiled knowledge to answer this question."
3. When making statements, include inline citations such as [Source 1], [Source 2] matching the source numbers provided.
4. Do NOT fabricate, extrapolate, or assume facts not present in the sources.
5. Distinguish clearly between established facts, decisions, hypotheses, and proposals if indicated in the sources.
6. Keep the response direct, structured, and concise.`;
}

async function callGemini(apiKey: string, model: ModelDefinition, prompt: string): Promise<string> {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model.apiModel}:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.1,
          topP: 0.8,
          maxOutputTokens: 1024,
        },
      }),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const status = response.status;
    const errorMsg = (errorData as any)?.error?.message || response.statusText;
    const err = new Error(`Gemini ${status}: ${errorMsg}`);
    (err as any).status = status;
    throw err;
  }

  const data = await response.json();
  const rawAnswer = data.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!rawAnswer) throw new Error('Empty model response');
  return rawAnswer;
}

async function callOpenAICompatible(
  apiKey: string,
  model: ModelDefinition,
  prompt: string
): Promise<string> {
  const provider = PROVIDERS[model.provider];
  const baseUrl = provider.baseUrl;
  if (!baseUrl) throw new Error(`Provider ${model.provider} has no OpenAI-compatible base URL`);

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
      ...(model.provider === 'openrouter'
        ? {
            'HTTP-Referer': typeof window !== 'undefined' ? window.location.origin : 'https://okp.local',
            'X-Title': 'Oracle Knowledge Platform',
          }
        : {}),
    },
    body: JSON.stringify({
      model: model.apiModel,
      temperature: 0.1,
      max_tokens: 1024,
      messages: [
        {
          role: 'system',
          content:
            'You are Oracle AI. Answer only from the provided evidence. Cite [Source N]. If evidence is insufficient, say so explicitly.',
        },
        { role: 'user', content: prompt },
      ],
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const status = response.status;
    const errorMsg =
      (errorData as any)?.error?.message ||
      (errorData as any)?.message ||
      response.statusText;
    const err = new Error(`${model.provider} ${status}: ${errorMsg}`);
    (err as any).status = status;
    throw err;
  }

  const data = await response.json();
  const rawAnswer = data.choices?.[0]?.message?.content;
  if (!rawAnswer) throw new Error('Empty model response');
  return rawAnswer;
}

export const ChatService = {
  hasApiKey(): boolean {
    const modelId = CredentialService.getSelectedModelId();
    const model = getModelById(modelId) || getModelById(DEFAULT_MODEL_ID)!;
    return CredentialService.hasApiKey(model.provider);
  },

  async ask(query: string): Promise<ChatResponse> {
    const trimmedQuery = (query || '').trim();
    if (!trimmedQuery) {
      return {
        answer: 'Please enter a question about your compiled knowledge.',
        citations: [],
      };
    }

    const modelId = CredentialService.getSelectedModelId();
    const model = getModelById(modelId) || getModelById(DEFAULT_MODEL_ID)!;
    const apiKey = CredentialService.getApiKey(model.provider);

    if (!apiKey) {
      return {
        answer: `${PROVIDERS[model.provider].label} API key is not configured for model "${model.label}". Open Settings to add a key or pick another model.`,
        citations: [],
        needsKey: true,
      };
    }

    console.log('[CHAT] Grounded retrieval for query:', trimmedQuery, 'model:', model.id);

    let contextResults: SearchResult[] = [];
    try {
      contextResults = await FirestoreService.search(trimmedQuery);
    } catch (err) {
      console.error('[CHAT] Retrieval error:', err);
      return {
        answer: 'Failed to query the compiled knowledge base in Firestore. Please check your connection.',
        citations: [],
        hasError: true,
      };
    }

    if (contextResults.length === 0) {
      return {
        answer:
          'I do not have sufficient evidence in the compiled knowledge to answer this question. No related knowledge objects or conversations were found for your query.',
        citations: [],
        modelUsed: model.id,
      };
    }

    const topResults = contextResults.slice(0, 6);

    const contextText = topResults
      .map((res, idx) => {
        const sourceNum = idx + 1;
        const platform = res.source_platform || res.platform || 'General';
        const body = res.content || res.first_user_message || 'No preview text';
        const boundedBody =
          body.length > 1500 ? `${body.substring(0, 1500)}... [truncated]` : body;
        return `[Source ${sourceNum}: "${res.title}" (${platform}) - ID: ${res.id}]\n${boundedBody}`;
      })
      .join('\n\n---\n\n');

    const citations: Citation[] = topResults.map((res, idx) => {
      const body = res.content || res.first_user_message || '';
      return {
        id: res.id,
        title: res.title,
        platform: res.source_platform || res.platform || 'General',
        source_index: idx + 1,
        snippet: body.length > 180 ? `${body.substring(0, 180)}...` : body,
      };
    });

    const prompt = buildPrompt(contextText, trimmedQuery);

    try {
      let rawAnswer: string;
      if (model.provider === 'gemini') {
        rawAnswer = await callGemini(apiKey, model, prompt);
      } else {
        rawAnswer = await callOpenAICompatible(apiKey, model, prompt);
      }

      return {
        answer: rawAnswer,
        citations,
        modelUsed: model.id,
      };
    } catch (err: any) {
      console.error('[CHAT] Model call error:', err);
      const status = err?.status;
      if (status === 400 || status === 401 || status === 403) {
        return {
          answer: `API key for ${PROVIDERS[model.provider].label} is invalid or unauthorized, or the model id is unavailable. Update Settings.`,
          citations: [],
          needsKey: true,
          hasError: true,
          modelUsed: model.id,
        };
      }
      if (status === 429) {
        return {
          answer: 'Provider quota / rate limit exceeded. Wait or switch model in Settings.',
          citations: [],
          hasError: true,
          modelUsed: model.id,
        };
      }
      return {
        answer: `Model request failed: ${err?.message || 'unknown error'}. Try another free-tier model in Settings.`,
        citations: [],
        hasError: true,
        modelUsed: model.id,
      };
    }
  },
};
