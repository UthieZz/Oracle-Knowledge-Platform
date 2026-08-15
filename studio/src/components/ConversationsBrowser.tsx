import React, { useState, useEffect } from 'react';


interface Conversation {
  conversation_id: string;
  title: string;
  source: string;
}
const ConversationsBrowser = () => {
  const [data, setData] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetch(`/api/conversations?page=${page}&limit=20&query=${query}`)
      .then(res => res.json())
      .then(res => {
        setData(res.data);
        setTotal(res.total);
      });
  }, [page, query]);

  return (
    <div className="p-6">
      <div className="flex justify-between mb-6">
        <h2 className="text-2xl font-bold">Conversations</h2>
        <input 
          type="text" 
          placeholder="Search..." 
          className="bg-gray-800 p-2 rounded text-white"
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-gray-800 text-gray-400">
            <th className="p-2">Title</th>
            <th className="p-2">Source</th>
          </tr>
        </thead>
        <tbody>
          {data.map(conv => (
            <tr key={conv.conversation_id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="p-2">{conv.title}</td>
              <td className="p-2 text-gray-500">{conv.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex gap-2">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} className="bg-gray-800 px-3 py-1 rounded">Prev</button>
        <span className="px-3 py-1">Page {page} of {Math.ceil(total / 20)}</span>
        <button onClick={() => setPage(p => p + 1)} className="bg-gray-800 px-3 py-1 rounded">Next</button>
      </div>
    </div>
  );
};

export default ConversationsBrowser;
