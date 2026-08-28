import React, { useState, useEffect } from 'react';
import { Database, MessageSquare, Paperclip, Activity } from 'lucide-react';
import { FirestoreService } from '../services/FirestoreService';

const PlatformsBrowser = () => {
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    FirestoreService.getPlatforms()
      .then(data => {
        setPlatforms(data);
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {platforms.map((p, idx) => (
        <div key={idx} className="bg-gray-900 border border-gray-800 rounded-2xl p-8 hover:border-blue-500/50 transition-all group">
          <div className="flex justify-between items-start mb-6">
            <div className="p-3 bg-blue-600/10 rounded-xl group-hover:bg-blue-600/20 transition-colors">
              <Database className="text-blue-500" size={32} />
            </div>
            <span className="bg-green-500/10 text-green-500 text-xs font-bold px-3 py-1 rounded-full border border-green-500/20 flex items-center gap-1">
              <Activity size={12} /> Active
            </span>
          </div>
          <h3 className="text-2xl font-bold text-white mb-2">{p.name || p.id}</h3>
          <p className="text-gray-500 text-sm mb-6">{p.description || 'Source platform for indexed conversations and extracted knowledge objects.'}</p>
          
          <div className="grid grid-cols-2 gap-4 pt-6 border-t border-gray-800">
            <div className="flex items-center gap-2 text-gray-400">
              <MessageSquare size={16} />
              <span className="text-sm font-medium">{p.conversations_count || 0} Conversations</span>
            </div>
            <div className="flex items-center gap-2 text-gray-400">
              <Paperclip size={16} />
              <span className="text-sm font-medium">{p.attachments_count || 0} Attachments</span>
            </div>
          </div>
        </div>
      ))}
      {platforms.length === 0 && (
        <div className="col-span-full py-20 text-center bg-gray-900 border border-dashed border-gray-800 rounded-2xl">
          <Database className="mx-auto text-gray-800 mb-4" size={48} />
          <p className="text-gray-500">No platforms identified. Import data to get started.</p>
        </div>
      )}
    </div>
  );
};

export default PlatformsBrowser;
