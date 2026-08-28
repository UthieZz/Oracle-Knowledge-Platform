import React, { useState, useEffect } from 'react';
import { FirestoreService, Conversation } from '../services/FirestoreService';

const ConversationsBrowser = () => {
  const [data, setData] = useState<Conversation[]>([]);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    FirestoreService.getConversations()
      .then(res => {
        setData(res);
        setIsLoading(false);
      });
  }, [page]);

  return (
    <div className="p-6">
      <div className="flex justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Conversations</h2>
      </div>
      
      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <>
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="p-3">Title</th>
                <th className="p-3">Platform</th>
                <th className="p-3">Messages</th>
                <th className="p-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {data.map(conv => (
                <tr key={conv.id} className="border-b border-gray-800 hover:bg-gray-900 transition-colors group">
                  <td className="p-3 font-medium text-gray-200 group-hover:text-white">{conv.title}</td>
                  <td className="p-3 text-gray-500">{conv.source_platform}</td>
                  <td className="p-3 text-gray-500">{conv.message_count}</td>
                  <td className="p-3 text-gray-600 text-sm">{conv.created_date}</td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-10 text-center text-gray-600">No conversations indexed yet.</td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="mt-6 flex justify-center gap-2">
            <button 
              onClick={() => setPage(p => Math.max(1, p - 1))} 
              className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              disabled={page === 1}
            >
              Previous
            </button>
            <span className="px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-gray-400">Page {page}</span>
            <button 
              onClick={() => setPage(p => p + 1)} 
              className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              disabled={data.length < 50}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ConversationsBrowser;
