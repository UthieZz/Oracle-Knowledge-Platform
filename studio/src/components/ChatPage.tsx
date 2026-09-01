import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, Key, Trash2, ShieldCheck, AlertCircle, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { ChatService, Citation } from '../services/ChatService';
import { CredentialService } from '../services/CredentialService';
import { getModelById, DEFAULT_MODEL_ID } from '../services/ModelRegistry';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  needsKey?: boolean;
  modelUsed?: string;
}

interface ChatPageProps {
  onOpenSettings?: () => void;
}

function resolveModelLabel(): string {
  const id = CredentialService.getSelectedModelId();
  const model = getModelById(id) || getModelById(DEFAULT_MODEL_ID);
  return model?.label || id || 'Unknown model';
}

const ChatPage: React.FC<ChatPageProps> = ({ onOpenSettings }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasKey, setHasKey] = useState(ChatService.hasApiKey());
  const [modelLabel, setModelLabel] = useState(resolveModelLabel());
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const refreshCredentials = () => {
    setHasKey(ChatService.hasApiKey());
    setModelLabel(resolveModelLabel());
  };

  useEffect(() => {
    refreshCredentials();
    const onFocus = () => refreshCredentials();
    const onStorage = (e: StorageEvent) => {
      if (!e.key || e.key.startsWith('okp_')) refreshCredentials();
    };
    window.addEventListener('focus', onFocus);
    window.addEventListener('storage', onStorage);
    // Poll lightly so Settings Done in the same tab updates the header
    const interval = window.setInterval(refreshCredentials, 1500);
    return () => {
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('storage', onStorage);
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async (overrideText?: string) => {
    const textToSend = overrideText || input;
    if (!textToSend.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: 'user', content: textToSend };
    setMessages(prev => [...prev, userMsg]);
    if (!overrideText) setInput('');
    setIsLoading(true);
    refreshCredentials();

    try {
      const data = await ChatService.ask(textToSend);

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        needsKey: data.needsKey,
        modelUsed: data.modelUsed,
      };
      setMessages(prev => [...prev, assistantMsg]);
      refreshCredentials();
    } catch (err) {
      console.error('[CHAT] UI handler error:', err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'A temporary error occurred while processing your request. Please try again.',
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
  };

  const toggleCitation = (citeId: string) => {
    setExpandedCitation(prev => prev === citeId ? null : citeId);
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-210px)] flex flex-col bg-gray-950 rounded-2xl border border-gray-800 shadow-2xl overflow-hidden">
      <div className="px-6 py-3 bg-gray-900/60 border-b border-gray-800 flex justify-between items-center text-xs">
        <div className="flex items-center gap-2 text-gray-400">
          <ShieldCheck size={15} className="text-blue-400" />
          <span>Grounded Epistemic Reasoning</span>
          <span className="text-gray-700">•</span>
          <span className="text-gray-300 font-mono">{modelLabel}</span>
        </div>
        <div className="flex items-center gap-3">
          {!hasKey && onOpenSettings && (
            <button
              onClick={onOpenSettings}
              className="flex items-center gap-1 text-amber-400 hover:text-amber-300 font-semibold transition-colors"
            >
              <Key size={13} /> Configure API Key
            </button>
          )}
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
              title="Clear conversation"
            >
              <Trash2 size={13} /> Clear
            </button>
          )}
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-6">
            <div className="w-16 h-16 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center mb-4 text-blue-500">
              <Bot size={32} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Oracle Grounded Chat</h3>
            <p className="text-gray-400 text-sm max-w-md mb-8 leading-relaxed">
              Ask questions across your compiled knowledge base. Answers are strictly grounded in retrieved evidence with full provenance citations.
            </p>

            {!hasKey && (
              <div className="bg-amber-950/40 border border-amber-800/60 p-4 rounded-xl max-w-md w-full mb-6 text-left">
                <div className="flex items-start gap-3">
                  <AlertCircle size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-bold text-amber-300 uppercase tracking-wider">API Key Required</h4>
                    <p className="text-xs text-gray-400 mt-1">
                      Configure a provider API key in Settings for the selected model ({modelLabel}).
                    </p>
                    {onOpenSettings && (
                      <button
                        onClick={onOpenSettings}
                        className="mt-3 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      >
                        <Key size={13} /> Open Settings
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="w-full max-w-md space-y-2 text-left">
              <p className="text-[11px] uppercase font-bold text-gray-500 tracking-wider mb-2 flex items-center gap-1">
                <Sparkles size={12} className="text-blue-400" /> Suggested Inquiries
              </p>
              <button
                onClick={() => handleSend('What are the key discussions and decisions across my indexed conversations?')}
                className="w-full text-left p-3 rounded-xl bg-gray-900 hover:bg-gray-850 border border-gray-800 text-xs text-gray-300 hover:text-white transition-all"
              >
                "What are the key discussions and decisions across my indexed conversations?"
              </button>
              <button
                onClick={() => handleSend('Summarize the main topics from my Gemini and Grok imports.')}
                className="w-full text-left p-3 rounded-xl bg-gray-900 hover:bg-gray-850 border border-gray-800 text-xs text-gray-300 hover:text-white transition-all"
              >
                "Summarize the main topics from my Gemini and Grok imports."
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-blue-600/90 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot size={17} className="text-white" />
              </div>
            )}

            <div className={`max-w-[85%] rounded-2xl p-5 ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-tr-none shadow-md'
                : 'bg-gray-900 text-gray-200 border border-gray-800 rounded-tl-none shadow-sm'
            }`}>
              <div className="whitespace-pre-wrap leading-relaxed text-sm">{msg.content}</div>

              {msg.modelUsed && msg.role === 'assistant' && (
                <p className="mt-2 text-[10px] text-gray-500 font-mono">model: {msg.modelUsed}</p>
              )}

              {msg.needsKey && onOpenSettings && (
                <div className="mt-4 pt-3 border-t border-gray-800">
                  <button
                    onClick={onOpenSettings}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Key size={13} /> Configure API Key Now
                  </button>
                </div>
              )}

              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-5 pt-4 border-t border-gray-800/80 space-y-2">
                  <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">
                    Verified Evidence Sources ({msg.citations.length})
                  </p>
                  <div className="flex flex-col gap-2">
                    {msg.citations.map((cite) => {
                      const isExpanded = expandedCitation === cite.id;
                      return (
                        <div
                          key={cite.id}
                          className="bg-gray-950/80 border border-gray-800 rounded-lg p-2.5 text-xs transition-colors"
                        >
                          <div
                            onClick={() => toggleCitation(cite.id)}
                            className="flex items-center justify-between cursor-pointer text-blue-400 hover:text-blue-300"
                          >
                            <div className="flex items-center gap-2 truncate">
                              <span className="font-bold text-gray-400 bg-gray-900 px-1.5 py-0.5 rounded text-[11px]">
                                Source {cite.source_index}
                              </span>
                              <span className="font-semibold truncate">{cite.title}</span>
                              <span className="text-[10px] text-gray-500 font-mono uppercase bg-gray-900/60 px-1.5 py-0.2 rounded">
                                {cite.platform}
                              </span>
                            </div>
                            <div className="flex items-center gap-1 text-gray-500 pl-2">
                              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </div>
                          </div>

                          {isExpanded && cite.snippet && (
                            <div className="mt-2.5 pt-2.5 border-t border-gray-800/60 text-gray-400 text-xs font-mono leading-relaxed bg-gray-900/40 p-2 rounded">
                              <p className="text-[10px] text-gray-500 uppercase font-sans font-bold mb-1">Snippet Evidence:</p>
                              {cite.snippet}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                <User size={16} className="text-gray-400" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3.5 justify-start">
            <div className="w-8 h-8 rounded-full bg-blue-600/90 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot size={17} className="text-white" />
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-none p-4 flex items-center gap-2.5">
              <Loader2 className="animate-spin text-blue-500" size={17} />
              <span className="text-gray-400 text-xs italic">Retrieving evidence and compiling grounded answer via {modelLabel}...</span>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-gray-900/60 border-t border-gray-800">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a question grounded in your compiled knowledge..."
            className="w-full bg-black border border-gray-800 rounded-xl py-3.5 pl-4 pr-12 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[54px] max-h-32 resize-none"
            rows={1}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="absolute right-2.5 top-2.5 p-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg transition-all"
            title="Send query"
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-[10px] text-center text-gray-600 mt-2 uppercase tracking-wider font-semibold">
          Strictly constrained to retrieved evidence in Firestore • Preserves provenance
        </p>
      </div>
    </div>
  );
};

export default ChatPage;
