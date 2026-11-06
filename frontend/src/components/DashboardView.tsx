import React, { useState } from 'react';
import {
  Sparkles,
  Wifi,
  KeyRound,
  LogOut,
  Camera,
  Lock,
  Minimize2,
  RefreshCw,
  Battery,
  BatteryCharging,
  Cpu,
  Activity,
  HardDrive,
  Globe,
  Radio,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { StateData, api } from '../api';

interface DashboardViewProps {
  state: StateData | null;
  onRefresh: () => void;
  onOpenQuickSetup: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ state, onRefresh, onOpenQuickSetup }) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  };

  const handleAction = async (name: string, fn: () => Promise<any>) => {
    setActionLoading(name);
    try {
      const res = await fn();
      if (res && res.success !== undefined) {
        showToast(res.success ? 'success' : 'error', res.message || '操作已完成');
      } else {
        showToast('success', '指令已发送');
      }
      onRefresh();
    } catch (err: any) {
      showToast('error', `操作失败: ${err.message || err}`);
    } finally {
      setActionLoading(null);
    }
  };

  const isOnline = state?.online === true;
  const isOffline = state?.online === false;
  const batPct = state?.battery?.percent ?? 100;
  const batPlugged = state?.battery?.plugged ?? true;

  // 格式化运行时间
  const uptimeSec = state?.system?.uptime_seconds ?? 0;
  const upHours = Math.floor(uptimeSec / 3600);
  const upMins = Math.floor((uptimeSec % 3600) / 60);

  return (
    <div className="flex-1 h-full overflow-y-auto p-6 space-y-6">
      {/* 顶部标题与快速刷新 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">控制中心概览</h2>
          <p className="text-xs text-apple-textTertiary">实时监控网络链路、供电健康与后台守护状态</p>
        </div>
        <button
          onClick={onRefresh}
          className="px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs text-apple-textSecondary hover:text-white flex items-center gap-1.5 transition-all"
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
              ? 'bg-apple-green/10 text-apple-green border-apple-green/20'
              : 'bg-apple-coral/10 text-apple-coral border-apple-coral/20'
          }`}
        >
          {toast.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* 小白一键打通醒目卡片 (Smart Onboarding Banner) */}
      {/* ------------------------------------------------------------------- */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-apple-card to-apple-sidebar border border-white/[0.09] p-5 shadow-apple-card flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-apple-blue/15 border border-apple-blue/20 flex items-center justify-center text-apple-blue shadow-apple-glow-blue/20 shadow-md shrink-0">
            <Sparkles className="w-6 h-6 stroke-[2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">小白一键智能打通</h3>
              <span className="px-2 py-0.5 rounded-full bg-apple-blue/20 text-apple-blue text-[10px] font-medium">
                推荐新同学
              </span>
            </div>
            <p className="text-xs text-apple-textSecondary mt-0.5">
              连入校园 Wi-Fi 即可自动拦截 302 重定向并推断所属高校，输入学号密码瞬间打通！
            </p>
          </div>
        </div>

        <button
          onClick={onOpenQuickSetup}
          className="px-4 py-2.5 rounded-xl bg-apple-blue hover:bg-apple-blueHover text-white text-xs font-medium shadow-apple-glow-blue/30 shadow-lg flex items-center gap-2 shrink-0 transition-all active:scale-[0.98]"
        >
          <Sparkles className="w-4 h-4" />
          一键极速打通
        </button>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* 2×2 苹果 Squircle 状态卡片网格 */}
      {/* ------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 卡片 1: 网络状态 */}
        <div className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-apple-textSecondary flex items-center gap-2">
              <Wifi className="w-4 h-4 text-apple-blue" />
              网络连接
            </span>
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium border flex items-center gap-1.5 ${
                isOnline
                  ? 'bg-apple-green/10 text-apple-green border-apple-green/20'
                  : isOffline
                  ? 'bg-apple-coral/10 text-apple-coral border-apple-coral/20'
                  : 'bg-apple-amber/10 text-apple-amber border-apple-amber/20'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-apple-green' : isOffline ? 'bg-apple-coral' : 'bg-apple-amber'}`} />
              {isOnline ? (state?.is_campus ? '校园网认证通过' : '家庭免认证环境') : isOffline ? '网络已断开' : '等待检测'}
            </span>
          </div>

          <div>
            <div className={`text-2xl font-bold tracking-tight ${isOnline ? 'text-apple-green' : isOffline ? 'text-apple-coral' : 'text-white'}`}>
              {isOnline ? '已稳定在线' : isOffline ? '当前离线' : '探测就绪中'}
            </div>
            <div className="text-xs text-apple-textTertiary mt-0.5">
              {state?.university_name} · [{state?.auth_protocol}]
            </div>
          </div>

          <div className="pt-2 border-t border-white/[0.06] grid grid-cols-2 gap-2 text-xs">
            <div className="space-y-0.5">
              <span className="text-[11px] text-apple-textTertiary flex items-center gap-1">
                <Radio className="w-3 h-3" /> Wi-Fi 信号
              </span>
              <p className="text-apple-textPrimary font-mono truncate">{state?.wifi || '未连接无线网'}</p>
            </div>
            <div className="space-y-0.5">
              <span className="text-[11px] text-apple-textTertiary flex items-center gap-1">
                <Globe className="w-3 h-3" /> 本机 IP
              </span>
              <p className="text-apple-textPrimary font-mono truncate">{state?.ip || '未知 IP'}</p>
            </div>
          </div>
        </div>

        {/* 卡片 2: 电源与电量 */}
        <div className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-apple-textSecondary flex items-center gap-2">
              <Battery className="w-4 h-4 text-apple-amber" />
              电源与电量
            </span>
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium border flex items-center gap-1.5 ${
                batPlugged
                  ? 'bg-apple-blue/10 text-apple-blue border-apple-blue/20'
                  : batPct <= 20
                  ? 'bg-apple-coral/10 text-apple-coral border-apple-coral/20'
                  : 'bg-apple-amber/10 text-apple-amber border-apple-amber/20'
              }`}
            >
              <BatteryCharging className="w-3 h-3" />
              {batPlugged ? '交流供电' : '电池供电'}
            </span>
          </div>

          <div>
            <div className="text-2xl font-bold tracking-tight text-white font-mono flex items-baseline gap-2">
              <span>{batPct}%</span>
              <span className="text-xs font-normal text-apple-textTertiary">{state?.battery?.status_text}</span>
            </div>
          </div>

          {/* 苹果风平滑进度条 */}
          <div className="w-full h-2 rounded-full bg-white/[0.06] overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                batPlugged
                  ? 'bg-apple-blue shadow-apple-glow-blue'
                  : batPct <= 20
                  ? 'bg-apple-coral shadow-apple-glow-coral'
                  : batPct <= 50
                  ? 'bg-apple-amber shadow-apple-glow-amber'
                  : 'bg-apple-green shadow-apple-glow-green'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, batPct))}%` }}
            />
          </div>

          <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-xs text-apple-textTertiary">
            <span>低电量守护</span>
            <span className="text-apple-textSecondary font-medium">断电 20% 安全倒计时关机</span>
          </div>
        </div>

        {/* 卡片 3: 系统与运行 */}
        <div className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-apple-textSecondary flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-400" />
              守护引擎指标
            </span>
            <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-apple-green/10 text-apple-green border border-apple-green/20">
              运行平稳
            </span>
          </div>

          <div>
            <div className="text-2xl font-bold tracking-tight text-white font-mono">
              {upHours}h {upMins.toString().padStart(2, '0')}m
            </div>
            <div className="text-xs text-apple-textTertiary mt-0.5">连续安全挂机时长</div>
          </div>

          <div className="pt-2 border-t border-white/[0.06] grid grid-cols-2 gap-2 text-xs">
            <div className="space-y-0.5">
              <span className="text-[11px] text-apple-textTertiary flex items-center gap-1">
                <HardDrive className="w-3 h-3" /> C盘可用空间
              </span>
              <p className="text-apple-textPrimary font-mono">{state?.system?.disk_free_gb ?? '--'} GB</p>
            </div>
            <div className="space-y-0.5">
              <span className="text-[11px] text-apple-textTertiary flex items-center gap-1">
                <Activity className="w-3 h-3" /> 常驻内存占用
              </span>
              <p className="text-apple-textPrimary font-mono">{state?.system?.memory ?? '--'}</p>
            </div>
          </div>
        </div>

        {/* 卡片 4: 守护动态事件 */}
        <div className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-apple-textSecondary flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              最新守护动态
            </span>
            <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-white/[0.04] text-apple-textSecondary border border-white/[0.08]">
              持续监听
            </span>
          </div>

          <div>
            <div className="text-xs text-apple-textSecondary font-mono">
              网关探测: {state?.gateway_ok ? '畅通' : '超时'} · {state?.gateway}
            </div>
            <p className="text-xs text-apple-textPrimary mt-1.5 line-clamp-2 leading-relaxed">
              {state?.last_event || '等待事件触发...'}
            </p>
          </div>

          <div className="pt-2 border-t border-white/[0.06] text-[11px] text-apple-textTertiary flex items-center justify-between">
            <span>物理接口</span>
            <span className="font-mono text-apple-textSecondary truncate max-w-[200px]">
              {state?.active_interface || '以太网 / 无线网卡'}
            </span>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* 结构化快捷操作群 */}
      {/* ------------------------------------------------------------------- */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-semibold text-apple-textSecondary uppercase tracking-wider">快捷控制中心</h4>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
          {/* 重连 Wi-Fi */}
          <button
            onClick={() => handleAction('wifi', api.reconnectWifi)}
            disabled={!!actionLoading}
            className="p-3 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] flex flex-col items-center justify-center gap-2 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'wifi' ? <Loader2 className="w-4 h-4 animate-spin text-apple-blue" /> : <Wifi className="w-4 h-4 text-apple-blue" />}
            <span>重连 Wi-Fi</span>
          </button>

          {/* 校园网认证 */}
          <button
            onClick={() => handleAction('auth', api.authCampus)}
            disabled={!!actionLoading}
            className="p-3 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] flex flex-col items-center justify-center gap-2 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'auth' ? <Loader2 className="w-4 h-4 animate-spin text-apple-green" /> : <KeyRound className="w-4 h-4 text-apple-green" />}
            <span>校园网认证</span>
          </button>

          {/* 注销下线 */}
          <button
            onClick={() => handleAction('logout', api.logoutCampus)}
            disabled={!!actionLoading}
            className="p-3 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] flex flex-col items-center justify-center gap-2 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'logout' ? <Loader2 className="w-4 h-4 animate-spin text-apple-coral" /> : <LogOut className="w-4 h-4 text-apple-coral" />}
            <span>注销下线</span>
          </button>

          {/* 截取屏幕 */}
          <button
            onClick={() => handleAction('screenshot', api.takeScreenshot)}
            disabled={!!actionLoading}
            className="p-3 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] flex flex-col items-center justify-center gap-2 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'screenshot' ? <Loader2 className="w-4 h-4 animate-spin text-cyan-400" /> : <Camera className="w-4 h-4 text-cyan-400" />}
            <span>截取桌面</span>
          </button>

          {/* 锁定屏幕 */}
          <button
            onClick={() => handleAction('lock', api.lockScreen)}
            disabled={!!actionLoading}
            className="p-3 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] flex flex-col items-center justify-center gap-2 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'lock' ? <Loader2 className="w-4 h-4 animate-spin text-purple-400" /> : <Lock className="w-4 h-4 text-purple-400" />}
            <span>锁定电脑</span>
          </button>

          {/* 最小化后台 */}
          <button
            onClick={() => api.minimize()}
            className="p-3 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] flex flex-col items-center justify-center gap-2 text-xs font-medium text-apple-textPrimary transition-all active:scale-[0.98]"
          >
            <Minimize2 className="w-4 h-4 text-apple-textTertiary" />
            <span>托盘常驻</span>
          </button>
        </div>
      </div>
    </div>
  );
};
