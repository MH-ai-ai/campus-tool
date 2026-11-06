import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { LogView } from './components/LogView';
import { SettingsView } from './components/SettingsView';
import { QuickSetupModal } from './components/QuickSetupModal';
import { api, StateData } from './api';

export function App() {
  const [currentTab, setCurrentTab] = useState<'dashboard' | 'logs' | 'settings'>('dashboard');
  const [state, setState] = useState<StateData | null>(null);
  const [quickSetupOpen, setQuickSetupOpen] = useState(false);

  const fetchState = async () => {
    try {
      const data = await api.getState();
      setState(data);
    } catch (err) {
      console.error('Failed to get state', err);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 3500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen w-screen bg-apple-bg text-apple-textPrimary overflow-hidden font-sans select-none">
      {/* 左侧磨砂毛玻璃侧边栏 */}
      <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} state={state} />

      {/* 右侧主视窗内容区 */}
      <main className="flex-1 h-full overflow-hidden flex flex-col bg-gradient-to-b from-[#14151e]/50 to-apple-bg">
        {currentTab === 'dashboard' && (
          <DashboardView
            state={state}
            onRefresh={fetchState}
            onOpenQuickSetup={() => setQuickSetupOpen(true)}
          />
        )}
        {currentTab === 'logs' && <LogView />}
        {currentTab === 'settings' && <SettingsView />}
      </main>

      {/* 小白一键打通向导模态弹窗 */}
      <QuickSetupModal
        isOpen={quickSetupOpen}
        onClose={() => setQuickSetupOpen(false)}
        onSuccess={() => {
          fetchState();
        }}
      />
    </div>
  );
}

export default App;
