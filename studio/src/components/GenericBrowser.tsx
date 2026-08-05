import React, { useState, useEffect } from 'react';

const GenericBrowser = ({ title, endpoint, columns }: { title: string, endpoint: string, columns: { key: string, label: string }[] }) => {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetch(`/api/${endpoint}?page=${page}&limit=20&query=${query}`)
      .then(res => res.json())
      .then(res => {
        setData(res.data);
        setTotal(res.total);
      });
  }, [page, query, endpoint]);

  return (
    <div className="p-6">
      <div className="flex justify-between mb-6">
        <h2 className="text-2xl font-bold">{title}</h2>
        <input 
          type="text" 
          placeholder="Search..." 
          className="bg-gray-800 p-2 rounded text-white"
          onChange={(e) => { setQuery(e.target.value); setPage(1); }}
        />
      </div>
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-gray-800 text-gray-400">
            {columns.map(col => <th key={col.key} className="p-2">{col.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((item, idx) => (
            <tr key={idx} className="border-b border-gray-800 hover:bg-gray-900">
              {columns.map(col => <td key={col.key} className="p-2">{item[col.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex gap-2">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} className="bg-gray-800 px-3 py-1 rounded">Prev</button>
        <span className="px-3 py-1">Page {page} of {Math.max(1, Math.ceil(total / 20))}</span>
        <button onClick={() => setPage(p => Math.min(Math.ceil(total / 20), p + 1))} className="bg-gray-800 px-3 py-1 rounded">Next</button>
      </div>
    </div>
  );
};

export default GenericBrowser;
