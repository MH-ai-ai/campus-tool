import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { LogView } from './components/LogView';
import { SettingsView } from './components/SettingsView';
import { api, StateData } from './api';

export function App() {
  const [currentTab, setCurrentTab] = useState<'dashboard' | 'logs' | 'settings'>('dashboard');
  const [state, setState] = useState<StateData | null>(null);

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
    <div className="relative flex h-screen w-screen bg-[#0b0c11] text-apple-textPrimary overflow-hidden font-sans select-none">
      {/* 底层极光流动微光折射源 (Ambient Liquid Mesh Glow) */}
      <div className="ambient-glow-sphere-1" />
      <div className="ambient-glow-sphere-2" />
      <div className="ambient-glow-sphere-3" />

      {/* 左侧液态毛玻璃侧边栏 */}
      <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} state={state} />

      {/* 右侧主视窗内容区 (真·液态玻璃折射容器) */}
      <main className="relative z-10 flex-1 h-full overflow-hidden flex flex-col">
        {currentTab === 'dashboard' && (
          <DashboardView
            state={state}
            onRefresh={fetchState}
          />
        )}
        {currentTab === 'logs' && <LogView />}
        {currentTab === 'settings' && <SettingsView />}
      </main>
    </div>
  );
}

export default App;
