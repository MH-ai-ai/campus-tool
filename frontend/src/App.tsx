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
      setState((prev) => {
        if (
          prev &&
          prev.online === data.online &&
          prev.wifi === data.wifi &&
          prev.ip === data.ip &&
          prev.battery?.percent === data.battery?.percent &&
          prev.battery?.plugged === data.battery?.plugged &&
          prev.last_event === data.last_event &&
          prev.system?.memory === data.system?.memory &&
          prev.telegram?.is_running === data.telegram?.is_running
        ) {
          return prev;
        }
        return data;
      });
    } catch (err) {
      console.error('Failed to get state', err);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative flex h-screen w-screen twilight-sky-backdrop text-white overflow-hidden font-sans select-none">
      {/* 左侧暮色水晶通透侧边栏 */}
      <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} state={state} />

      {/* 右侧主视窗内容区 (极速硬件加速的高透玻璃容器) */}
      <main className="relative z-10 flex-1 h-full overflow-hidden flex flex-col will-change-transform">
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
