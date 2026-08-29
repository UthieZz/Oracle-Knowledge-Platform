import { FirestoreService, SearchResult } from "./FirestoreService";
import { CredentialService } from "./CredentialService";

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
}

export const ChatService = {
  /**
   * Check if Gemini API key is configured.
   */
  hasApiKey(): boolean {
    return CredentialService.hasGeminiApiKey();
  },

  /**
   * Execute evidence retrieval, context building, and grounded reasoning via Gemini.
   */
  async ask(query: string): Promise<ChatResponse> {
    const trimmedQuery = (query || '').trim();
    if (!trimmedQuery) {
      return {
        answer: "Please enter a question about your compiled knowledge.",
        citations: []
      };
    }

    // 1. Verify Credential
    const apiKey = CredentialService.getGeminiApiKey();
    if (!apiKey) {
      return {
        answer: "Gemini API key is not configured. Please open Settings (or click the button below) to enter your Google AI Studio API key to enable grounded reasoning.",
        citations: [],
        needsKey: true
      };
    }

    console.log("[CHAT] Grounded retrieval for query:", trimmedQuery);

    // 2. Evidence Retrieval
    let contextResults: SearchResult[] = [];
    try {
      contextResults = await FirestoreService.search(trimmedQuery);
    } catch (err) {
      console.error("[CHAT] Retrieval error:", err);
      return {
        answer: "Failed to query the compiled knowledge base in Firestore. Please check your connection.",
        citations: [],
        hasError: true
      };
    }

    // 3. Handle Empty Retrieval Case
    if (contextResults.length === 0) {
      return {
        answer: "I do not have sufficient evidence in the compiled knowledge to answer this question. No related knowledge objects or conversations were found for your query.",
        citations: []
      };
    }

    // Bounded context: Take top 6 most relevant records
    const topResults = contextResults.slice(0, 6);

    // 4. Construct Bounded Evidence Context
    const contextText = topResults.map((res, idx) => {
      const sourceNum = idx + 1;
      const platform = res.source_platform || res.platform || 'General';
      const body = res.content || res.first_user_message || 'No preview text';
      // Truncate individual items to keep context bounded
      const boundedBody = body.length > 1500 ? `${body.substring(0, 1500)}... [truncated]` : body;
      return `[Source ${sourceNum}: "${res.title}" (${platform}) - ID: ${res.id}]\n${boundedBody}`;
    }).join("\n\n---\n\n");

    const citations: Citation[] = topResults.map((res, idx) => {
      const body = res.content || res.first_user_message || '';
      return {
        id: res.id,
        title: res.title,
        platform: res.source_platform || res.platform || 'General',
        source_index: idx + 1,
        snippet: body.length > 180 ? `${body.substring(0, 180)}...` : body
      };
    });

    // 5. Strict Grounding Prompt
    const prompt = `You are Oracle AI, the evidence-grounded reasoning layer of the Oracle Knowledge Platform (OKP).

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

    // 6. Call Gemini
    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
            generationConfig: {
              temperature: 0.1, // Low temperature for factual precision
              topP: 0.8,
              maxOutputTokens: 1024
            }
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const status = response.status;
        const errorMsg = errorData?.error?.message || response.statusText;
        console.error(`[CHAT] Gemini API returned status ${status}:`, errorMsg);

        if (status === 400 || status === 403) {
          return {
            answer: "Gemini API key is invalid or unauthorized. Please update your API key in Settings.",
            citations: [],
            needsKey: true,
            hasError: true
          };
        }
        if (status === 429) {
          return {
            answer: "Gemini API quota exceeded. Please wait a moment before asking again.",
            citations: [],
            hasError: true
          };
        }
        return {
          answer: `Gemini API request failed (${status}): ${errorMsg}. Please check your configuration.`,
          citations: [],
          hasError: true
        };
      }

      const data = await response.json();
      const rawAnswer = data.candidates?.[0]?.content?.parts?.[0]?.text;

      if (!rawAnswer) {
        return {
          answer: "I was unable to generate a response from the available evidence.",
          citations
        };
      }

      return {
        answer: rawAnswer,
        citations
      };
    } catch (err: any) {
      console.error("[CHAT] Network or runtime error calling Gemini:", err);
      return {
        answer: "A network error occurred while communicating with Gemini. Please verify your internet connection.",
        citations: [],
        hasError: true
      };
    }
  }
};
