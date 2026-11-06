import React, { useState } from 'react';
import {
  Wifi,
  KeyRound,
  LogOut,
  Minimize2,
  RefreshCw,
  Send,
  Radio,
  Globe,
  Activity,
  CheckCircle2,
  AlertCircle,
  Loader2,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Cpu,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { StateData, api } from '../api';

interface DashboardViewProps {
  state: StateData | null;
  onRefresh: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ state, onRefresh }) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [showTgConfig, setShowTgConfig] = useState(false);
  const [botToken, setBotToken] = useState('');
  const [botUserId, setBotUserId] = useState('');
  const [savingTg, setSavingTg] = useState(false);

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3500);
  };

  const handleAction = async (name: string, fn: () => Promise<any>) => {
    setActionLoading(name);
    try {
      const res = await fn();
      if (res && res.success !== undefined) {
        showToast(res.success ? 'success' : 'error', res.message || '指令执行完毕');
      } else {
        showToast('success', '指令已下发');
      }
      onRefresh();
    } catch (err: any) {
      showToast('error', `操作异常: ${err.message || err}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleTestTelegram = async () => {
    setActionLoading('test_tg');
    try {
      const res = await api.testTelegramBot();
      showToast(res.success ? 'success' : 'error', res.message);
    } catch (err: any) {
      showToast('error', `握手测试失败: ${err.message || err}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveTelegram = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!botToken.trim() || !botUserId.trim()) {
      showToast('error', '请输入完整的 Bot Token 与 Telegram 用户 ID');
      return;
    }
    setSavingTg(true);
    try {
      const cfg = await api.getConfig();
      cfg.telegram_bot_token = botToken.trim();
      cfg.telegram_user_id = botUserId.trim();
      const res = await api.saveConfig(cfg);
      if (res.success) {
        showToast('success', 'Telegram 凭据已保存，守护引擎正在建立长连接');
        setShowTgConfig(false);
        onRefresh();
      } else {
        showToast('error', res.message);
      }
    } catch (err: any) {
      showToast('error', `保存失败: ${err.message || err}`);
    } finally {
      setSavingTg(false);
    }
  };

  const isOnline = state?.online === true;
  const isOffline = state?.online === false;
  const tgConfigured = state?.telegram?.configured ?? false;
  const tgRunning = state?.telegram?.is_running ?? false;

  return (
    <div className="flex-1 h-full overflow-y-auto p-7 space-y-6">
      {/* 顶部标题区 */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">校园网守护中枢</h2>
            <span className="px-2 py-0.5 rounded-full bg-apple-green/10 border border-apple-green/20 text-apple-green text-[10px] font-mono font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-apple-green animate-pulse" />
              毫秒自愈链路活跃
            </span>
          </div>
          <p className="text-xs text-apple-textTertiary mt-0.5">
            掉线被动毫秒感知 · 无感重连自愈 · Telegram 手机全权远程接管
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="liquid-btn px-3 py-1.5 rounded-xl text-xs text-apple-textSecondary hover:text-white flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          刷新数据
        </button>
      </div>

      {/* 状态操作通知浮条 */}
      {toast && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center gap-2 animate-in fade-in duration-200 ${
            toast.type === 'success'
              ? 'bg-apple-green/10 text-apple-green border-apple-green/25'
              : 'bg-apple-coral/10 text-apple-coral border-apple-coral/25'
          }`}
        >
          {toast.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span className="font-medium">{toast.message}</span>
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* 双核心卡片布局：1. 网络自愈守护视窗  2. Telegram 手机远程控制中枢 */}
      {/* ------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* ================================================================= */}
        {/* 核心 1: 校园网自愈守护视窗 */}
        {/* ================================================================= */}
        <div className="liquid-card rounded-2xl p-6 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <span className="text-xs font-semibold text-white tracking-wide uppercase flex items-center gap-2">
              <Wifi className="w-4 h-4 text-apple-blue" />
              校园网链路守护
            </span>
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium border flex items-center gap-1.5 ${
                isOnline
                  ? 'bg-apple-green/15 text-apple-green border-apple-green/30 shadow-apple-glow-green/20 shadow-sm'
                  : isOffline
                  ? 'bg-apple-coral/15 text-apple-coral border-apple-coral/30 shadow-apple-glow-coral/20 shadow-sm'
                  : 'bg-apple-amber/15 text-apple-amber border-apple-amber/30'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isOnline ? 'bg-apple-green animate-pulse' : isOffline ? 'bg-apple-coral' : 'bg-apple-amber'
                }`}
              />
              {isOnline ? '网络畅通 · 持续守护' : isOffline ? '掉线自愈处理中' : '初始化探测'}
            </span>
          </div>

          {/* 核心指标展示 */}
          <div className="space-y-1">
            <div className="text-2xl font-bold tracking-tight text-white font-mono flex items-baseline gap-2">
              <span>{isOnline ? '已在线' : '离线中'}</span>
              <span className="text-xs font-normal text-apple-textTertiary">
                {state?.university_name} [{state?.auth_protocol}]
              </span>
            </div>
            <p className="text-xs text-apple-textSecondary truncate font-mono">
              认证账号: {state?.campus_account || '尚未配置认证学号'}
            </p>
          </div>

          {/* 链路参数网格 */}
          <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-white/[0.025] border border-white/[0.06] text-xs font-mono">
            <div className="space-y-1">
              <span className="text-[10px] text-apple-textTertiary flex items-center gap-1">
                <Radio className="w-3 h-3 text-apple-blue" /> Wi-Fi 信号
              </span>
              <p className="text-apple-textPrimary truncate">{state?.wifi || '未接入无线网'}</p>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-apple-textTertiary flex items-center gap-1">
                <Globe className="w-3 h-3 text-cyan-400" /> 本机 IP / 接口
              </span>
              <p className="text-apple-textPrimary truncate">{state?.ip || '未知 IP'}</p>
            </div>
            <div className="space-y-1 pt-2 border-t border-white/[0.04]">
              <span className="text-[10px] text-apple-textTertiary flex items-center gap-1">
                <Zap className="w-3 h-3 text-apple-green" /> 网关探测
              </span>
              <p className="text-apple-textPrimary truncate">
                {state?.gateway} ({state?.gateway_ok ? '畅通' : '响应中'})
              </p>
            </div>
            <div className="space-y-1 pt-2 border-t border-white/[0.04]">
              <span className="text-[10px] text-apple-textTertiary flex items-center gap-1">
                <Cpu className="w-3 h-3 text-purple-400" /> 物理网卡
              </span>
              <p className="text-apple-textPrimary truncate">{state?.active_interface || '默认物理网卡'}</p>
            </div>
          </div>

          {/* 实时探针动态行 */}
          <div className="pt-1 flex items-center justify-between text-[11px] text-apple-textTertiary">
            <span className="flex items-center gap-1.5 truncate max-w-[260px]">
              <Activity className="w-3.5 h-3.5 text-apple-green shrink-0" />
              {state?.last_event || '守护引擎正常运行'}
            </span>
            <span className="font-mono text-apple-textSecondary">被动探针</span>
          </div>
        </div>

        {/* ================================================================= */}
        {/* 核心 2: Telegram 手机远程控制中枢 */}
        {/* ================================================================= */}
        <div className="liquid-card rounded-2xl p-6 space-y-5 flex flex-col justify-between">
          <div className="space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <span className="text-xs font-semibold text-white tracking-wide uppercase flex items-center gap-2">
                <Send className="w-4 h-4 text-cyan-400" />
                Telegram 手机远程控制中枢
              </span>
              <span
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium border flex items-center gap-1.5 ${
                  tgRunning
                    ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30 shadow-apple-glow-blue/20'
                    : tgConfigured
                    ? 'bg-apple-amber/15 text-apple-amber border-apple-amber/30'
                    : 'bg-white/[0.05] text-apple-textTertiary border-white/[0.08]'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    tgRunning ? 'bg-cyan-400 animate-pulse' : tgConfigured ? 'bg-apple-amber' : 'bg-apple-textTertiary'
                  }`}
                />
                {tgRunning ? '手机监听在线' : tgConfigured ? 'Bot 启动中' : '未挂载'}
              </span>
            </div>

            {/* Telegram 状态与快速测试 */}
            <div className="p-4 rounded-xl bg-white/[0.025] border border-white/[0.06] space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-medium text-apple-textPrimary">已绑定移动设备</div>
                  <div className="text-[11px] text-apple-textTertiary font-mono mt-0.5">
                    User ID: {state?.telegram?.user_id || '未绑定（需在下方填入）'}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleTestTelegram}
                  disabled={!tgConfigured || !!actionLoading}
                  className="liquid-btn px-3 py-1.5 rounded-xl text-xs font-medium text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5 disabled:opacity-40"
                >
                  {actionLoading === 'test_tg' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  向手机发送测试握手
                </button>
              </div>

              {/* 常用手机指令速查 */}
              <div className="pt-2.5 border-t border-white/[0.05] space-y-1.5">
                <span className="text-[10px] text-apple-textTertiary uppercase tracking-wider">手机端常用控制指令</span>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                  <div className="p-1.5 rounded-lg bg-black/30 border border-white/[0.05] flex items-center justify-between">
                    <span className="text-cyan-400">/status</span>
                    <span className="text-[10px] text-apple-textTertiary">状态与按键面板</span>
                  </div>
                  <div className="p-1.5 rounded-lg bg-black/30 border border-white/[0.05] flex items-center justify-between">
                    <span className="text-apple-green">/reconnect</span>
                    <span className="text-[10px] text-apple-textTertiary">强制网络重连</span>
                  </div>
                  <div className="p-1.5 rounded-lg bg-black/30 border border-white/[0.05] flex items-center justify-between">
                    <span className="text-apple-blue">/auth</span>
                    <span className="text-[10px] text-apple-textTertiary">重新认证上线</span>
                  </div>
                  <div className="p-1.5 rounded-lg bg-black/30 border border-white/[0.05] flex items-center justify-between">
                    <span className="text-apple-coral">/logout</span>
                    <span className="text-[10px] text-apple-textTertiary">立即下线注销</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 快速配置抽屉折叠按钮 */}
            <div>
              <button
                type="button"
                onClick={() => setShowTgConfig(!showTgConfig)}
                className="w-full text-xs text-apple-textSecondary hover:text-white flex items-center justify-between py-1 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-400" />
                  {showTgConfig ? '收起 Telegram 凭据配置' : '展开/修改 Telegram 手机凭据'}
                </span>
                {showTgConfig ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {/* 展开的内嵌表单 */}
              {showTgConfig && (
                <form onSubmit={handleSaveTelegram} className="mt-3 p-4 rounded-xl bg-[#0e1017]/90 border border-white/[0.1] space-y-3 text-xs">
                  <div className="space-y-1">
                    <label className="text-[11px] text-apple-textSecondary">Bot Token (从 @BotFather 获取)</label>
                    <input
                      type="password"
                      required
                      placeholder="例如: 123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
                      value={botToken}
                      onChange={(e) => setBotToken(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-black/40 border border-white/[0.1] font-mono text-apple-textPrimary focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] text-apple-textSecondary">Telegram 用户 ID (从 @userinfobot 获取)</label>
                    <input
                      type="text"
                      required
                      placeholder="例如: 987654321"
                      value={botUserId}
                      onChange={(e) => setBotUserId(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-black/40 border border-white/[0.1] font-mono text-apple-textPrimary focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  <div className="pt-1 flex justify-end">
                    <button
                      type="submit"
                      disabled={savingTg}
                      className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium flex items-center gap-1 disabled:opacity-50"
                    >
                      {savingTg ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                      保存并挂载 Bot
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          <div className="pt-2 text-[11px] text-apple-textTertiary flex items-center justify-between">
            <span>双向长轮询通信</span>
            <span className="font-mono text-cyan-400">零代理 / 直连加密</span>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* 底部精炼核心控制胶囊群 */}
      {/* ------------------------------------------------------------------- */}
      <div className="pt-2 space-y-2.5">
        <div className="text-[11px] font-semibold text-apple-textTertiary uppercase tracking-wider font-mono">
          控制中枢指令
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* 重连 Wi-Fi */}
          <button
            onClick={() => handleAction('wifi', api.reconnectWifi)}
            disabled={!!actionLoading}
            className="liquid-btn p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'wifi' ? <Loader2 className="w-4 h-4 animate-spin text-apple-blue" /> : <Wifi className="w-4 h-4 text-apple-blue" />}
            <span>重连无线网</span>
          </button>

          {/* 校园网认证 */}
          <button
            onClick={() => handleAction('auth', api.authCampus)}
            disabled={!!actionLoading}
            className="liquid-btn p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'auth' ? <Loader2 className="w-4 h-4 animate-spin text-apple-green" /> : <KeyRound className="w-4 h-4 text-apple-green" />}
            <span>触发认证</span>
          </button>

          {/* 注销下线 */}
          <button
            onClick={() => handleAction('logout', api.logoutCampus)}
            disabled={!!actionLoading}
            className="liquid-btn p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'logout' ? <Loader2 className="w-4 h-4 animate-spin text-apple-coral" /> : <LogOut className="w-4 h-4 text-apple-coral" />}
            <span>注销下线</span>
          </button>

          {/* 托盘后台静默常驻 */}
          <button
            onClick={() => api.minimize()}
            className="liquid-btn p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98]"
          >
            <Minimize2 className="w-4 h-4 text-apple-textTertiary" />
            <span>静默后台常驻</span>
          </button>
        </div>
      </div>
    </div>
  );
};
