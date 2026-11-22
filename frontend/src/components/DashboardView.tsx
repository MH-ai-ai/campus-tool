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
  Loader2,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Cpu,
  ShieldCheck,
  Zap,
  Battery,
  BatteryCharging,
  Eye,
  EyeOff,
  Sparkles,
} from 'lucide-react';
import { StateData, api } from '../api';
import { useToast } from './ToastContext';

interface DashboardViewProps {
  state: StateData | null;
  onRefresh: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ state, onRefresh }) => {
  const toast = useToast();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

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

  const handleAction = async (name: string, fn: () => Promise<any>) => {
    setActionLoading(name);
    try {
      const res = await fn();
      if (res && res.success !== undefined) {
        if (res.success) {
          toast.success(res.message || '指令执行完毕');
        } else {
          toast.error(res.message || '指令执行失败');
        }
      } else {
        toast.info('指令已下发');
      }
      onRefresh();
    } catch (err: any) {
      toast.error(`操作异常: ${err?.message || err}`);
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
        const extra = detectedName ? `（自动识别: ${detectedName} ${detectedProto}）` : '';
        toast.success(`${res.message}${extra}`);
        onRefresh();
      } else {
        toast.error(res.message || '一键联网失败');
      }
    } catch (err: any) {
      toast.error(`一键联网异常: ${err?.message || err}`);
    } finally {
      setQuickConnecting(false);
    }
  };

  // Telegram 握手测试
  const handleTestTelegram = async () => {
    setActionLoading('test_tg');
    try {
      const res = await api.testTelegramBot();
      if (res.success) {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch (err: any) {
      toast.error(`握手测试失败: ${err?.message || err}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Telegram 保存凭据
  const handleSaveTelegram = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!botToken.trim() || !botUserId.trim()) {
      toast.error('请输入完整的 Bot Token 与 Telegram 用户 ID');
      return;
    }
    setSavingTg(true);
    try {
      const cfg = await api.getConfig();
      cfg.telegram_bot_token = botToken.trim();
      cfg.telegram_user_id = parseInt(botUserId.trim(), 10) || 0;
      const res = await api.saveConfig(cfg);
      if (res.success) {
        toast.success('Telegram 凭据已加密保存，正在后台自动挂载 Bot...');
        setShowTgConfig(false);
        onRefresh();
        setTimeout(() => onRefresh(), 2000);
      } else {
        toast.error(res.message);
      }
    } catch (err: any) {
      toast.error(`保存失败: ${err?.message || err}`);
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
    <div className="flex-1 h-full flex flex-col overflow-hidden">
      {/* 顶部固定玻璃页头 */}
      <header className="shrink-0 ios-glass-header px-6 pt-5 pb-4 flex items-center justify-between gap-4 z-20">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-lg font-bold tracking-tight text-ink-primary">安澜 · 守护中枢</h2>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border inline-flex items-center gap-1.5 whitespace-nowrap ${
                isOnline
                  ? 'bg-[#1f7a53]/10 border-[#1f7a53]/25 text-[#1f7a53]'
                  : isOffline
                  ? 'bg-[#b43a40]/10 border-[#b43a40]/25 text-[#b43a40]'
                  : 'bg-[#b47319]/10 border-[#b47319]/25 text-[#9a5b13]'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isOnline ? 'bg-[#2a9d6c]' : isOffline ? 'bg-[#cf4d54]' : 'bg-[#cf8a27]'
                }`}
              />
              {isOnline ? '自愈链路在线' : isOffline ? '离线自愈中' : '探针就绪'}
            </span>
          </div>
          <p className="text-xs text-ink-secondary mt-0.5 truncate">
            断网自动重连与校园网认证 · 状态变化即时推送 · 远程查电量与控制
          </p>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          className="ios-btn-secondary h-8 px-3 rounded-lg text-xs font-medium text-ink-primary whitespace-nowrap shrink-0 inline-flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5 text-ink-secondary" />
          <span>刷新数据</span>
        </button>
      </header>

      {/* 可滚动主内容区 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* =================================================================== */}
        {/* 核心 1: 一键联网与凭据快速配置卡片 */}
        {/* =================================================================== */}
        {!hasAccount ? (
          <div className="ios-glass-card rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#142033]/[0.07]">
              <span className="text-xs font-semibold text-ink-primary flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#2b5797]" />
                首次快速配置 · 自动识别校园网并一键联网
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] bg-[#2b5797]/10 border border-[#2b5797]/20 text-[#2b5797] font-medium whitespace-nowrap">
                本地加密存储
              </span>
            </div>

            <p className="text-xs text-ink-secondary">
              只需输入学号与密码，系统将自动嗅探校园网认证协议（Dr.COM / 深澜 Srun / 锐捷 / Portal）并完成持久化保存。
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-ink-secondary font-medium">校园网学号 / 认证账号</label>
                <input
                  type="text"
                  placeholder="例如: 20240901001"
                  value={inputAccount}
                  onChange={(e) => setInputAccount(e.target.value)}
                  className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-ink-secondary font-medium">校园网认证密码</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="请输入认证密码"
                    value={inputPassword}
                    onChange={(e) => setInputPassword(e.target.value)}
                    className="ios-input w-full px-3.5 py-2 pr-10 rounded-xl text-xs font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? '隐藏密码' : '显示密码'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-tertiary hover:text-ink-primary"
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="pt-1">
              <button
                type="button"
                onClick={handleQuickConnect}
                disabled={quickConnecting || !inputAccount.trim() || !inputPassword.trim()}
                className="w-full ios-btn-primary py-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {quickConnecting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    正在自动探测网关并执行登录...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    自动检测校园网并一键联网
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="ios-glass-card rounded-2xl p-5 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="space-y-1.5 text-center md:text-left min-w-0">
              <div className="flex items-center justify-center md:justify-start gap-2.5 flex-wrap">
                <span className="text-sm font-semibold text-ink-primary flex items-center gap-2">
                  <Wifi className="w-4 h-4 text-[#2b5797]" />
                  校园网一键极速联网
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border inline-flex items-center gap-1.5 ${
                    isOnline
                      ? 'bg-[#1f7a53]/10 text-[#1f7a53] border-[#1f7a53]/25'
                      : 'bg-[#b43a40]/10 text-[#b43a40] border-[#b43a40]/25'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-[#2a9d6c]' : 'bg-[#cf4d54]'}`} />
                  {isOnline ? '持续自愈守护中' : '未连接 · 待认证'}
                </span>
              </div>
              <p className="text-xs text-ink-secondary font-mono truncate">
                当前账号：<span className="text-ink-primary font-semibold">{state?.campus_account}</span>
                <span className="text-ink-tertiary ml-2">
                  ({state?.university_name} · {state?.auth_protocol})
                </span>
              </p>
              <p className="text-[11px] text-ink-tertiary">
                若发生异常断网或网关切换，点击右侧按钮可立即拉起 Wi-Fi 并重新探测认证。
              </p>
            </div>

            <div className="shrink-0">
              <button
                type="button"
                onClick={handleQuickConnect}
                disabled={quickConnecting}
                className="ios-btn-primary px-5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap inline-flex items-center gap-2 disabled:opacity-50"
              >
                {quickConnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                <span>一键极速联网</span>
              </button>
            </div>
          </div>
        )}

        {/* =================================================================== */}
        {/* 双栏核心功能：左侧网络与电源 | 右侧 Telegram 手机控制中枢 */}
        {/* =================================================================== */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* 左侧：网络链路与电脑电量 */}
          <div className="space-y-4">
            {/* 网络链路参数卡片 */}
            <div className="ios-glass-card rounded-2xl p-5 space-y-3.5">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#142033]/[0.07]">
                <span className="text-xs font-semibold text-ink-primary flex items-center gap-2">
                  <Wifi className="w-4 h-4 text-[#2b5797]" />
                  网络链路与网关自愈
                </span>
                <span className="text-[11px] text-ink-tertiary font-mono">掉线自动恢复</span>
              </div>

              <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl ios-glass-inset text-xs font-mono">
                <div className="space-y-1 min-w-0">
                  <span className="text-[11px] font-sans text-ink-tertiary flex items-center gap-1">
                    <Radio className="w-3 h-3 text-[#2b5797]" /> Wi-Fi 信号
                  </span>
                  <p className="text-ink-primary font-medium truncate">{state?.wifi || '未接入无线网'}</p>
                </div>
                <div className="space-y-1 min-w-0">
                  <span className="text-[11px] font-sans text-ink-tertiary flex items-center gap-1">
                    <Globe className="w-3 h-3 text-[#2b5797]" /> 本机 IP
                  </span>
                  <p className="text-ink-primary font-medium truncate">{state?.ip || '获取中...'}</p>
                </div>
                <div className="space-y-1 pt-2.5 border-t border-[#142033]/[0.06] min-w-0">
                  <span className="text-[11px] font-sans text-ink-tertiary flex items-center gap-1">
                    <Zap className="w-3 h-3 text-[#9a5b13]" /> 网关探测
                  </span>
                  <p className="text-ink-primary font-medium truncate">
                    {state?.gateway} ({state?.gateway_ok ? '畅通' : '响应中'})
                  </p>
                </div>
                <div className="space-y-1 pt-2.5 border-t border-[#142033]/[0.06] min-w-0">
                  <span className="text-[11px] font-sans text-ink-tertiary flex items-center gap-1">
                    <Cpu className="w-3 h-3 text-ink-secondary" /> 活动网卡
                  </span>
                  <p className="text-ink-primary font-medium truncate">{state?.active_interface || '默认物理网卡'}</p>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-ink-secondary gap-2">
                <span className="flex items-center gap-1.5 min-w-0 truncate">
                  <Activity className="w-3.5 h-3.5 text-[#1f7a53] shrink-0" />
                  <span className="truncate">{state?.last_event || '网络引擎待命中'}</span>
                </span>
              </div>
            </div>

            {/* 电脑电量与电源守护卡片 */}
            <div className="ios-glass-card rounded-2xl p-5 space-y-3.5">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#142033]/[0.07]">
                <span className="text-xs font-semibold text-ink-primary flex items-center gap-2">
                  {isCharging ? (
                    <BatteryCharging className="w-4 h-4 text-[#1f7a53]" />
                  ) : (
                    <Battery className="w-4 h-4 text-[#9a5b13]" />
                  )}
                  电脑电量与电源守护
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border whitespace-nowrap ${
                    isCharging
                      ? 'bg-[#1f7a53]/10 text-[#1f7a53] border-[#1f7a53]/25'
                      : 'bg-[#b47319]/10 text-[#9a5b13] border-[#b47319]/25'
                  }`}
                >
                  {isCharging ? '交流供电中' : '电池供电中'}
                </span>
              </div>

              <div className="flex items-center justify-between gap-4 p-3.5 rounded-xl ios-glass-inset">
                <div className="min-w-0">
                  <div className="text-2xl font-bold font-mono text-ink-primary flex items-baseline gap-2">
                    <span>{batteryPct}%</span>
                    <span className="text-xs font-sans font-normal text-ink-secondary truncate">
                      {battery?.status_text || '正常供电'}
                    </span>
                  </div>
                  <div className="text-[11px] text-ink-tertiary mt-1">
                    低电量梯次提醒：≤50%、≤30%、≤20% 自动推送告警
                  </div>
                </div>

                {/* 克制清晰进度条 */}
                <div className="w-24 h-2.5 bg-[#142033]/10 rounded-full overflow-hidden shrink-0">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      batteryPct > 40
                        ? 'bg-[#2a9d6c]'
                        : batteryPct > 20
                        ? 'bg-[#cf8a27]'
                        : 'bg-[#cf4d54]'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, batteryPct))}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* 右侧：Telegram 手机远程控制中枢 */}
          <div className="ios-glass-card rounded-2xl p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3.5">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#142033]/[0.07]">
                <span className="text-xs font-semibold text-ink-primary flex items-center gap-2">
                  <Send className="w-4 h-4 text-[#2b5797]" />
                  Telegram 手机远程中枢
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border inline-flex items-center gap-1.5 whitespace-nowrap ${
                    tgRunning
                      ? 'bg-[#2b5797]/10 text-[#2b5797] border-[#2b5797]/25'
                      : tgConfigured
                      ? 'bg-[#b47319]/10 text-[#9a5b13] border-[#b47319]/25'
                      : 'bg-[#142033]/[0.05] text-ink-tertiary border-[#142033]/10'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      tgRunning ? 'bg-[#2b5797]' : tgConfigured ? 'bg-[#cf8a27]' : 'bg-ink-tertiary/50'
                    }`}
                  />
                  {tgRunning ? '监听在线' : tgConfigured ? 'Bot 就绪' : '待绑定'}
                </span>
              </div>

              {/* 绑定与握手测试 */}
              <div className="p-3.5 rounded-xl ios-glass-inset space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-ink-primary">已授权手机端 User ID</div>
                    <div className="text-[11px] text-ink-tertiary font-mono mt-0.5 truncate">
                      {state?.telegram?.user_id ? `ID: ${state.telegram.user_id}` : '未绑定用户 ID'}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleTestTelegram}
                    disabled={!tgConfigured || !!actionLoading}
                    className="ios-btn-secondary h-8 px-3 rounded-lg text-xs font-medium text-[#2b5797] whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 disabled:opacity-40"
                  >
                    {actionLoading === 'test_tg' ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                    <span>发送测试握手</span>
                  </button>
                </div>

                {/* 指令速查网格 */}
                <div className="pt-2.5 border-t border-[#142033]/[0.06] space-y-2">
                  <span className="text-[11px] text-ink-tertiary font-medium">手机端常用指令速查</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {[
                      { cmd: '/boost', desc: '嗅探并自愈联网', tone: 'text-[#2b5797]' },
                      { cmd: '/status', desc: '网络与系统全景', tone: 'text-[#2b5797]' },
                      { cmd: '/reconnect', desc: '强制重连校园网', tone: 'text-[#1f7a53]' },
                      { cmd: '/battery', desc: '查电量与供电状态', tone: 'text-[#1f7a53]' },
                      { cmd: '/network', desc: '实时链路明细', tone: 'text-ink-primary' },
                      { cmd: '/shutdown', desc: '远程安全关机', tone: 'text-[#b43a40]' },
                    ].map((item) => (
                      <div
                        key={item.cmd}
                        className="px-2.5 py-1.5 rounded-lg bg-white/70 border border-[#142033]/[0.06] flex items-center justify-between gap-2 min-w-0"
                      >
                        <span className={`font-mono font-semibold text-[11px] shrink-0 ${item.tone}`}>
                          {item.cmd}
                        </span>
                        <span className="text-[11px] text-ink-secondary truncate">{item.desc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* 凭据折叠配置 */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowTgConfig(!showTgConfig)}
                  className="w-full text-xs text-ink-secondary hover:text-ink-primary flex items-center justify-between py-1 transition-colors"
                >
                  <span className="flex items-center gap-1.5">
                    <SlidersHorizontal className="w-3.5 h-3.5 text-[#2b5797]" />
                    {showTgConfig ? '收起 Telegram 凭据配置' : '展开 / 修改 Telegram 手机凭据'}
                  </span>
                  {showTgConfig ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showTgConfig && (
                  <form
                    onSubmit={handleSaveTelegram}
                    className="mt-2.5 p-3.5 rounded-xl ios-glass-inset space-y-3 text-xs"
                  >
                    <div className="space-y-1">
                      <label className="text-[11px] text-ink-secondary font-medium">
                        Bot Token（从 @BotFather 获取）
                      </label>
                      <input
                        type="password"
                        required
                        placeholder="123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
                        value={botToken}
                        onChange={(e) => setBotToken(e.target.value)}
                        className="ios-input w-full px-3 py-1.5 rounded-lg font-mono text-xs"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] text-ink-secondary font-medium">
                        Telegram 用户 ID（从 @userinfobot 获取）
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="例如: 987654321"
                        value={botUserId}
                        onChange={(e) => setBotUserId(e.target.value)}
                        className="ios-input w-full px-3 py-1.5 rounded-lg font-mono text-xs"
                      />
                    </div>

                    <div className="pt-1 flex justify-end">
                      <button
                        type="submit"
                        disabled={savingTg}
                        className="ios-btn-primary h-8 px-3.5 rounded-lg text-xs font-medium whitespace-nowrap inline-flex items-center gap-1.5 disabled:opacity-50"
                      >
                        {savingTg ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                        <span>保存并启动 Bot</span>
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>

            <div className="pt-2 border-t border-[#142033]/[0.06] text-[11px] text-ink-tertiary flex items-center justify-between">
              <span>双向断网消息缓冲</span>
              <span className="text-[#2b5797] font-medium">自愈后自动补发至手机</span>
            </div>
          </div>
        </div>

        {/* =================================================================== */}
        {/* 底部本地控制快捷按钮组 */}
        {/* =================================================================== */}
        <div className="pt-1 space-y-2.5">
          <div className="text-[11px] font-semibold text-ink-tertiary tracking-wide">本地控制中枢</div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <button
              type="button"
              onClick={() => handleAction('wifi', api.reconnectWifi)}
              disabled={!!actionLoading}
              className="ios-btn-secondary py-3 px-3.5 rounded-xl flex items-center justify-center gap-2 text-xs font-medium text-ink-primary whitespace-nowrap disabled:opacity-50"
            >
              {actionLoading === 'wifi' ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#2b5797] shrink-0" />
              ) : (
                <Wifi className="w-4 h-4 text-[#2b5797] shrink-0" />
              )}
              <span>重连无线网</span>
            </button>

            <button
              type="button"
              onClick={() => handleAction('auth', api.authCampus)}
              disabled={!!actionLoading}
              className="ios-btn-secondary py-3 px-3.5 rounded-xl flex items-center justify-center gap-2 text-xs font-medium text-ink-primary whitespace-nowrap disabled:opacity-50"
            >
              {actionLoading === 'auth' ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#1f7a53] shrink-0" />
              ) : (
                <KeyRound className="w-4 h-4 text-[#1f7a53] shrink-0" />
              )}
              <span>触发认证</span>
            </button>

            <button
              type="button"
              onClick={() => handleAction('logout', api.logoutCampus)}
              disabled={!!actionLoading}
              className="ios-btn-secondary py-3 px-3.5 rounded-xl flex items-center justify-center gap-2 text-xs font-medium text-ink-primary whitespace-nowrap disabled:opacity-50"
            >
              {actionLoading === 'logout' ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#b43a40] shrink-0" />
              ) : (
                <LogOut className="w-4 h-4 text-[#b43a40] shrink-0" />
              )}
              <span>注销下线</span>
            </button>

            <button
              type="button"
              onClick={() => api.minimize()}
              className="ios-btn-secondary py-3 px-3.5 rounded-xl flex items-center justify-center gap-2 text-xs font-medium text-ink-primary whitespace-nowrap"
            >
              <Minimize2 className="w-4 h-4 text-ink-secondary shrink-0" />
              <span>静默后台常驻</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
