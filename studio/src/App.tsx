import React, { useState, useEffect } from 'react';
import { LayoutDashboard, Search, MessageSquare, BookOpen, Settings, Zap, Upload, Paperclip } from 'lucide-react';
import ImportPage from './components/ImportPage';
import ConversationsBrowser from './components/ConversationsBrowser';
import Dashboard from './components/Dashboard';
import SearchPage from './components/SearchPage';
import ChatPage from './components/ChatPage';
import AttachmentsBrowser from './components/AttachmentsBrowser';
import EntitiesBrowser from './components/EntitiesBrowser';
import KnowledgeObjectsBrowser from './components/KnowledgeObjectsBrowser';
import PlatformsBrowser from './components/PlatformsBrowser';
import { FirestoreService } from './services/FirestoreService';

const App = () => {
  const [view, setView] = useState<'dashboard' | 'import' | 'conversations' | 'search' | 'chat' | 'platforms' | 'knowledgeObjects' | 'entities' | 'attachments'>('dashboard');
  const [stats, setStats] = useState({ platforms: 0, conversations: 0, status: 'Ready', last_compile: 'Never', knowledge_objects: 0 });

  const fetchStats = async () => {
    try {
      const data = await FirestoreService.getDashboardStats();

      setStats({
        platforms: data.platforms,
        conversations: data.conversations,
        status: 'Ready',
        last_compile: data.updated_at ?? 'Never',
        knowledge_objects: data.knowledge_objects ?? 0,
      });
    } catch (err) {
      console.error("Error fetching Firestore dashboard stats:", err);
    }
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
              onClick={() => setView('search')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'search' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <Search size={20}/> Search
            </li>
            <li 
              onClick={() => setView('chat')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'chat' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <Zap size={20}/> Oracle Chat
            </li>
            <li 
              onClick={() => setView('conversations')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'conversations' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <MessageSquare size={20}/> Conversations
            </li>
            <li 
              onClick={() => setView('platforms')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'platforms' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <BookOpen size={20}/> Platforms
            </li>
            <li 
              onClick={() => setView('knowledgeObjects')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'knowledgeObjects' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <BookOpen size={20}/> Knowledge Objects
            </li>
            <li 
              onClick={() => setView('attachments')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'attachments' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <Paperclip size={20}/> Attachments
            </li>
            <li 
              onClick={() => setView('entities')}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${view === 'entities' ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-900 hover:text-white'}`}
            >
              <BookOpen size={20}/> Entities
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
            <h2 className="text-3xl font-bold tracking-tight">
              {view === 'dashboard' ? 'Dashboard' : 
               view === 'import' ? 'Import' : 
               view === 'search' ? 'Search' : 
               view === 'chat' ? 'Oracle Chat' :
               view === 'attachments' ? 'Attachments' :
               view === 'platforms' ? 'Platforms' :
               'Conversations'}
            </h2>
            <p className="text-gray-500 mt-1">
              {view === 'dashboard' ? 'System overview and statistics.' : 
               view === 'import' ? 'Bring new data into your knowledge platform.' : 
               view === 'search' ? 'Global search across all compiled knowledge.' :
               view === 'chat' ? 'Ask questions grounded in your second brain.' :
               view === 'attachments' ? 'Browse extracted files and media.' :
               view === 'platforms' ? 'Active knowledge source platforms.' :
               'Browse all indexed conversations.'}
            </p>
          </div>
          {view === 'dashboard' && (
            <div className="text-right">
              <p className="text-xs text-gray-500 uppercase font-semibold">Last Compiled</p>
              <p className="text-sm font-mono text-gray-300">{stats.last_compile}</p>
            </div>
          )}
        </header>

        {view === 'dashboard' ? <Dashboard stats={stats} /> : 
         view === 'import' ? <ImportPage /> : 
         view === 'search' ? <SearchPage /> :
         view === 'chat' ? <ChatPage /> :
         view === 'attachments' ? <AttachmentsBrowser /> :
         view === 'entities' ? <EntitiesBrowser /> :
         view === 'knowledgeObjects' ? <KnowledgeObjectsBrowser /> :
         view === 'platforms' ? <PlatformsBrowser /> :
         <ConversationsBrowser />}
      </main>
    </div>
  );
};

export default App;
