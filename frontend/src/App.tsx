import React, { useState, useEffect } from 'react';
import { Power, Minimize2, X } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { LogView } from './components/LogView';
import { SettingsView } from './components/SettingsView';
import { ToastProvider } from './components/ToastContext';
import { api, StateData } from './api';

export function App() {
  const [currentTab, setCurrentTab] = useState<'dashboard' | 'logs' | 'settings'>('dashboard');
  const [state, setState] = useState<StateData | null>(null);
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [rememberCloseChoice, setRememberCloseChoice] = useState(false);
  const [closingActionBusy, setClosingActionBusy] = useState(false);

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
          prev.telegram?.is_running === data.telegram?.is_running &&
          prev.version === data.version
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

    const onCloseRequested = () => {
      setRememberCloseChoice(false);
      setClosingActionBusy(false);
      setCloseDialogOpen(true);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setCloseDialogOpen(false);
      }
    };

    window.addEventListener('anlan:close-requested', onCloseRequested);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      clearInterval(interval);
      window.removeEventListener('anlan:close-requested', onCloseRequested);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, []);

  const submitCloseChoice = async (action: 'tray' | 'exit') => {
    if (closingActionBusy) return;
    setClosingActionBusy(true);
    try {
      await api.handleCloseChoice(action, rememberCloseChoice);
      setCloseDialogOpen(false);
    } catch (err) {
      console.error('Close choice failed', err);
      setCloseDialogOpen(false);
    } finally {
      setClosingActionBusy(false);
    }
  };

  return (
    <ToastProvider>
      <div className="relative flex h-screen w-screen ios-canvas-backdrop text-ink-primary overflow-hidden font-sans select-none">
        {/* 左侧 iOS 浅色微透侧边栏 */}
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} state={state} />

        {/* 右侧主视窗内容区 */}
        <main className="relative z-10 flex-1 min-w-0 h-full overflow-hidden flex flex-col">
          {currentTab === 'dashboard' && (
            <DashboardView state={state} onRefresh={fetchState} />
          )}
          {currentTab === 'logs' && <LogView />}
          {currentTab === 'settings' && <SettingsView />}
        </main>

        {/* 关闭窗口 (×) 行为选择模态框 */}
        {closeDialogOpen && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-[#142033]/25 backdrop-blur-sm p-4"
            onClick={() => !closingActionBusy && setCloseDialogOpen(false)}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="close-dialog-title"
              className="w-full max-w-md rounded-2xl bg-white/95 backdrop-blur-xl border border-[#142033]/12 shadow-glass-elevated p-5 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 id="close-dialog-title" className="text-sm font-bold text-ink-primary">
                    关闭 安澜
                  </h3>
                  <p className="text-xs text-ink-secondary mt-1 leading-relaxed">
                    选择最小化到系统托盘后，安澜将继续在后台守护校园网断线重连与电量安全；选择直接退出将停止全部守护服务。
                  </p>
                </div>
                <button
                  type="button"
                  aria-label="取消关闭"
                  onClick={() => setCloseDialogOpen(false)}
                  disabled={closingActionBusy}
                  className="p-1 rounded-lg text-ink-tertiary hover:text-ink-primary hover:bg-[#142033]/[0.06] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <label className="flex items-center gap-2 text-xs text-ink-secondary cursor-pointer select-none pt-1">
                <input
                  type="checkbox"
                  checked={rememberCloseChoice}
                  onChange={(e) => setRememberCloseChoice(e.target.checked)}
                  disabled={closingActionBusy}
                  className="w-4 h-4 rounded accent-[#2b5797] border-[#142033]/25"
                />
                <span>记住我的选择，下次不再询问（可在核心配置中修改）</span>
              </label>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#142033]/[0.07]">
                <button
                  type="button"
                  onClick={() => setCloseDialogOpen(false)}
                  disabled={closingActionBusy}
                  className="ios-btn-secondary h-8 px-3 rounded-lg text-xs font-medium text-ink-secondary disabled:opacity-50"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => submitCloseChoice('exit')}
                  disabled={closingActionBusy}
                  className="h-8 px-3 rounded-lg text-xs font-semibold border border-[#cf4d54]/35 bg-[#cf4d54]/[0.07] text-[#b43a40] hover:bg-[#cf4d54]/[0.13] inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <Power className="w-3.5 h-3.5" />
                  <span>直接退出程序</span>
                </button>
                <button
                  type="button"
                  onClick={() => submitCloseChoice('tray')}
                  disabled={closingActionBusy}
                  className="ios-btn-primary h-8 px-3.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Minimize2 className="w-3.5 h-3.5" />
                  <span>最小化到托盘</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ToastProvider>
  );
}

export default App;
