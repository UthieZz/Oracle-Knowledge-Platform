import React, { useState, useEffect } from 'react';
import { BookOpen, Search, X, Loader2, FileText, Layers } from 'lucide-react';
import { FirestoreService, KnowledgeObject } from '../services/FirestoreService';

const KnowledgeObjectsBrowser = () => {
  const [data, setData] = useState<KnowledgeObject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedKO, setSelectedKO] = useState<KnowledgeObject | null>(null);
  const [query, setQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  useEffect(() => {
    setIsLoading(true);
    FirestoreService.getKnowledgeObjects(200)
      .then(res => {
        setData(res);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load knowledge objects:", err);
        setIsLoading(false);
      });
  }, []);

  const platforms = Array.from(new Set(data.map(d => d.source_platform).filter(Boolean)));

  const filtered = data.filter(item => {
    const matchesQuery = !query || 
      (item.title && item.title.toLowerCase().includes(query.toLowerCase())) ||
      (item.content && item.content.toLowerCase().includes(query.toLowerCase()));
    const matchesPlatform = platformFilter === 'all' || item.source_platform === platformFilter;
    return matchesQuery && matchesPlatform;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="p-6 bg-gray-950 rounded-2xl border border-gray-800">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <BookOpen className="text-blue-500" /> Knowledge Objects
          </h2>
          <p className="text-gray-500 text-sm mt-1">Compiled canonical knowledge representations with provenance tracking.</p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {platforms.length > 0 && (
            <select
              value={platformFilter}
              onChange={(e) => { setPlatformFilter(e.target.value); setPage(1); }}
              className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All Sources ({data.length})</option>
              {platforms.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          )}

          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
            <input 
              type="text" 
              placeholder="Search objects..." 
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
                  <th className="p-3">Title</th>
                  <th className="p-3">Platform</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Created</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {paginated.map((item) => (
                  <tr 
                    key={item.id} 
                    onClick={() => setSelectedKO(item)}
                    className="border-b border-gray-800 hover:bg-gray-900/60 transition-colors cursor-pointer group"
                  >
                    <td className="p-3 font-semibold text-white group-hover:text-blue-400 max-w-md truncate">
                      {item.title}
                    </td>
                    <td className="p-3">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-300 uppercase">
                        {item.source_platform}
                      </span>
                    </td>
                    <td className="p-3 text-xs text-gray-500 uppercase">{item.type || 'Object'}</td>
                    <td className="p-3 text-xs text-gray-500">{item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}</td>
                    <td className="p-3 text-right">
                      <span className="text-xs text-blue-500 group-hover:underline">View Details</span>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-gray-600">
                      <BookOpen className="mx-auto mb-3 opacity-30" size={36} />
                      No knowledge objects found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {filtered.length > pageSize && (
            <div className="mt-6 flex justify-between items-center text-sm text-gray-400">
              <span>Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filtered.length)} of {filtered.length} objects</span>
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

      {/* Detail Modal */}
      {selectedKO && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-6 border-b border-gray-800 flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-600/20 text-blue-400 border border-blue-500/30">
                    {selectedKO.source_platform}
                  </span>
                  <span className="text-xs text-gray-500 font-mono">ID: {selectedKO.id}</span>
                </div>
                <h3 className="text-xl font-bold text-white">{selectedKO.title}</h3>
              </div>
              <button 
                onClick={() => setSelectedKO(null)}
                className="p-1.5 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm text-gray-300 leading-relaxed">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-1.5">
                  <FileText size={14} /> Compiled Content
                </h4>
                <div className="bg-gray-950 p-4 rounded-xl border border-gray-800/80 font-mono text-xs whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {selectedKO.content || 'No content stored.'}
                </div>
              </div>

              {selectedKO.provenance && Object.keys(selectedKO.provenance).length > 0 && (
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-1.5">
                    <Layers size={14} /> Provenance Metadata
                  </h4>
                  <pre className="bg-gray-950 p-3.5 rounded-xl border border-gray-800/80 text-xs font-mono text-gray-400 overflow-x-auto">
                    {JSON.stringify(selectedKO.provenance, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-gray-800 flex justify-end">
              <button 
                onClick={() => setSelectedKO(null)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-sm transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeObjectsBrowser;
