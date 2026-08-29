import React, { useState, useEffect } from 'react';
import { Paperclip, FileText, Search, Loader2, Image, FileCode, Music } from 'lucide-react';
import { FirestoreService, Attachment } from '../services/FirestoreService';

const AttachmentsBrowser = () => {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    FirestoreService.getAttachments(100)
      .then(data => {
        setAttachments(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load attachments:", err);
        setIsLoading(false);
      });
  }, []);

  const filtered = attachments.filter(a => {
    const name = (a.file_name || a.name || '').toLowerCase();
    const platform = (a.source_platform || a.platform || '').toLowerCase();
    const summary = (a.summary || a.processed_content || '').toLowerCase();
    const q = query.toLowerCase();
    return name.includes(q) || platform.includes(q) || summary.includes(q);
  });

  const getMediaIcon = (mediaType?: string) => {
    const mt = (mediaType || '').toLowerCase();
    if (mt.includes('image') || mt.includes('png') || mt.includes('jpg')) return <Image size={24} className="text-emerald-400" />;
    if (mt.includes('code') || mt.includes('json') || mt.includes('py')) return <FileCode size={24} className="text-amber-400" />;
    if (mt.includes('audio') || mt.includes('mp3') || mt.includes('voice')) return <Music size={24} className="text-purple-400" />;
    return <FileText size={24} className="text-blue-400" />;
  };

  return (
    <div className="p-6 bg-gray-950 rounded-2xl border border-gray-800">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Paperclip className="text-blue-500" /> Extracted Attachments
          </h2>
          <p className="text-gray-500 text-sm mt-1">Files, images, and audio metadata extracted during compilation.</p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
          <input 
            type="text" 
            placeholder="Search attachments..." 
            className="w-full bg-gray-900 border border-gray-800 rounded-lg py-2 pl-10 pr-4 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="animate-spin text-blue-500" size={32} />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((att) => {
            const fileName = att.file_name || att.name || att.id;
            const summary = att.summary || att.processed_content;
            const platform = att.source_platform || att.platform || 'General';

            return (
              <div key={att.id} className="bg-gray-900/80 border border-gray-800 p-5 rounded-xl hover:border-gray-700 transition-all group flex flex-col justify-between">
                <div>
                  <div className="flex items-start gap-3.5 mb-3">
                    <div className="p-2.5 bg-gray-800/80 rounded-lg group-hover:bg-blue-600/20 transition-colors flex-shrink-0">
                      {getMediaIcon(att.media_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-white text-sm truncate" title={fileName}>{fileName}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold bg-gray-800 px-1.5 py-0.5 rounded">
                          {platform}
                        </span>
                        {att.media_type && (
                          <span className="text-[10px] text-gray-500 font-mono truncate">
                            {att.media_type}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {att.conversation_id && (
                    <p className="text-xs text-gray-500 font-mono truncate mb-2">
                      Conv: {att.conversation_title || att.conversation_id}
                    </p>
                  )}
                </div>

                {summary && (
                  <div className="mt-3 pt-3 border-t border-gray-800/80 text-xs text-gray-400 line-clamp-3 leading-relaxed">
                    {summary}
                  </div>
                )}
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="col-span-full py-16 text-center text-gray-600">
              <Paperclip className="mx-auto mb-3 opacity-30" size={40} />
              <p>No attachments found.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AttachmentsBrowser;
