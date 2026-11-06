import React from 'react';
import { LayoutDashboard, Terminal, Settings2, Shield, Wifi, Send, Radio } from 'lucide-react';
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
    <aside className="w-56 h-full liquid-sidebar flex flex-col justify-between p-4.5 z-20 shrink-0">
      <div>
        {/* Cyber Shield 品牌标识 */}
        <div className="flex items-center gap-3 px-2 py-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#0a84ff] via-[#1c1e2a] to-[#30d158] p-[1.5px] shadow-apple-glow-blue/40 shadow-lg">
            <div className="w-full h-full bg-[#12141c] rounded-[10px] flex items-center justify-center text-white">
              <Shield className="w-4.5 h-4.5 text-[#30d158] stroke-[2.2]" />
            </div>
          </div>
          <div>
            <h1 className="text-xs font-bold tracking-wider uppercase text-white font-mono">Campus Guard</h1>
            <p className="text-[10px] text-apple-textTertiary tracking-wide">无感自愈守护内核</p>
          </div>
        </div>

        {/* 导航菜单 */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 ${
                  active
                    ? 'bg-gradient-to-r from-apple-blue to-[#2894ff] text-white shadow-apple-glow-blue/30 shadow-md font-semibold'
                    : 'text-apple-textSecondary hover:text-white hover:bg-white/[0.06]'
                }`}
              >
                <Icon className={`w-4 h-4 stroke-[2] ${active ? 'text-white' : 'text-apple-textSecondary'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* 底部实时状态呼吸指示药丸 */}
      <div className="space-y-3 pt-4 border-t border-white/[0.08]">
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.08] space-y-2">
          {/* 网络自愈状态 */}
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-apple-textSecondary flex items-center gap-1.5">
              <Wifi className="w-3.5 h-3.5 text-apple-blue" />
              链路状态
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isOnline
                    ? 'bg-apple-green shadow-apple-glow-green animate-pulse'
                    : isOffline
                    ? 'bg-apple-coral shadow-apple-glow-coral'
                    : 'bg-apple-amber animate-pulse'
                }`}
              />
              <span
                className={`font-medium ${
                  isOnline ? 'text-apple-green' : isOffline ? 'text-apple-coral' : 'text-apple-amber'
                }`}
              >
                {isOnline ? '在线' : isOffline ? '自愈中' : '就绪'}
              </span>
            </div>
          </div>

          {/* Telegram 手机中枢状态 */}
          <div className="flex items-center justify-between text-[11px] pt-1.5 border-t border-white/[0.04]">
            <span className="text-apple-textSecondary flex items-center gap-1.5">
              <Send className="w-3 h-3 text-cyan-400" />
              Telegram
            </span>
            <span className={`text-[10px] font-mono ${tgRunning ? 'text-cyan-400 font-medium' : 'text-apple-textTertiary'}`}>
              {tgRunning ? '手机已连通' : '未挂载'}
            </span>
          </div>
        </div>

        {/* 底部架构标志 */}
        <div className="px-2 flex items-center justify-between text-[10px] text-apple-textTertiary font-mono">
          <span>Pro Edition</span>
          <span className="uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/[0.05]">
            Liquid Glass
          </span>
        </div>
      </div>
    </aside>
  );
};
