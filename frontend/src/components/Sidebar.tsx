import React from 'react';
import { LayoutDashboard, Terminal, Settings2, Waves, Wifi, Send } from 'lucide-react';
import { StateData } from '../api';

interface SidebarProps {
  currentTab: 'dashboard' | 'logs' | 'settings';
  onSelectTab: (tab: 'dashboard' | 'logs' | 'settings') => void;
  state: StateData | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, state }) => {
  const isOnline = state?.online === true;
  const isOffline = state?.online === false;
  const tgRunning = state?.telegram?.configured && state?.telegram?.is_running;

  const navItems = [
    { id: 'dashboard' as const, label: '守护中枢', icon: LayoutDashboard },
    { id: 'logs' as const, label: '事件流日志', icon: Terminal },
    { id: 'settings' as const, label: '核心配置', icon: Settings2 },
  ];

  return (
    <aside className="w-52 h-full ios-glass-sidebar flex flex-col justify-between p-4 z-20 shrink-0">
      <div>
        {/* 典雅品牌标识 */}
        <div className="flex items-center gap-2.5 px-2 py-2.5 mb-5">
          <div className="w-9 h-9 rounded-xl bg-[#2b5797]/10 border border-[#2b5797]/20 flex items-center justify-center text-[#2b5797] shrink-0 shadow-sm">
            <Waves className="w-4 h-4 stroke-[2.2]" />
          </div>
          <div className="min-w-0">
            <h1 className="text-[15px] font-bold tracking-wide text-ink-primary truncate">安澜</h1>
            <p className="text-[11px] text-ink-tertiary truncate">校园网无感守护</p>
          </div>
        </div>

        {/* 导航菜单 */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all duration-150 ${
                  active
                    ? 'ios-btn-primary text-white font-semibold'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-[#142033]/[0.05]'
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 stroke-[2] ${active ? 'text-white' : 'text-ink-tertiary'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* 底部状态概览卡片 */}
      <div className="space-y-2.5 pt-3 border-t border-[#142033]/[0.08]">
        <div className="p-3 rounded-xl ios-glass-card space-y-2">
          {/* 网络自愈状态 */}
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-ink-secondary flex items-center gap-1.5">
              <Wifi className="w-3.5 h-3.5 text-[#2b5797]" />
              链路状态
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isOnline
                    ? 'bg-[#2a9d6c]'
                    : isOffline
                    ? 'bg-[#cf4d54]'
                    : 'bg-[#cf8a27]'
                }`}
              />
              <span
                className={`font-medium ${
                  isOnline ? 'text-[#1f7a53]' : isOffline ? 'text-[#b43a40]' : 'text-[#9a5b13]'
                }`}
              >
                {isOnline ? '在线' : isOffline ? '自愈中' : '就绪'}
              </span>
            </div>
          </div>

          {/* Telegram 手机中枢状态 */}
          <div className="flex items-center justify-between text-[11px] pt-2 border-t border-[#142033]/[0.06]">
            <span className="text-ink-secondary flex items-center gap-1.5">
              <Send className="w-3 h-3 text-ink-tertiary" />
              Telegram
            </span>
            <span className={`text-[11px] font-medium ${tgRunning ? 'text-[#2b5797]' : 'text-ink-tertiary'}`}>
              {tgRunning ? '已连通' : '未挂载'}
            </span>
          </div>
        </div>

        <div className="px-2 flex items-center justify-between text-[10px] text-ink-tertiary">
          <span>安澜 · 桌面端</span>
          <span className="font-mono">{state?.version ? `v${state.version}` : 'v2.3.2'}</span>
        </div>
      </div>
    </aside>
  );
};
