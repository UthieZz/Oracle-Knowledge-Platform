import React, { useState, useEffect } from 'react';
import { Database, Search, Tag, Loader2, MessageSquare } from 'lucide-react';
import { FirestoreService, Entity } from '../services/FirestoreService';

const EntitiesBrowser = () => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    setIsLoading(true);
    FirestoreService.getEntities(200)
      .then(data => {
        setEntities(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load entities:", err);
        setIsLoading(false);
      });
  }, []);

  const types = Array.from(new Set(entities.map(e => e.type).filter(Boolean)));

  const filtered = entities.filter(entity => {
    const matchesQuery = !query || 
      (entity.value && entity.value.toLowerCase().includes(query.toLowerCase())) ||
      (entity.conversation_id && entity.conversation_id.toLowerCase().includes(query.toLowerCase()));
    const matchesType = typeFilter === 'all' || entity.type === typeFilter;
    return matchesQuery && matchesType;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="p-6 bg-gray-950 rounded-2xl border border-gray-800">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Tag className="text-blue-500" /> Canonical Entities
          </h2>
          <p className="text-gray-500 text-sm mt-1">Extracted named concepts, tools, and topics across indexed knowledge.</p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {types.length > 0 && (
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
              className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All Types ({entities.length})</option>
              {types.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          )}

          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
            <input 
              type="text" 
              placeholder="Filter entities..." 
              className="w-full bg-gray-900 border border-gray-800 rounded-lg py-2 pl-9 pr-4 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setPage(1); }}
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="animate-spin text-blue-500" size={32} />
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wider">
                  <th className="p-3">Entity Value</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Linked Conversation ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {paginated.map((item, idx) => (
                  <tr key={item.id || idx} className="hover:bg-gray-900/60 transition-colors">
                    <td className="p-3 font-semibold text-white">
                      <span className="bg-gray-800/80 px-2.5 py-1 rounded text-blue-400 border border-gray-700/50">
                        {item.value}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="text-xs uppercase tracking-wider font-semibold text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
                        {item.type || 'Entity'}
                      </span>
                    </td>
                    <td className="p-3 text-sm text-gray-500 font-mono">
                      {item.conversation_id ? (
                        <span className="flex items-center gap-1.5 truncate max-w-xs" title={item.conversation_id}>
                          <MessageSquare size={13} className="text-gray-600 flex-shrink-0" />
                          <span className="truncate">{item.conversation_id}</span>
                        </span>
                      ) : (
                        <span className="text-gray-600">Global</span>
                      )}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={3} className="p-12 text-center text-gray-600">
                      <Database className="mx-auto mb-3 opacity-30" size={36} />
                      No entities matching your filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {filtered.length > pageSize && (
            <div className="mt-6 flex justify-between items-center text-sm text-gray-400">
              <span>Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filtered.length)} of {filtered.length} entities</span>
              <div className="flex gap-2">
                <button 
                  onClick={() => setPage(p => Math.max(1, p - 1))} 
                  disabled={page === 1}
                  className="bg-gray-900 hover:bg-gray-800 disabled:opacity-40 px-3 py-1.5 rounded-lg border border-gray-800 text-white transition-colors"
                >
                  Previous
                </button>
                <span className="px-3 py-1.5 bg-gray-950 border border-gray-800 rounded-lg">Page {page} of {totalPages}</span>
                <button 
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))} 
                  disabled={page === totalPages}
                  className="bg-gray-900 hover:bg-gray-800 disabled:opacity-40 px-3 py-1.5 rounded-lg border border-gray-800 text-white transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default EntitiesBrowser;
