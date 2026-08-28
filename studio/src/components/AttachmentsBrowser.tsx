import React, { useState, useEffect } from 'react';
import { Paperclip, FileText, Search } from 'lucide-react';
import { FirestoreService, Attachment } from '../services/FirestoreService';

const AttachmentsBrowser = () => {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    FirestoreService.getAttachments()
      .then(data => {
        setAttachments(data);
        setIsLoading(false);
      });
  }, []);

  const filtered = attachments.filter(a => 
    a.name.toLowerCase().includes(query.toLowerCase()) || 
    a.platform.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="p-6 bg-gray-950 rounded-2xl border border-gray-800">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Paperclip className="text-blue-500" /> Attachments
        </h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
          <input 
            type="text" 
            placeholder="Search attachments..." 
            className="bg-gray-900 border border-gray-800 rounded-lg py-2 pl-10 pr-4 text-white focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all w-64"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((att) => (
            <div key={att.id} className="bg-gray-900 border border-gray-800 p-5 rounded-xl hover:bg-gray-800 transition-all group">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-gray-800 rounded-lg group-hover:bg-blue-600/20 transition-colors">
                  <FileText className="text-gray-400 group-hover:text-blue-400" size={24} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-white truncate mb-1">{att.name}</h3>
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">{att.platform}</p>
                  <p className="text-xs text-gray-600 mt-2 line-clamp-1">{att.conversation_title || 'Unlinked attachment'}</p>
                </div>
              </div>
              
              {(att.processed_content || att.ocr_text) && (
                <div className="mt-4 pt-4 border-t border-gray-800">
                  <span className="text-[10px] bg-blue-600/10 text-blue-500 px-2 py-0.5 rounded font-bold uppercase">Processed</span>
                  <p className="text-xs text-gray-500 mt-2 line-clamp-2 italic">
                    {att.processed_content || att.ocr_text}
                  </p>
                </div>
              )}
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full py-20 text-center opacity-50">
              <Paperclip className="mx-auto mb-4" size={48} />
              <p>No attachments found.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AttachmentsBrowser;
