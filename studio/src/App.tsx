import React, { useState, useEffect } from 'react';
import { LayoutDashboard, Search, MessageSquare, BookOpen, Settings, Zap, Upload } from 'lucide-react';
import ImportPage from './components/ImportPage';

// Simplified Dashboard Component
const Dashboard = ({ stats }: { stats: any }) => (
  <div className="grid grid-cols-3 gap-4">
    <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
      <h3 className="text-gray-400 text-sm font-medium mb-1">Platforms</h3>
      <p className="text-3xl font-bold text-white">{stats.platforms}</p>
    </div>
    <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
      <h3 className="text-gray-400 text-sm font-medium mb-1">Conversations</h3>
      <p className="text-3xl font-bold text-white">{stats.conversations}</p>
    </div>
    <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
      <h3 className="text-gray-400 text-sm font-medium mb-1">Status</h3>
      <p className={`text-3xl font-bold ${stats.status === 'Running' ? 'text-blue-500' : 'text-green-500'}`}>
        {stats.status}
      </p>
    </div>
  </div>
);

const App = () => {
  const [view, setView] = useState<'dashboard' | 'import'>('dashboard');
  const [stats, setStats] = useState({ platforms: 0, conversations: 0, status: 'Ready', last_compile: 'Never' });

  const fetchStats = () => {
    fetch('/api/dashboard')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error("Error fetching stats:", err));
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-black text-white font-sans selection:bg-blue-500/30">
      {/* Sidebar Navigation */}
      <nav className="w-64 bg-gray-950 p-6 border-r border-gray-800 flex flex-col">
        <h1 className="text-xl font-bold mb-10 flex items-center gap-2">
          <Zap className="text-blue-500 fill-blue-500" size={24}/> 
          <span className="tracking-tight">Oracle Studio</span>
        </h1>
        
        <div className="flex-1">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4 px-2">Main Menu</h2>
          <ul className="space-y-2 text-gray-400">
            <li 
              onClick={() => setView('dashboard')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'dashboard' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <LayoutDashboard size={20}/> Dashboard
            </li>
            <li 
              onClick={() => setView('import')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'import' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <Upload size={20}/> Import
            </li>
            <li className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-not-allowed text-gray-600">
              <Search size={20}/> Search
            </li>
            <li className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-not-allowed text-gray-600">
              <MessageSquare size={20}/> Chat
            </li>
            <li className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-not-allowed text-gray-600">
              <BookOpen size={20}/> Knowledge
            </li>
          </ul>
        </div>

        <div className="pt-6 border-t border-gray-800">
          <ul className="space-y-2 text-gray-400">
            <li className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-not-allowed text-gray-600">
              <Settings size={20}/> Settings
            </li>
          </ul>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-10 overflow-y-auto bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-gray-900 via-black to-black">
        <header className="mb-10 flex justify-between items-end">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{view === 'dashboard' ? 'Dashboard' : 'Import'}</h2>
            <p className="text-gray-500 mt-1">
              {view === 'dashboard' ? 'System overview and statistics.' : 'Bring new data into your knowledge platform.'}
            </p>
          </div>
          {view === 'dashboard' && (
            <div className="text-right">
              <p className="text-xs text-gray-500 uppercase font-semibold">Last Compiled</p>
              <p className="text-sm font-mono text-gray-300">{stats.last_compile}</p>
            </div>
          )}
        </header>

        {view === 'dashboard' ? <Dashboard stats={stats} /> : <ImportPage />}
      </main>
    </div>
  );
};

export default App;
