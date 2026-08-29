import React, { useState, useEffect } from 'react';
import { Database, MessageSquare, Paperclip, Activity, Tag, Layers, Loader2 } from 'lucide-react';
import { FirestoreService, Platform } from '../services/FirestoreService';

const PlatformsBrowser = () => {
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    FirestoreService.getPlatforms()
      .then(data => {
        setPlatforms(data);
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load platforms:", err);
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="animate-spin text-blue-500" size={36} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Layers className="text-blue-500" /> Active Source Platforms
          </h2>
          <p className="text-gray-500 text-sm mt-1">Multi-source provenance boundaries compiled into canonical knowledge.</p>
        </div>
        <span className="text-xs font-semibold px-3 py-1 bg-gray-900 border border-gray-800 text-gray-400 rounded-full">
          {platforms.length} Platforms Active
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {platforms.map((p, idx) => {
          const convCount = p.conversation_count ?? p.conversations_count ?? 0;
          const msgCount = p.message_count ?? 0;
          const attCount = p.attachment_count ?? p.attachments_count ?? 0;
          const entCount = p.entity_count ?? 0;

          return (
            <div key={p.id || idx} className="bg-gray-900/90 border border-gray-800 rounded-2xl p-7 hover:border-blue-500/50 transition-all group shadow-sm">
              <div className="flex justify-between items-start mb-5">
                <div className="p-3 bg-blue-600/10 rounded-xl group-hover:bg-blue-600/20 transition-colors">
                  <Database className="text-blue-500" size={28} />
                </div>
                <span className="bg-emerald-500/10 text-emerald-400 text-xs font-bold px-3 py-1 rounded-full border border-emerald-500/20 flex items-center gap-1.5">
                  <Activity size={12} /> Active
                </span>
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">{p.name || p.id}</h3>
              <p className="text-gray-400 text-sm mb-6 leading-relaxed">
                {p.description || `Canonical provenance source for indexed ${p.name} conversations and extracted artifacts.`}
              </p>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-5 border-t border-gray-800 text-xs">
                <div className="bg-gray-950/60 p-2.5 rounded-lg border border-gray-800/60">
                  <span className="text-gray-500 flex items-center gap-1 mb-1">
                    <MessageSquare size={13} /> Convs
                  </span>
                  <span className="text-base font-bold text-white">{convCount}</span>
                </div>
                <div className="bg-gray-950/60 p-2.5 rounded-lg border border-gray-800/60">
                  <span className="text-gray-500 flex items-center gap-1 mb-1">
                    <Layers size={13} /> Messages
                  </span>
                  <span className="text-base font-bold text-white">{msgCount}</span>
                </div>
                <div className="bg-gray-950/60 p-2.5 rounded-lg border border-gray-800/60">
                  <span className="text-gray-500 flex items-center gap-1 mb-1">
                    <Paperclip size={13} /> Attachments
                  </span>
                  <span className="text-base font-bold text-white">{attCount}</span>
                </div>
                <div className="bg-gray-950/60 p-2.5 rounded-lg border border-gray-800/60">
                  <span className="text-gray-500 flex items-center gap-1 mb-1">
                    <Tag size={13} /> Entities
                  </span>
                  <span className="text-base font-bold text-white">{entCount}</span>
                </div>
              </div>
            </div>
          );
        })}
        {platforms.length === 0 && (
          <div className="col-span-full py-20 text-center bg-gray-900 border border-dashed border-gray-800 rounded-2xl">
            <Database className="mx-auto text-gray-800 mb-4" size={48} />
            <p className="text-gray-500">No platforms compiled yet. Import your AI export archives to begin.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PlatformsBrowser;
