import React, { useState, useEffect } from 'react';
import { Search, MessageSquare, FileText, ArrowRight } from 'lucide-react';

const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (query) {
        performSearch();
      } else {
        setResults([]);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [query]);

  const performSearch = async () => {
    setIsSearching(true);
    try {
      const res = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error("Search error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="relative mb-10">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="text-gray-500" size={24} />
        </div>
        <input
          type="text"
          autoFocus
          className="block w-full bg-gray-900 border border-gray-700 rounded-2xl py-5 pl-14 pr-4 text-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all shadow-2xl"
          placeholder="Search your second brain..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {results.length > 0 ? (
          <p className="text-gray-500 text-sm mb-4">Found {results.length} results</p>
        ) : query && !isSearching ? (
          <p className="text-gray-500 text-center py-20">No results found for "{query}"</p>
        ) : !query ? (
          <div className="text-center py-20">
            <Search className="mx-auto text-gray-800 mb-4" size={64} />
            <p className="text-gray-500">Global search across all compiled knowledge and raw indexed conversations.</p>
          </div>
        ) : null}

        {results.map((result, idx) => (
          <div 
            key={idx} 
            className="group bg-gray-900/50 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 p-6 rounded-xl transition-all cursor-pointer flex justify-between items-center shadow-sm"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <MessageSquare className="text-blue-500" size={16} />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-widest">{result.source_platform || 'Conversation'}</span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors">{result.title}</h3>
              <p className="text-gray-400 text-sm line-clamp-2 mt-2">{result.first_user_message || 'No preview available'}</p>
              <div className="flex gap-4 mt-3">
                <span className="text-xs text-gray-600 flex items-center gap-1">
                   <FileText size={12} /> {result.message_count || 0} messages
                </span>
                <span className="text-xs text-gray-600">
                   {result.created_date || result.created || 'Unknown date'}
                </span>
              </div>
            </div>
            <ArrowRight className="text-gray-700 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" size={24} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default SearchPage;
