import React, { useState, useEffect } from 'react';
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
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Cpu,
} from 'lucide-react';
import { api, UniversityItem } from '../api';

export const SettingsView: React.FC = () => {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sniffing, setSniffing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [schools, setSchools] = useState<UniversityItem[]>([]);
  const [showSchoolDropdown, setShowSchoolDropdown] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    loadConfig();
    searchSchools('');
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

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3500);
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSaving(true);
    try {
      const res = await api.saveConfig(config);
      showToast(res.success ? 'success' : 'error', res.message);
    } catch (err: any) {
      showToast('error', `保存失败: ${err.message || err}`);
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
        }));
      }
      showToast(res.success ? 'success' : 'error', res.message);
    } catch (err: any) {
      showToast('error', `嗅探失败: ${err.message || err}`);
    } finally {
      setSniffing(false);
    }
  };

  const selectSchool = (school: UniversityItem) => {
    setConfig((prev) => ({
      ...prev,
      university_name: school.name,
      auth_protocol: school.protocol,
      campus_auth_url: school.auth_url,
      campus_gateway: school.gateway,
      campus_wifi_ssids: school.wifi_ssids.length > 0 ? school.wifi_ssids : prev.campus_wifi_ssids,
    }));
    setShowSchoolDropdown(false);
    showToast('success', `已应用「${school.name}」配置模板`);
  };

  const updateField = (key: string, val: any) => {
    setConfig((prev) => ({ ...prev, [key]: val }));
  };

  if (loading) {
    return (
      <div className="flex-1 h-full flex items-center justify-center text-apple-textSecondary text-xs">
        <Loader2 className="w-5 h-5 animate-spin mr-2 text-apple-blue" />
        读取核心配置中...
      </div>
    );
  }

  return (
    <div className="flex-1 h-full overflow-y-auto p-7 space-y-6">
      {/* 头部固定栏 */}
      <div className="flex items-center justify-between sticky top-0 z-30 bg-[#0b0c11]/85 backdrop-blur-2xl py-2 -my-2 border-b border-white/[0.08]">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">守护内核配置</h2>
          <p className="text-xs text-apple-textTertiary">管理高校认证体系、网络网关、加密存储与多通道告警</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSniff}
            disabled={sniffing}
            className="liquid-btn px-3.5 py-2 rounded-xl text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5 disabled:opacity-50"
          >
            {sniffing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            自动嗅探当前网络
          </button>

          <button
            type="button"
            onClick={() => handleSave()}
            disabled={saving}
            className="px-4 py-2 rounded-xl bg-apple-blue hover:bg-apple-blueHover text-white text-xs font-medium shadow-apple-glow-blue/30 shadow-md flex items-center gap-1.5 transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            保存配置
          </button>
        </div>
      </div>

      {/* 状态通知浮条 */}
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
      {/* 分组 1: 高校与认证体系 (特别优化层级防止遮挡) */}
      {/* ------------------------------------------------------------------- */}
      <section className="liquid-card rounded-2xl p-5 space-y-4 relative z-20">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.08]">
          <School className="w-4 h-4 text-apple-blue" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">高校与认证体系</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* 高校检索选择 */}
          <div className="space-y-1.5 relative">
            <label className="text-apple-textSecondary font-medium flex items-center justify-between">
              <span>所属高校体系</span>
              <span className="text-[10px] text-apple-textTertiary">首字母模糊检索</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={config.university_name || ''}
                onChange={(e) => {
                  updateField('university_name', e.target.value);
                  searchSchools(e.target.value);
                  setShowSchoolDropdown(true);
                }}
                onFocus={() => setShowSchoolDropdown(true)}
                placeholder="搜索高校，如：延安大学、清华、浙大..."
                className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
              />
              <Search className="w-3.5 h-3.5 text-apple-textTertiary absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {/* 模糊下拉匹配面板 - 修复遮挡与层级 */}
            {showSchoolDropdown && schools.length > 0 && (
              <>
                <div
                  className="fixed inset-0 z-40 bg-transparent"
                  onClick={() => setShowSchoolDropdown(false)}
                />
                <div className="absolute left-0 right-0 top-full mt-2 z-50 max-h-60 overflow-y-auto rounded-xl bg-[#12141f] border border-white/[0.18] shadow-[0_20px_50px_rgba(0,0,0,0.9)] p-1.5 space-y-1 backdrop-blur-2xl">
                  <div className="px-2 py-1 text-[10px] text-apple-textTertiary font-mono flex items-center justify-between border-b border-white/[0.06]">
                    <span>匹配高校模板 ({schools.length})</span>
                    <button
                      type="button"
                      onClick={() => setShowSchoolDropdown(false)}
                      className="text-apple-blue hover:underline"
                    >
                      关闭
                    </button>
                  </div>
                  {schools.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => selectSchool(item)}
                      className="w-full text-left px-3 py-2 rounded-lg hover:bg-apple-blue/20 hover:text-white transition-colors flex items-center justify-between text-xs"
                    >
                      <span className="font-medium text-apple-textPrimary truncate">{item.name}</span>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-white/[0.08] text-apple-textSecondary shrink-0 ml-2">
                        {item.protocol}
                      </span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* 核心认证协议 */}
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">认证协议体系</label>
            <select
              value={config.auth_protocol || 'drcom'}
              onChange={(e) => updateField('auth_protocol', e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            >
              <option value="drcom">城市热点 Dr.COM Web (延安大学全校区置顶)</option>
              <option value="srun">深澜 Srun 4000 / Portal</option>
              <option value="ruijie">锐捷 Ruijie (RG-ePortal / SAM)</option>
              <option value="portal">通用 Web Portal 启发式网关</option>
            </select>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 2: 账号凭据 */}
      {/* ------------------------------------------------------------------- */}
      <section className="liquid-card rounded-2xl p-5 space-y-4 relative z-10">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.08]">
          <KeyRound className="w-4 h-4 text-apple-green" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">账号与安全凭据</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">校园网学号 / 账号</label>
            <input
              type="text"
              value={config.campus_account || ''}
              onChange={(e) => updateField('campus_account', e.target.value)}
              placeholder="请输入校园网认证账号"
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium flex items-center justify-between">
              <span>校园网认证密码</span>
              <span className="text-[10px] text-apple-green flex items-center gap-1 font-mono">
                <Shield className="w-3 h-3" /> 本地 Fernet 加密
              </span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={config.campus_password || ''}
                onChange={(e) => updateField('campus_password', e.target.value)}
                placeholder="请输入认证密码"
                className="w-full px-3.5 py-2 pr-10 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-apple-textTertiary hover:text-white"
              >
                {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 3: 网络与网关接口 */}
      {/* ------------------------------------------------------------------- */}
      <section className="liquid-card rounded-2xl p-5 space-y-4 relative z-10">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.08]">
          <Network className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">网络与认证参数</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">认证接口 URL</label>
            <input
              type="text"
              value={config.campus_auth_url || ''}
              onChange={(e) => updateField('campus_auth_url', e.target.value)}
              placeholder="http://10.200.84.3:801/eportal/index.jsp"
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">网关探测 IP</label>
            <input
              type="text"
              value={config.campus_gateway || ''}
              onChange={(e) => updateField('campus_gateway', e.target.value)}
              placeholder="10.200.84.3"
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">校园 WiFi SSID 名单</label>
            <input
              type="text"
              value={Array.isArray(config.campus_wifi_ssids) ? config.campus_wifi_ssids.join(', ') : config.campus_wifi_ssids || ''}
              onChange={(e) =>
                updateField(
                  'campus_wifi_ssids',
                  e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                )
              }
              placeholder="YADX-STU, YAU-WiFi"
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">信任免认证 WiFi (如宿舍热点/家庭)</label>
            <input
              type="text"
              value={Array.isArray(config.trusted_home_ssids) ? config.trusted_home_ssids.join(', ') : config.trusted_home_ssids || ''}
              onChange={(e) =>
                updateField(
                  'trusted_home_ssids',
                  e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                )
              }
              placeholder="Home_5G, MyHotspot"
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            />
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 4: 运行守护与开机常驻 */}
      {/* ------------------------------------------------------------------- */}
      <section className="liquid-card rounded-2xl p-5 space-y-4 relative z-10">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.08]">
          <Cpu className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">后台守护策略</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">掉线探针周期 (秒)</label>
            <input
              type="number"
              min={1}
              max={60}
              value={config.network_check_interval_seconds ?? 2}
              onChange={(e) => updateField('network_check_interval_seconds', parseInt(e.target.value, 10))}
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">断电安全关机阈值 (%)</label>
            <input
              type="number"
              min={5}
              max={50}
              value={config.auto_shutdown_threshold ?? 20}
              onChange={(e) => updateField('auto_shutdown_threshold', parseInt(e.target.value, 10))}
              className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.12] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            />
          </div>

          <div className="space-y-1.5 flex flex-col justify-end">
            <label className="flex items-center gap-2.5 cursor-pointer py-2">
              <input
                type="checkbox"
                checked={config.autostart ?? true}
                onChange={(e) => updateField('autostart', e.target.checked)}
                className="w-4 h-4 rounded text-apple-blue focus:ring-apple-blue bg-black/40 border-white/[0.2]"
              />
              <span className="text-apple-textPrimary font-medium font-sans">开机静默启动并在后台常驻</span>
            </label>
          </div>
        </div>
      </section>
    </div>
  );
};
