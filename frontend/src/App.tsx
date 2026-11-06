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
    <div className="relative flex h-screen w-screen twilight-sky-backdrop text-white overflow-hidden font-sans select-none">
      {/* 暮色流光环境光晕球 (Ethereal Ambient Glowing Spheres) */}
      <div className="twilight-glow-sunset" />
      <div className="twilight-glow-amethyst" />
      <div className="twilight-glow-gold" />
      <div className="twilight-glow-cyan" />

      {/* 诗意微云与暮色晨昏星光背景纹理层 (Ethereal Twilight Clouds & Shimmer) */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none opacity-20 z-0 mix-blend-overlay"
        xmlns="http://www.w3.org/2000/svg"
      >
        <filter id="twilightNoise">
          <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="4" stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0.2" />
        </filter>
        <rect width="100%" height="100%" filter="url(#twilightNoise)" />
      </svg>

      {/* 左侧暮色水晶通透侧边栏 */}
      <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} state={state} />

      {/* 右侧主视窗内容区 (高透水晶液态玻璃容器) */}
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
