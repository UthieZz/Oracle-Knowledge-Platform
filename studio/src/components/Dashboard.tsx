import React from 'react';

const Dashboard = ({ stats }: { stats: any }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 shadow-sm">
      <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Platforms</h3>
      <p className="text-4xl font-bold text-white">{stats.platforms}</p>
      <p className="text-gray-500 text-sm mt-1">Active sources</p>
    </div>
    <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 shadow-sm">
      <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Conversations</h3>
      <p className="text-4xl font-bold text-white">{stats.conversations}</p>
      <p className="text-gray-500 text-sm mt-1">Total indexed</p>
    </div>
    <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 shadow-sm">
      <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">System Status</h3>
      <p className={`text-4xl font-bold ${stats.status === 'Running' ? 'text-blue-500' : 'text-green-500'}`}>
        {stats.status}
      </p>
      <p className="text-gray-500 text-sm mt-1">Pipeline state</p>
    </div>
    <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 shadow-sm">
        <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Knowledge Objects</h3>
        <p className="text-4xl font-bold text-white">{stats.knowledge_objects}</p>
        <p className="text-gray-500 text-sm mt-1">Total extracted</p>
    </div>
  </div>
);

export default Dashboard;
