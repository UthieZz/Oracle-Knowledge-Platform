import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, ExternalLink, Loader2 } from 'lucide-react';
import { ChatService, Citation } from '../services/ChatService';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

const ChatPage = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const data = await ChatService.ask(input);
      
      const assistantMsg: ChatMessage = { 
        role: 'assistant', 
        content: data.answer, 
        citations: data.citations 
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-200px)] flex flex-col bg-gray-950 rounded-2xl border border-gray-800 shadow-2xl overflow-hidden">
      {/* Chat History */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-50">
            <Bot size={64} className="mb-4 text-blue-500" />
            <h3 className="text-xl font-bold text-white">Oracle AI</h3>
            <p className="text-gray-400 max-w-sm">Ask anything about your compiled knowledge. I'll provide grounded answers with citations.</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                <Bot size={18} className="text-white" />
              </div>
            )}
            
            <div className={`max-w-[80%] rounded-2xl p-4 ${
              msg.role === 'user' 
                ? 'bg-blue-600 text-white rounded-tr-none' 
                : 'bg-gray-900 text-gray-200 border border-gray-800 rounded-tl-none'
            }`}>
              <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
              
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-800 space-y-2">
                  <p className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Sources</p>
                  <div className="flex flex-wrap gap-2">
                    {msg.citations.map((cite, cidx) => (
                      <div key={cidx} className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 px-2 py-1 rounded text-xs text-blue-400 cursor-pointer transition-colors">
                        <span className="font-bold">[{cite.source_index}]</span>
                        <span className="truncate max-w-[150px]">{cite.title}</span>
                        <ExternalLink size={10} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center flex-shrink-0">
                <User size={18} className="text-gray-400" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-4 justify-start">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
              <Bot size={18} className="text-white" />
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-none p-4 flex items-center gap-2">
              <Loader2 className="animate-spin text-blue-500" size={18} />
              <span className="text-gray-500 text-sm italic">Oracle is thinking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-gray-900/50 border-t border-gray-800">
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
            placeholder="Ask your second brain..."
            className="w-full bg-black border border-gray-800 rounded-xl py-3 pl-4 pr-12 text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[56px] max-h-32 resize-none"
            rows={1}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-2 p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-800 text-white rounded-lg transition-all"
          >
            <Send size={20} />
          </button>
        </div>
        <p className="text-[10px] text-center text-gray-600 mt-2 uppercase tracking-widest font-medium">Grounded in your indexed conversations</p>
      </div>
    </div>
  );
};

export default ChatPage;
