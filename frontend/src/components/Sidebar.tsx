import React from 'react';
import { LayoutDashboard, Terminal, Settings2, ShieldCheck, Wifi, BatteryCharging, AlertCircle } from 'lucide-react';
import { StateData } from '../api';

interface SidebarProps {
  currentTab: 'dashboard' | 'logs' | 'settings';
  onSelectTab: (tab: 'dashboard' | 'logs' | 'settings') => void;
  state: StateData | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, state }) => {
  const isOnline = state?.online === true;
  const isOffline = state?.online === false;

  const navItems = [
    { id: 'dashboard' as const, label: '控制概览', icon: LayoutDashboard },
    { id: 'logs' as const, label: '运行日志', icon: Terminal },
    { id: 'settings' as const, label: '偏好设置', icon: Settings2 },
  ];

  return (
    <aside className="w-56 h-full bg-apple-sidebar/95 border-r border-white/[0.08] flex flex-col justify-between p-4 backdrop-blur-xl shrink-0">
      <div>
        {/* Logo 与主标题 */}
        <div className="flex items-center gap-3 px-2 py-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-apple-blue to-cyan-400 flex items-center justify-center shadow-apple-glow-blue/40 shadow-lg text-white">
            <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white">Campus Guard</h1>
            <p className="text-[11px] text-apple-textTertiary">校园网智能守护</p>
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
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-150 ${
                  active
                    ? 'bg-apple-blue text-white shadow-apple-glow-blue/20 shadow-md'
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

      {/* 底部实时状态呼吸药丸与版本信息 */}
      <div className="space-y-3 pt-4 border-t border-white/[0.06]">
        {/* 状态指示条 */}
        <div className="px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-apple-textSecondary flex items-center gap-1.5">
              <Wifi className="w-3.5 h-3.5" />
              网络状态
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isOnline
                    ? 'bg-apple-green shadow-apple-glow-green animate-pulse'
                    : isOffline
                    ? 'bg-apple-coral shadow-apple-glow-coral'
                    : 'bg-apple-amber'
                }`}
              />
              <span
                className={`font-medium ${
                  isOnline ? 'text-apple-green' : isOffline ? 'text-apple-coral' : 'text-apple-amber'
                }`}
              >
                {isOnline ? '已在线' : isOffline ? '已离线' : '探测中'}
              </span>
            </div>
          </div>

          {state?.battery && (
            <div className="flex items-center justify-between text-[11px] text-apple-textTertiary">
              <span className="flex items-center gap-1.5">
                <BatteryCharging className="w-3.5 h-3.5" />
                电源电量
              </span>
              <span className="font-mono text-apple-textSecondary">{state.battery.percent}%</span>
            </div>
          )}
        </div>

        {/* 底部版本 */}
        <div className="px-2 flex items-center justify-between text-[10px] text-apple-textTertiary">
          <span>v2.1.0 (Apple HIG)</span>
          <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/[0.06]">Webview2</span>
        </div>
      </div>
    </aside>
  );
};
