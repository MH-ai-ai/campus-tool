import React, { useState, useEffect, useRef } from 'react';
import {
  Save,
  Search,
  Sparkles,
  School,
  KeyRound,
  Network,
  Bell,
  Battery,
  Shield,
  ShieldCheck,
  Eye,
  EyeOff,
  Loader2,
  Cpu,
  Radar,
  Play,
} from 'lucide-react';
import { api, UniversityItem } from '../api';
import { useToast } from './ToastContext';

export const SettingsView: React.FC = () => {
  const toast = useToast();
  const [config, setConfig] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sniffing, setSniffing] = useState(false);
  const [detectingProxy, setDetectingProxy] = useState(false);
  const [testingProxy, setTestingProxy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [schools, setSchools] = useState<UniversityItem[]>([]);
  const [showSchoolDropdown, setShowSchoolDropdown] = useState(false);
  const schoolDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConfig();
    searchSchools('');

    const handleClickOutside = (event: MouseEvent) => {
      if (schoolDropdownRef.current && !schoolDropdownRef.current.contains(event.target as Node)) {
        setShowSchoolDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await api.getConfig();
      setConfig(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const searchSchools = async (q: string) => {
    try {
      const list = await api.searchUniversities(q);
      setSchools(list);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSaving(true);
    try {
      const res = await api.saveConfig(config);
      if (res.success) {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch (err: any) {
      toast.error(`保存失败: ${err?.message || err}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSniff = async () => {
    setSniffing(true);
    try {
      const res = await api.autoSniff();
      if (res.detected) {
        setConfig((prev) => ({
          ...prev,
          campus_auth_url: res.detected?.campus_auth_url || prev.campus_auth_url,
          campus_gateway: res.detected?.campus_gateway || prev.campus_gateway,
          auth_protocol: res.detected?.auth_protocol || prev.auth_protocol,
          university_name: res.detected?.university_name || prev.university_name,
          wlan_ac_ip: res.detected?.wlan_ac_ip || prev.wlan_ac_ip,
        }));
      }
      if (res.success) {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch (err: any) {
      toast.error(`嗅探失败: ${err?.message || err}`);
    } finally {
      setSniffing(false);
    }
  };

  const selectSchool = (school: UniversityItem) => {
    setConfig((prev) => ({
      ...prev,
      university_name: school.name,
      university_id: school.id,
      auth_protocol: school.protocol,
      campus_auth_url: school.auth_url,
      campus_gateway: school.gateway,
      campus_wifi_ssids: school.wifi_ssids.length > 0 ? school.wifi_ssids : prev.campus_wifi_ssids,
    }));
    setShowSchoolDropdown(false);
    toast.success(`已应用「${school.name}」配置模板`);
  };

  const updateField = (key: string, val: any) => {
    setConfig((prev) => ({ ...prev, [key]: val }));
  };

  const handleDetectProxy = async (silentOnMiss = false) => {
    setDetectingProxy(true);
    try {
      const res = await api.detectProxyClient();
      if (res.success && res.data?.found) {
        setConfig((prev) => ({
          ...prev,
          proxy_exe_path: res.data?.exe_path || prev.proxy_exe_path,
          proxy_server: res.data?.proxy_server || prev.proxy_server || '127.0.0.1:7897',
        }));
        toast.success(res.message);
      } else if (!silentOnMiss) {
        toast.error(res.message);
      }
    } catch (err: any) {
      if (!silentOnMiss) {
        toast.error(`探测代理客户端失败: ${err?.message || err}`);
      }
    } finally {
      setDetectingProxy(false);
    }
  };

  const handleTestProxyLaunch = async () => {
    setTestingProxy(true);
    try {
      const res = await api.launchProxyNow({
        proxy_exe_path: config.proxy_exe_path ?? '',
        proxy_server: config.proxy_server ?? '127.0.0.1:7897',
        auto_enable_system_proxy: config.auto_enable_system_proxy ?? true,
        proxy_bypass: config.proxy_bypass ?? '',
      });
      if (res.success) {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch (err: any) {
      toast.error(`执行代理联动测试失败: ${err?.message || err}`);
    } finally {
      setTestingProxy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 h-full flex items-center justify-center text-ink-secondary text-xs">
        <Loader2 className="w-4 h-4 animate-spin mr-2 text-[#2b5797]" />
        读取核心配置中...
      </div>
    );
  }

  return (
    <div className="flex-1 h-full flex flex-col overflow-hidden">
      {/* 顶部独立固定操作栏 */}
      <header className="shrink-0 ios-glass-header px-6 pt-5 pb-4 flex items-center justify-between gap-4 z-30">
        <div className="min-w-0">
          <h2 className="text-lg font-bold tracking-tight text-ink-primary truncate">守护内核配置</h2>
          <p className="text-xs text-ink-secondary mt-0.5 truncate">
            管理高校认证体系、网络网关、加密存储与守护策略
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleSniff}
            disabled={sniffing}
            className="ios-btn-secondary h-8 px-3 rounded-lg text-xs font-medium text-[#2b5797] whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 disabled:opacity-50"
          >
            {sniffing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 shrink-0" />
            )}
            <span>自动嗅探当前网络</span>
          </button>

          <button
            type="button"
            onClick={() => handleSave()}
            disabled={saving}
            className="ios-btn-primary h-8 px-3.5 rounded-lg text-xs font-semibold whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" /> : <Save className="w-3.5 h-3.5 shrink-0" />}
            <span>保存配置</span>
          </button>
        </div>
      </header>

      {/* 独立可滚动表单内容区 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* 分组 1: 高校与认证体系 */}
        <section className="ios-glass-card rounded-2xl p-5 space-y-4 relative z-20 overflow-visible">
          <div className="flex items-center gap-2 pb-2.5 border-b border-[#142033]/[0.07]">
            <School className="w-4 h-4 text-[#2b5797]" />
            <h3 className="text-xs font-semibold text-ink-primary tracking-wide">高校与认证体系</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs overflow-visible">
            {/* 高校检索选择 */}
            <div ref={schoolDropdownRef} className="space-y-1.5 relative">
              <label className="text-ink-secondary font-medium flex items-center justify-between gap-2">
                <span>所属院校 / 预置模板</span>
                <span className="text-[11px] text-[#2b5797]">支持全拼 / 首字母搜索</span>
              </label>

              <div className="relative">
                <input
                  type="text"
                  value={config.university_name || ''}
                  onFocus={() => {
                    searchSchools('');
                    setShowSchoolDropdown(true);
                  }}
                  onChange={(e) => {
                    updateField('university_name', e.target.value);
                    searchSchools(e.target.value);
                    setShowSchoolDropdown(true);
                  }}
                  placeholder="输入学校名或拼音检索（例如：延安大学 / 清华大学）"
                  className="ios-input w-full px-3.5 py-2 pr-9 rounded-xl text-xs"
                />
                <Search className="w-3.5 h-3.5 text-ink-tertiary absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* 浅色磨砂浮动选择弹层 */}
              {showSchoolDropdown && schools.length > 0 && (
                <div className="absolute left-0 right-0 top-full mt-1.5 max-h-56 overflow-y-auto rounded-xl bg-white/95 backdrop-blur-xl border border-[#142033]/12 shadow-glass-elevated z-50 divide-y divide-[#142033]/[0.06]">
                  {schools.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => selectSchool(s)}
                      className="w-full px-3.5 py-2.5 text-left text-xs hover:bg-[#2b5797]/[0.07] flex items-center justify-between transition-colors cursor-pointer"
                    >
                      <span className="font-medium text-ink-primary truncate">{s.name}</span>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#2b5797]/10 text-[#2b5797] shrink-0 ml-2">
                        {s.protocol}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 认证协议 */}
            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">认证协议体系</label>
              <select
                value={config.auth_protocol || 'drcom'}
                onChange={(e) => updateField('auth_protocol', e.target.value)}
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              >
                <option value="drcom">城市热点 Dr.COM Web (延安大学全校区置顶)</option>
                <option value="srun">深澜 Srun 4000 / Portal</option>
                <option value="ruijie">锐捷 Ruijie (RG-ePortal / SAM)</option>
                <option value="portal">通用 Web Portal 启发式网关</option>
              </select>
            </div>
          </div>
        </section>

        {/* 分组 2: 账号与安全凭据 */}
        <section className="ios-glass-card rounded-2xl p-5 space-y-4 relative z-10">
          <div className="flex items-center gap-2 pb-2.5 border-b border-[#142033]/[0.07]">
            <KeyRound className="w-4 h-4 text-[#1f7a53]" />
            <h3 className="text-xs font-semibold text-ink-primary tracking-wide">账号与安全凭据</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">校园网学号 / 账号</label>
              <input
                type="text"
                value={config.campus_account || ''}
                onChange={(e) => updateField('campus_account', e.target.value)}
                placeholder="请输入校园网认证账号"
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium flex items-center justify-between gap-2">
                <span>校园网认证密码</span>
                <span className="text-[11px] text-[#1f7a53] flex items-center gap-1 whitespace-nowrap">
                  <Shield className="w-3 h-3" /> 本地 Fernet 加密
                </span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={config.campus_password || ''}
                  onChange={(e) => updateField('campus_password', e.target.value)}
                  placeholder="请输入认证密码"
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
        </section>

        {/* 分组 3: 网络与认证参数 */}
        <section className="ios-glass-card rounded-2xl p-5 space-y-4 relative z-10">
          <div className="flex items-center gap-2 pb-2.5 border-b border-[#142033]/[0.07]">
            <Network className="w-4 h-4 text-[#2b5797]" />
            <h3 className="text-xs font-semibold text-ink-primary tracking-wide">网络与认证参数</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">认证接口 URL</label>
              <input
                type="text"
                value={config.campus_auth_url || ''}
                onChange={(e) => updateField('campus_auth_url', e.target.value)}
                placeholder="http://10.200.84.3:801/eportal/portal/login"
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">网关探测 IP</label>
              <input
                type="text"
                value={config.campus_gateway || ''}
                onChange={(e) => updateField('campus_gateway', e.target.value)}
                placeholder="10.211.0.1"
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">校园 WiFi SSID 名单（逗号分隔）</label>
              <input
                type="text"
                value={
                  Array.isArray(config.campus_wifi_ssids)
                    ? config.campus_wifi_ssids.join(', ')
                    : config.campus_wifi_ssids || ''
                }
                onChange={(e) =>
                  updateField(
                    'campus_wifi_ssids',
                    e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean)
                  )
                }
                placeholder="YADX-STU, YADX-TEA"
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">信任免认证 WiFi（宿舍热点 / 家庭）</label>
              <input
                type="text"
                value={
                  Array.isArray(config.trusted_home_ssids)
                    ? config.trusted_home_ssids.join(', ')
                    : config.trusted_home_ssids || ''
                }
                onChange={(e) =>
                  updateField(
                    'trusted_home_ssids',
                    e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean)
                  )
                }
                placeholder="Home_5G, MyHotspot"
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>
          </div>
        </section>

        {/* 分组 4: 连网后自动启动代理（Clash 联动） */}
        <section className="ios-glass-card rounded-2xl p-5 space-y-4 relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[#142033]/[0.07]">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#2b5797]" />
              <h3 className="text-xs font-semibold text-ink-primary tracking-wide">
                连网后自动启动代理（Clash 联动）
              </h3>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleDetectProxy(false)}
                disabled={detectingProxy}
                className="ios-btn-secondary h-7 px-2.5 rounded-lg text-[11px] font-medium text-[#2b5797] whitespace-nowrap inline-flex items-center gap-1 disabled:opacity-50"
              >
                {detectingProxy ? (
                  <Loader2 className="w-3 h-3 animate-spin shrink-0" />
                ) : (
                  <Radar className="w-3 h-3 shrink-0" />
                )}
                <span>一键探测本机 Clash</span>
              </button>

              <button
                type="button"
                onClick={handleTestProxyLaunch}
                disabled={testingProxy}
                className="ios-btn-secondary h-7 px-2.5 rounded-lg text-[11px] font-medium text-[#1f7a53] whitespace-nowrap inline-flex items-center gap-1 disabled:opacity-50"
              >
                {testingProxy ? (
                  <Loader2 className="w-3 h-3 animate-spin shrink-0" />
                ) : (
                  <Play className="w-3 h-3 shrink-0" />
                )}
                <span>立即测试启动</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <label className="flex items-center gap-2.5 cursor-pointer py-1.5 select-none">
              <input
                type="checkbox"
                checked={config.auto_start_proxy ?? false}
                onChange={(e) => {
                  const checked = e.target.checked;
                  updateField('auto_start_proxy', checked);
                  if (checked && !String(config.proxy_exe_path || '').trim()) {
                    handleDetectProxy(true);
                  }
                }}
                className="w-4 h-4 rounded accent-[#2b5797] border-[#142033]/25"
              />
              <span className="text-ink-primary font-medium">校园网连通后自动启动代理客户端</span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer py-1.5 select-none">
              <input
                type="checkbox"
                checked={config.auto_enable_system_proxy ?? true}
                onChange={(e) => updateField('auto_enable_system_proxy', e.target.checked)}
                className="w-4 h-4 rounded accent-[#2b5797] border-[#142033]/25"
              />
              <span className="text-ink-primary font-medium">
                代理端口就绪后自动开启 Windows 系统代理（自动绕过校园内网）
              </span>
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">代理客户端可执行文件路径</label>
              <input
                type="text"
                value={config.proxy_exe_path || ''}
                onChange={(e) => updateField('proxy_exe_path', e.target.value)}
                placeholder="留空则自动探测本机 Clash Verge / FlClash 等"
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">本地代理端口地址</label>
              <input
                type="text"
                value={config.proxy_server ?? '127.0.0.1:7897'}
                onChange={(e) => updateField('proxy_server', e.target.value)}
                placeholder="127.0.0.1:7897"
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>
          </div>

          <p className="text-[11px] text-ink-tertiary leading-relaxed">
            建议关闭 Clash 自身的开机自启，改由安澜在连上校园网后再启动，彻底避免开机代理抢占导致校园网无法认证。
          </p>
        </section>

        {/* 分组 5: 后台守护策略 */}
        <section className="ios-glass-card rounded-2xl p-5 space-y-4 relative z-10">
          <div className="flex items-center gap-2 pb-2.5 border-b border-[#142033]/[0.07]">
            <Battery className="w-4 h-4 text-[#9a5b13]" />
            <h3 className="text-xs font-semibold text-ink-primary tracking-wide">后台守护策略</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">掉线探针周期（秒）</label>
              <input
                type="number"
                min={1}
                max={60}
                value={config.network_check_interval_seconds ?? 2}
                onChange={(e) => updateField('network_check_interval_seconds', parseInt(e.target.value, 10))}
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-ink-secondary font-medium">断电安全关机阈值（%）</label>
              <input
                type="number"
                min={5}
                max={50}
                value={config.auto_shutdown_threshold ?? 20}
                onChange={(e) => updateField('auto_shutdown_threshold', parseInt(e.target.value, 10))}
                className="ios-input w-full px-3.5 py-2 rounded-xl text-xs font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
            <label className="flex items-center gap-2.5 cursor-pointer py-1.5 select-none">
              <input
                type="checkbox"
                checked={config.autostart ?? true}
                onChange={(e) => updateField('autostart', e.target.checked)}
                className="w-4 h-4 rounded accent-[#2b5797] border-[#142033]/25"
              />
              <span className="text-ink-primary font-medium">开机自动启动</span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer py-1.5 select-none">
              <input
                type="checkbox"
                checked={config.start_minimized_on_boot ?? true}
                onChange={(e) => updateField('start_minimized_on_boot', e.target.checked)}
                className="w-4 h-4 rounded accent-[#2b5797] border-[#142033]/25"
              />
              <span className="text-ink-primary font-medium">开机自启时静默藏入系统托盘</span>
            </label>
          </div>
        </section>
      </div>
    </div>
  );
};
