import React, { useState, useEffect } from 'react';
import { LayoutDashboard, Search, MessageSquare, BookOpen, Settings, Zap, Paperclip, Tag, Layers, ShieldCheck, Menu, X } from 'lucide-react';
import ImportPage from './components/ImportPage';
import ConversationsBrowser from './components/ConversationsBrowser';
import Dashboard from './components/Dashboard';
import SearchPage from './components/SearchPage';
import ChatPage from './components/ChatPage';
import AttachmentsBrowser from './components/AttachmentsBrowser';
import EntitiesBrowser from './components/EntitiesBrowser';
import KnowledgeObjectsBrowser from './components/KnowledgeObjectsBrowser';
import PlatformsBrowser from './components/PlatformsBrowser';
import SettingsModal from './components/SettingsModal';
import { FirestoreService } from './services/FirestoreService';
import { CredentialService } from './services/CredentialService';

const App = () => {
  const [view, setView] = useState<'dashboard' | 'import' | 'conversations' | 'search' | 'chat' | 'platforms' | 'knowledgeObjects' | 'entities' | 'attachments'>('dashboard');
  const [stats, setStats] = useState({ platforms: 0, conversations: 0, status: 'Ready', last_compile: 'Never', knowledge_objects: 0 });
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [hasGeminiKey, setHasGeminiKey] = useState(CredentialService.hasGeminiApiKey());

  const fetchStats = async () => {
    try {
      const data = await FirestoreService.getDashboardStats();
      setStats({
        platforms: data.platforms,
        conversations: data.conversations,
        status: 'Ready',
        last_compile: data.updated_at ? new Date(data.updated_at).toLocaleString() : 'Never',
        knowledge_objects: data.knowledge_objects ?? 0,
      });
      setHasGeminiKey(CredentialService.hasGeminiApiKey());
    } catch (err) {
      console.error("[STUDIO] Error fetching dashboard stats:", err);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 8000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { id: 'search', label: 'Search', icon: <Search size={18} /> },
    { id: 'chat', label: 'Oracle Chat', icon: <Zap size={18} /> },
    { id: 'conversations', label: 'Conversations', icon: <MessageSquare size={18} /> },
    { id: 'knowledgeObjects', label: 'Knowledge Objects', icon: <BookOpen size={18} /> },
    { id: 'platforms', label: 'Platforms', icon: <Layers size={18} /> },
    { id: 'entities', label: 'Entities', icon: <Tag size={18} /> },
    { id: 'attachments', label: 'Attachments', icon: <Paperclip size={18} /> },
    { id: 'import', label: 'Import Sources', icon: <BookOpen size={18} /> },
  ];

  return (
    <div className="flex h-screen bg-black text-white font-sans selection:bg-blue-500/30 overflow-hidden">
      {/* Mobile Menu Backdrop */}
      {mobileMenuOpen && (
        <div 
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-black/70 z-40 md:hidden"
        />
      )}

      {/* Sidebar Navigation */}
      <nav className={`fixed md:static inset-y-0 left-0 z-50 w-64 bg-gray-950 p-6 border-r border-gray-800 flex flex-col justify-between transform transition-transform duration-200 md:translate-x-0 ${
        mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div>
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-xl font-bold flex items-center gap-2.5">
              <div className="p-1.5 bg-blue-600/20 border border-blue-500/40 rounded-lg">
                <Zap className="text-blue-500 fill-blue-500" size={18}/>
              </div>
              <span className="tracking-tight font-black text-white">Oracle Studio</span>
            </h1>
            <button 
              onClick={() => setMobileMenuOpen(false)}
              className="md:hidden text-gray-400 hover:text-white"
            >
              <X size={20} />
            </button>
          </div>
          
          <div className="space-y-6">
            <div>
              <h2 className="text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-3 px-2">Navigation</h2>
              <ul className="space-y-1 text-gray-400">
                {navItems.map((item) => (
                  <li 
                    key={item.id}
                    onClick={() => { setView(item.id as any); setMobileMenuOpen(false); }}
                    className={`flex items-center gap-3 px-3 py-2 rounded-xl cursor-pointer transition-colors text-sm ${
                      view === item.id 
                        ? 'bg-blue-600 text-white font-semibold shadow-sm' 
                        : 'hover:bg-gray-900/80 hover:text-white'
                    }`}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Sidebar Footer */}
        <div className="pt-4 border-t border-gray-800 space-y-2">
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-900 transition-colors text-sm"
          >
            <div className="flex items-center gap-3">
              <Settings size={18}/>
              <span>Settings</span>
            </div>
            {hasGeminiKey ? (
              <span className="w-2 h-2 rounded-full bg-emerald-400" title="Gemini API Key Active"></span>
            ) : (
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" title="Gemini API Key Missing"></span>
            )}
          </button>
          <div className="px-3 py-1 flex items-center justify-between text-[10px] text-gray-600 font-mono">
            <span>OKP Closed Beta</span>
            <span>v1.0.0</span>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-gray-900 via-black to-black">
        {/* Top Header */}
        <header className="p-6 md:p-8 border-b border-gray-800/80 flex justify-between items-center bg-gray-950/40 backdrop-blur-sm flex-shrink-0">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-lg bg-gray-900 text-gray-300 hover:text-white"
            >
              <Menu size={20} />
            </button>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white capitalize">
                {view === 'knowledgeObjects' ? 'Knowledge Objects' : view}
              </h2>
              <p className="text-gray-500 text-xs mt-0.5 hidden sm:block">
                {view === 'dashboard' ? 'Compiled system knowledge statistics and health.' : 
                 view === 'import' ? 'Canonical local compilation workflow.' : 
                 view === 'search' ? 'Global multi-collection deterministic retrieval.' :
                 view === 'chat' ? 'Evidence-grounded conversational reasoning layer.' :
                 view === 'attachments' ? 'Files and media extracted from imported sources.' :
                 view === 'platforms' ? 'Source platforms compiled into the knowledge package.' :
                 view === 'entities' ? 'Structured entity graph and concept mentions.' :
                 view === 'knowledgeObjects' ? 'Canonical compiled knowledge objects with provenance.' :
                 'Indexed conversation sessions and messages.'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="p-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-300 hover:text-white transition-colors"
              title="Platform Settings"
            >
              <Settings size={18} />
            </button>
          </div>
        </header>

        {/* Scrollable View Area */}
        <div className="flex-1 p-6 md:p-8 overflow-y-auto">
          {view === 'dashboard' ? <Dashboard stats={stats} /> : 
           view === 'import' ? <ImportPage /> : 
           view === 'search' ? <SearchPage /> :
           view === 'chat' ? <ChatPage onOpenSettings={() => setIsSettingsOpen(true)} /> :
           view === 'attachments' ? <AttachmentsBrowser /> :
           view === 'entities' ? <EntitiesBrowser /> :
           view === 'knowledgeObjects' ? <KnowledgeObjectsBrowser /> :
           view === 'platforms' ? <PlatformsBrowser /> :
           <ConversationsBrowser />}
        </div>
      </main>

      {/* Settings Modal */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => {
          setIsSettingsOpen(false);
          setHasGeminiKey(CredentialService.hasGeminiApiKey());
        }}
        onStatsRefresh={fetchStats}
      />
    </div>
  );
};

export default App;
