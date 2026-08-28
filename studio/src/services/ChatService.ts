import { FirestoreService } from "./FirestoreService";

const GEMINI_API_KEY = "AQ.Ab8RN6KUZQk4UHz7Jq3PSMUYx0PAzbetYTjhxRjJhamXbwwOfw"; // Injected from .env for beta demo

export interface Citation {
  id: string;
  title: string;
  platform: string;
  source_index: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}

export const ChatService = {
  async ask(query: string): Promise<ChatResponse> {
    console.log("[CHAT] Searching for context for:", query);
    
    // 1. Retrieval
    const contextResults = await FirestoreService.search(query);
    
    if (contextResults.length === 0) {
      return {
        answer: "I couldn't find any specific information in your compiled knowledge to answer that. Could you try rephrasing or importing more data?",
        citations: []
      };
    }

    // 2. Build Context
    const contextText = contextResults.map((res, idx) => {
      const sourceInfo = `[Source ${idx + 1}: ${res.title} (${res.source_platform || res.platform || 'General'})]`;
      const content = res.content || res.first_user_message || 'No content preview available';
      return `${sourceInfo}\n${content}`;
    }).join("\n\n");

    const citations: Citation[] = contextResults.map((res, idx) => ({
      id: res.id,
      title: res.title,
      platform: res.source_platform || res.platform || 'General',
      source_index: idx + 1
    }));

    // 3. Call Gemini
    const prompt = `
You are Oracle AI, the reasoning layer of the Oracle Knowledge Platform.
Your task is to answer the user's question based ONLY on the provided context.

CONTEXT:
${contextText}

USER QUESTION:
${query}

INSTRUCTIONS:
- Be concise and factual.
- Use the citations [Source X] in your answer when referencing information.
- If the context doesn't contain the answer, say you don't have enough evidence.
- Do not invent facts.
- Distinguish between facts, decisions, and hypotheses if indicated in the context.
`;

    try {
      // Using direct fetch to avoid adding new dependencies for now
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }]
        })
      });

      const data = await response.json();
      const answer = data.candidates?.[0]?.content?.parts?.[0]?.text || "I'm sorry, I couldn't generate an answer.";

      return {
        answer,
        citations
      };
    } catch (err) {
      console.error("Gemini API error:", err);
      return {
        answer: "I encountered an error while trying to generate a response. Please check your connectivity or API configuration.",
        citations: []
      };
    }
  }
};
