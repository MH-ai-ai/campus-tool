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
  Battery,
  BatteryCharging,
  Power,
  Eye,
  EyeOff,
  Sparkles,
} from 'lucide-react';
import { StateData, api } from '../api';

interface DashboardViewProps {
  state: StateData | null;
  onRefresh: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ state, onRefresh }) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // 首屏快速凭据输入
  const [inputAccount, setInputAccount] = useState('');
  const [inputPassword, setInputPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [quickConnecting, setQuickConnecting] = useState(false);

  // Telegram 配置抽屉
  const [showTgConfig, setShowTgConfig] = useState(false);
  const [botToken, setBotToken] = useState('');
  const [botUserId, setBotUserId] = useState('');
  const [savingTg, setSavingTg] = useState(false);

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 4000);
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

  // 首屏一键自动探测并联网
  const handleQuickConnect = async () => {
    setQuickConnecting(true);
    try {
      const res = await api.quickConnect(inputAccount.trim(), inputPassword.trim());
      if (res.success) {
        const detectedName = res.detected?.university_name || '';
        const detectedProto = res.detected?.auth_protocol ? `[${res.detected.auth_protocol.toUpperCase()}]` : '';
        const extra = detectedName ? ` (自动识别: ${detectedName} ${detectedProto})` : '';
        showToast('success', `${res.message}${extra}，已加密持久化存储`);
        onRefresh();
      } else {
        showToast('error', res.message || '一键联网失败');
      }
    } catch (err: any) {
      showToast('error', `一键联网异常: ${err.message || err}`);
    } finally {
      setQuickConnecting(false);
    }
  };

  // Telegram 握手测试
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

  // Telegram 保存凭据
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
        showToast('success', 'Telegram 凭据已持久化加密保存，手机远程服务已挂载');
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
  const hasAccount = !!state?.campus_account;
  const tgConfigured = state?.telegram?.configured ?? false;
  const tgRunning = state?.telegram?.is_running ?? false;

  const battery = state?.battery;
  const isCharging = battery?.plugged ?? true;
  const batteryPct = battery?.percent ?? 100;

  return (
    <div className="flex-1 h-full overflow-y-auto p-7 space-y-6">
      {/* 顶部标题区 */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl font-bold tracking-tight text-white drop-shadow-sm">Campus Guard 守护中枢</h2>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-400/20 border border-emerald-400/40 text-emerald-200 text-[10px] font-mono font-medium flex items-center gap-1.5 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              毫秒自愈链路活跃
            </span>
          </div>
          <p className="text-xs text-white/70 mt-1">
            网络毫秒级断网自愈 · 恢复后自动推送 Telegram · 手机查电量与远程关机
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="twilight-btn-secondary px-3.5 py-1.5 rounded-xl text-xs text-white/90 hover:text-white flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          刷新数据
        </button>
      </div>

      {/* 状态操作通知浮条 */}
      {toast && (
        <div
          className={`p-3.5 rounded-2xl border text-xs flex items-center gap-2.5 animate-in fade-in duration-200 shadow-lg ${
            toast.type === 'success'
              ? 'bg-emerald-500/20 text-emerald-100 border-emerald-400/40 backdrop-blur-md'
              : 'bg-rose-500/20 text-rose-100 border-rose-400/40 backdrop-blur-md'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-300 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-300 shrink-0" />
          )}
          <span className="font-medium">{toast.message}</span>
        </div>
      )}

      {/* =================================================================== */}
      {/* 核心 1: 首屏一键联网与凭据自动识别卡片 */}
      {/* =================================================================== */}
      {!hasAccount ? (
        <div className="twilight-glass-card rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/20">
            <span className="text-xs font-semibold text-white tracking-wide uppercase flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-pink-300" />
              首次快速配置 · 自动检测校园网类型并一键联网
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] bg-pink-500/20 border border-pink-400/40 text-pink-200 font-mono">
              本地安全加密持久化
            </span>
          </div>

          <p className="text-xs text-white/80">
            只需输入学号与密码，点击后将自动嗅探校园网类型（Dr.COM / 深澜 Srun / 锐捷 / Portal）并完成联网与永久保存。
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="space-y-1.5">
              <label className="text-white/80 font-medium">校园网学号 / 认证账号</label>
              <input
                type="text"
                placeholder="例如: 20240901001"
                value={inputAccount}
                onChange={(e) => setInputAccount(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-pink-400"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-white/80 font-medium">校园网认证密码</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="请输入认证密码"
                  value={inputPassword}
                  onChange={(e) => setInputPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-pink-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
          </div>

          <div className="pt-2">
            <button
              type="button"
              onClick={handleQuickConnect}
              disabled={quickConnecting || !inputAccount.trim() || !inputPassword.trim()}
              className="w-full twilight-btn-primary py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {quickConnecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  正在自动探测网关与校园网协议并执行登录...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-amber-300" />
                  自动检测校园网并一键联网
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* 已有配置时的醒目「一键极速联网」超级卡片 */
        <div className="twilight-glass-card rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between gap-5">
          <div className="space-y-2 text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2.5">
              <span className="text-sm font-semibold text-white tracking-wide uppercase flex items-center gap-2">
                <Wifi className="w-4 h-4 text-cyan-300" />
                校园网一键极速联网
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-[10px] font-medium border flex items-center gap-1.5 ${
                  isOnline
                    ? 'bg-emerald-500/20 text-emerald-200 border-emerald-400/40'
                    : 'bg-rose-500/20 text-rose-200 border-rose-400/40'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                  }`}
                />
                {isOnline ? '持续自愈守护中' : '未连接 · 待认证'}
              </span>
            </div>
            <p className="text-xs text-white/80 font-mono">
              当前账号: <span className="text-white font-semibold">{state?.campus_account}</span>
              <span className="text-white/50 ml-2">({state?.university_name} · {state?.auth_protocol})</span>
            </p>
            <p className="text-[11px] text-white/60">
              如遇网络异常，点击右侧按钮即可强制重新探测网关并无感重新上线。
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={handleQuickConnect}
              disabled={quickConnecting}
              className="twilight-btn-primary px-6 py-3.5 rounded-2xl text-xs font-bold text-white flex items-center gap-2.5 shadow-xl disabled:opacity-50"
            >
              {quickConnecting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4 text-amber-300" />
              )}
              <span>一键极速联网</span>
            </button>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* 双栏核心功能：左侧网络链路与电源透视 | 右侧 Telegram 手机控制中枢 */}
      {/* =================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 左侧：网络链路与电脑电量电源守护 */}
        <div className="space-y-5">
          {/* 网络链路参数卡片 */}
          <div className="twilight-glass-card rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/20">
              <span className="text-xs font-semibold text-white tracking-wide uppercase flex items-center gap-2">
                <Wifi className="w-4 h-4 text-cyan-300" />
                网络链路与网关自愈
              </span>
              <span className="text-[10px] text-white/60 font-mono">
                掉线探针: 每 2 秒
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-white/10 border border-white/20 text-xs font-mono">
              <div className="space-y-1">
                <span className="text-[10px] text-white/60 flex items-center gap-1">
                  <Radio className="w-3 h-3 text-cyan-300" /> Wi-Fi 信号
                </span>
                <p className="text-white font-medium truncate">{state?.wifi || '未接入无线网'}</p>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-white/60 flex items-center gap-1">
                  <Globe className="w-3 h-3 text-pink-300" /> 本机 IP
                </span>
                <p className="text-white font-medium truncate">{state?.ip || '获取中...'}</p>
              </div>
              <div className="space-y-1 pt-2 border-t border-white/10">
                <span className="text-[10px] text-white/60 flex items-center gap-1">
                  <Zap className="w-3 h-3 text-amber-300" /> 网关探测
                </span>
                <p className="text-white font-medium truncate">
                  {state?.gateway} ({state?.gateway_ok ? '畅通' : '响应中'})
                </p>
              </div>
              <div className="space-y-1 pt-2 border-t border-white/10">
                <span className="text-[10px] text-white/60 flex items-center gap-1">
                  <Cpu className="w-3 h-3 text-purple-300" /> 活动网卡
                </span>
                <p className="text-white font-medium truncate">{state?.active_interface || '默认物理网卡'}</p>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-white/70">
              <span className="flex items-center gap-1.5 truncate max-w-[280px]">
                <Activity className="w-3.5 h-3.5 text-emerald-300 shrink-0" />
                {state?.last_event || '网络引擎待命中'}
              </span>
              <span className="font-mono text-white/50 text-[10px]">掉线自动恢复</span>
            </div>
          </div>

          {/* 电脑电量与充电状态卡片 (满足手机端查电量/低电量提醒需求) */}
          <div className="twilight-glass-card rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/20">
              <span className="text-xs font-semibold text-white tracking-wide uppercase flex items-center gap-2">
                {isCharging ? (
                  <BatteryCharging className="w-4 h-4 text-emerald-300" />
                ) : (
                  <Battery className="w-4 h-4 text-amber-300" />
                )}
                电脑电量与电源守护
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-medium border flex items-center gap-1 ${
                  isCharging
                    ? 'bg-emerald-500/20 text-emerald-200 border-emerald-400/40'
                    : 'bg-amber-500/20 text-amber-200 border-amber-400/40'
                }`}
              >
                {isCharging ? '🔌 交流供电中 (正在充电)' : '🔋 电池供电中'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-xl bg-white/10 border border-white/20">
              <div>
                <div className="text-2xl font-bold font-mono text-white flex items-baseline gap-2">
                  <span>{batteryPct}%</span>
                  <span className="text-xs font-normal text-white/70">
                    {battery?.status_text || '正常供电'}
                  </span>
                </div>
                <div className="text-[11px] text-white/60 mt-1">
                  低电量规则：≤50%、≤30%、≤20% 自动向手机 Telegram 派发告警
                </div>
              </div>

              {/* 电量进度长条 */}
              <div className="w-24 h-3.5 bg-black/30 rounded-full overflow-hidden p-0.5 border border-white/20">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    batteryPct > 40
                      ? 'bg-gradient-to-r from-emerald-400 to-cyan-300'
                      : batteryPct > 20
                      ? 'bg-gradient-to-r from-amber-400 to-orange-400'
                      : 'bg-gradient-to-r from-rose-500 to-red-500 animate-pulse'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, batteryPct))}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* 右侧：Telegram 手机远程控制中枢 (全权手机操控 + 远程关机) */}
        <div className="twilight-glass-card rounded-2xl p-5 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/20">
              <span className="text-xs font-semibold text-white tracking-wide uppercase flex items-center gap-2">
                <Send className="w-4 h-4 text-cyan-300" />
                Telegram 手机远程指令中枢
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-[10px] font-medium border flex items-center gap-1.5 ${
                  tgRunning
                    ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400/40'
                    : tgConfigured
                    ? 'bg-amber-500/20 text-amber-200 border-amber-400/40'
                    : 'bg-white/10 text-white/50 border-white/20'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    tgRunning ? 'bg-cyan-300 animate-pulse' : tgConfigured ? 'bg-amber-300' : 'bg-white/40'
                  }`}
                />
                {tgRunning ? '手机监听在线' : tgConfigured ? 'Bot 就绪' : '待绑定'}
              </span>
            </div>

            {/* 设备绑定与握手测试 */}
            <div className="p-3.5 rounded-xl bg-white/10 border border-white/20 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-medium text-white">已授权手机端 User ID</div>
                  <div className="text-[11px] text-white/60 font-mono mt-0.5">
                    {state?.telegram?.user_id ? `ID: ${state.telegram.user_id}` : '未绑定用户 ID'}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleTestTelegram}
                  disabled={!tgConfigured || !!actionLoading}
                  className="twilight-btn-secondary px-3 py-1.5 rounded-xl text-xs font-medium text-cyan-200 hover:text-white flex items-center gap-1.5 disabled:opacity-40"
                >
                  {actionLoading === 'test_tg' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5 text-cyan-300" />
                  )}
                  发送测试握手
                </button>
              </div>

              {/* 核心指令卡片速查 */}
              <div className="pt-2 border-t border-white/15 space-y-1.5">
                <span className="text-[10px] text-white/60 uppercase tracking-wider">手机端核心控制指令速查</span>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2 rounded-xl bg-white/5 border border-white/15 flex items-center justify-between">
                    <span className="text-emerald-300 font-bold">/battery</span>
                    <span className="text-[10px] text-white/70">查电量与充电状态</span>
                  </div>
                  <div className="p-2 rounded-xl bg-white/5 border border-white/15 flex items-center justify-between">
                    <span className="text-cyan-300 font-bold">/status</span>
                    <span className="text-[10px] text-white/70">查看网络与系统全景</span>
                  </div>
                  <div className="p-2 rounded-xl bg-white/5 border border-white/15 flex items-center justify-between">
                    <span className="text-pink-300 font-bold">/reconnect</span>
                    <span className="text-[10px] text-white/70">远程重连校园网</span>
                  </div>
                  <div className="p-2 rounded-xl bg-white/5 border border-white/15 flex items-center justify-between">
                    <span className="text-rose-400 font-bold">/shutdown</span>
                    <span className="text-[10px] text-white/70">远程关机电脑</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 快速配置凭据折叠面板 */}
            <div>
              <button
                type="button"
                onClick={() => setShowTgConfig(!showTgConfig)}
                className="w-full text-xs text-white/70 hover:text-white flex items-center justify-between py-1 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-300" />
                  {showTgConfig ? '收起 Telegram 凭据配置' : '展开 / 修改 Telegram 手机凭据'}
                </span>
                {showTgConfig ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showTgConfig && (
                <form
                  onSubmit={handleSaveTelegram}
                  className="mt-3 p-4 rounded-xl bg-white/15 border border-white/25 space-y-3 text-xs"
                >
                  <div className="space-y-1">
                    <label className="text-[11px] text-white/80">Bot Token (从 Telegram @BotFather 获取)</label>
                    <input
                      type="password"
                      required
                      placeholder="123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
                      value={botToken}
                      onChange={(e) => setBotToken(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-black/30 border border-white/20 font-mono text-white placeholder-white/30 focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] text-white/80">Telegram 用户 ID (从 @userinfobot 获取)</label>
                    <input
                      type="text"
                      required
                      placeholder="例如: 987654321"
                      value={botUserId}
                      onChange={(e) => setBotUserId(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-black/30 border border-white/20 font-mono text-white placeholder-white/30 focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  <div className="pt-1 flex justify-end">
                    <button
                      type="submit"
                      disabled={savingTg}
                      className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-90 text-white font-medium flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {savingTg ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                      保存并启动 Bot
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          <div className="pt-2 text-[11px] text-white/60 flex items-center justify-between">
            <span>双向断网消息缓冲</span>
            <span className="font-mono text-cyan-200">自愈后自动推送至手机</span>
          </div>
        </div>
      </div>

      {/* =================================================================== */}
      {/* 底部操作快捷胶囊按钮 */}
      {/* =================================================================== */}
      <div className="pt-2 space-y-2.5">
        <div className="text-[11px] font-semibold text-white/60 uppercase tracking-wider font-mono">
          本地控制中枢
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* 重连 Wi-Fi */}
          <button
            onClick={() => handleAction('wifi', api.reconnectWifi)}
            disabled={!!actionLoading}
            className="twilight-btn-secondary p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-white transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'wifi' ? (
              <Loader2 className="w-4 h-4 animate-spin text-cyan-300" />
            ) : (
              <Wifi className="w-4 h-4 text-cyan-300" />
            )}
            <span>重连无线网</span>
          </button>

          {/* 触发认证 */}
          <button
            onClick={() => handleAction('auth', api.authCampus)}
            disabled={!!actionLoading}
            className="twilight-btn-secondary p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-white transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'auth' ? (
              <Loader2 className="w-4 h-4 animate-spin text-emerald-300" />
            ) : (
              <KeyRound className="w-4 h-4 text-emerald-300" />
            )}
            <span>触发认证</span>
          </button>

          {/* 注销下线 */}
          <button
            onClick={() => handleAction('logout', api.logoutCampus)}
            disabled={!!actionLoading}
            className="twilight-btn-secondary p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-white transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {actionLoading === 'logout' ? (
              <Loader2 className="w-4 h-4 animate-spin text-rose-300" />
            ) : (
              <LogOut className="w-4 h-4 text-rose-300" />
            )}
            <span>注销下线</span>
          </button>

          {/* 托盘后台静默常驻 */}
          <button
            onClick={() => api.minimize()}
            className="twilight-btn-secondary p-3.5 rounded-2xl flex items-center justify-center gap-2.5 text-xs font-medium text-white transition-all active:scale-[0.98]"
          >
            <Minimize2 className="w-4 h-4 text-white/70" />
            <span>静默后台常驻</span>
          </button>
        </div>
      </div>
    </div>
  );
};
