import React, { useState, useEffect } from 'react';
import { FirestoreService, KnowledgeObject } from '../services/FirestoreService';

const KnowledgeObjectsBrowser = () => {
  const [data, setData] = useState<KnowledgeObject[]>([]);

  useEffect(() => {
    FirestoreService.getKnowledgeObjects().then(setData);
  }, []);

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">Knowledge Objects</h2>
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-gray-800 text-gray-400">
            <th className="p-2">Title</th>
            <th className="p-2">Type</th>
            <th className="p-2">Platform</th>
            <th className="p-2">Created</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="p-2">{item.title}</td>
              <td className="p-2">{item.type}</td>
              <td className="p-2">{item.source_platform}</td>
              <td className="p-2">{item.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default KnowledgeObjectsBrowser;
