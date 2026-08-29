import React, { useState, useEffect } from 'react';
import { Search, MessageSquare, FileText, ArrowRight, Zap, Tag, Paperclip, Loader2 } from 'lucide-react';
import { FirestoreService, SearchResult } from '../services/FirestoreService';

const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'knowledge' | 'conversation' | 'entity' | 'attachment'>('all');

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (query.trim()) {
        performSearch();
      } else {
        setResults([]);
      }
    }, 250);

    return () => clearTimeout(delayDebounceFn);
  }, [query]);

  const performSearch = async () => {
    setIsSearching(true);
    try {
      const data = await FirestoreService.search(query);
      setResults(data);
    } catch (err) {
      console.error("[SEARCH] Search error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const filtered = results.filter(r => activeFilter === 'all' || r.type === activeFilter);

  const getResultIcon = (type: string) => {
    switch (type) {
      case 'knowledge':
        return <Zap className="text-blue-500" size={16} />;
      case 'conversation':
        return <MessageSquare className="text-emerald-500" size={16} />;
      case 'entity':
        return <Tag className="text-amber-500" size={16} />;
      case 'attachment':
        return <Paperclip className="text-purple-500" size={16} />;
      default:
        return <FileText className="text-gray-500" size={16} />;
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
          <Search className="text-gray-500" size={22} />
        </div>
        <input
          type="text"
          autoFocus
          className="block w-full bg-gray-900 border border-gray-800 rounded-2xl py-4 pl-14 pr-12 text-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent transition-all shadow-xl"
          placeholder="Search knowledge objects, conversations, entities, attachments..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-5 flex items-center">
            <Loader2 className="animate-spin text-blue-500" size={20} />
          </div>
        )}
      </div>

      {/* Filter Tabs */}
      {results.length > 0 && (
        <div className="flex gap-2 border-b border-gray-800/80 pb-3 overflow-x-auto text-xs">
          <button
            onClick={() => setActiveFilter('all')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium ${activeFilter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-900 text-gray-400 hover:text-white'}`}
          >
            All ({results.length})
          </button>
          <button
            onClick={() => setActiveFilter('knowledge')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium ${activeFilter === 'knowledge' ? 'bg-blue-600 text-white' : 'bg-gray-900 text-gray-400 hover:text-white'}`}
          >
            Knowledge Objects ({results.filter(r => r.type === 'knowledge').length})
          </button>
          <button
            onClick={() => setActiveFilter('conversation')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium ${activeFilter === 'conversation' ? 'bg-blue-600 text-white' : 'bg-gray-900 text-gray-400 hover:text-white'}`}
          >
            Conversations ({results.filter(r => r.type === 'conversation').length})
          </button>
          <button
            onClick={() => setActiveFilter('entity')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium ${activeFilter === 'entity' ? 'bg-blue-600 text-white' : 'bg-gray-900 text-gray-400 hover:text-white'}`}
          >
            Entities ({results.filter(r => r.type === 'entity').length})
          </button>
          <button
            onClick={() => setActiveFilter('attachment')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium ${activeFilter === 'attachment' ? 'bg-blue-600 text-white' : 'bg-gray-900 text-gray-400 hover:text-white'}`}
          >
            Attachments ({results.filter(r => r.type === 'attachment').length})
          </button>
        </div>
      )}

      {/* Results List */}
      <div className="space-y-3">
        {filtered.length > 0 ? (
          <p className="text-gray-500 text-xs font-medium uppercase tracking-wider">
            Showing {filtered.length} matching record{filtered.length === 1 ? '' : 's'}
          </p>
        ) : query && !isSearching ? (
          <div className="text-center py-20 bg-gray-950/60 rounded-2xl border border-gray-800">
            <Search className="mx-auto text-gray-700 mb-3" size={40} />
            <p className="text-gray-400 font-medium">No results found for "{query}"</p>
            <p className="text-gray-600 text-xs mt-1">Try querying different keywords or check if data is imported.</p>
          </div>
        ) : !query ? (
          <div className="text-center py-20 bg-gray-950/60 rounded-2xl border border-gray-800">
            <Search className="mx-auto text-gray-800 mb-4" size={56} />
            <h3 className="text-lg font-bold text-white mb-1">Global Deterministic Search</h3>
            <p className="text-gray-500 text-sm max-w-md mx-auto">
              Search across all compiled canonical knowledge objects, indexed conversations, entities, and attachments.
            </p>
          </div>
        ) : null}

        {filtered.map((result, idx) => (
          <div 
            key={`${result.type}-${result.id}-${idx}`} 
            className="group bg-gray-900/60 hover:bg-gray-900 border border-gray-800 hover:border-gray-700 p-5 rounded-xl transition-all shadow-sm flex justify-between items-start"
          >
            <div className="flex-1 pr-4 min-w-0">
              <div className="flex items-center gap-2 mb-1.5">
                {getResultIcon(result.type)}
                <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                  {result.type}
                </span>
                <span className="text-gray-700">•</span>
                <span className="text-xs text-gray-500 font-semibold uppercase">
                  {result.source_platform || result.platform || 'General'}
                </span>
              </div>
              <h3 className="text-base font-bold text-white group-hover:text-blue-400 transition-colors">
                {result.title}
              </h3>
              <p className="text-gray-400 text-xs line-clamp-2 mt-1.5 leading-relaxed font-normal">
                {result.content || result.first_user_message || 'No preview snippet available'}
              </p>
              <div className="flex items-center gap-4 mt-3 text-[11px] text-gray-500">
                {result.type === 'conversation' && result.message_count !== undefined && (
                  <span className="flex items-center gap-1">
                    <FileText size={12} /> {result.message_count} messages
                  </span>
                )}
                {result.created_date && (
                  <span>Created: {new Date(result.created_date).toLocaleDateString()}</span>
                )}
                <span className="font-mono text-gray-600">ID: {result.id}</span>
              </div>
            </div>
            <ArrowRight className="text-gray-700 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all flex-shrink-0 mt-1" size={18} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default SearchPage;
