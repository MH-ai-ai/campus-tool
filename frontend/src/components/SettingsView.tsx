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
      <div className="flex-1 h-full flex items-center justify-center text-white/70 text-xs">
        <Loader2 className="w-5 h-5 animate-spin mr-2 text-cyan-300" />
        读取核心配置中...
      </div>
    );
  }

  return (
    <div className="flex-1 h-full overflow-y-auto p-7 space-y-6">
      {/* 头部固定栏 */}
      <div className="flex items-center justify-between sticky top-0 z-30 py-2 -my-2 border-b border-white/20 backdrop-blur-xl bg-white/10 px-4 -mx-4 rounded-xl">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white drop-shadow-sm">守护内核配置</h2>
          <p className="text-xs text-white/70">管理高校认证体系、网络网关、加密存储与多通道告警</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSniff}
            disabled={sniffing}
            className="twilight-btn-secondary px-3.5 py-2 rounded-xl text-xs text-cyan-200 hover:text-white flex items-center gap-1.5 disabled:opacity-50"
          >
            {sniffing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-cyan-300" />}
            自动嗅探当前网络
          </button>

          <button
            type="button"
            onClick={() => handleSave()}
            disabled={saving}
            className="twilight-btn-primary px-4 py-2 rounded-xl text-white text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.98] disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            保存配置
          </button>
        </div>
      </div>

      {/* 状态通知浮条 */}
      {toast && (
        <div
          className={`p-3.5 rounded-2xl border text-xs flex items-center gap-2.5 animate-in fade-in duration-200 shadow-lg ${
            toast.type === 'success'
              ? 'bg-emerald-500/20 text-emerald-100 border-emerald-400/40 backdrop-blur-md'
              : 'bg-rose-500/20 text-rose-100 border-rose-400/40 backdrop-blur-md'
          }`}
        >
          {toast.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-300 shrink-0" /> : <AlertCircle className="w-4 h-4 text-rose-300 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* 分组 1: 高校与认证体系 (特别优化层级防止遮挡，允许下拉溢出) */}
      {/* ------------------------------------------------------------------- */}
      <section className="twilight-glass-card rounded-2xl p-5 space-y-4 relative z-30 overflow-visible">
        <div className="flex items-center gap-2 pb-2 border-b border-white/20">
          <School className="w-4 h-4 text-cyan-300" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">高校与认证体系</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs overflow-visible">
          {/* 高校检索选择 */}
          <div ref={schoolDropdownRef} className="space-y-1.5 relative">
            <label className="text-white/80 font-medium flex items-center justify-between">
              <span>所属院校 / 预置模板</span>
              <span className="text-[10px] text-cyan-300 font-mono">支持全拼/首字母搜索</span>
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
                className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300"
              />
              <Search className="w-3.5 h-3.5 text-white/50 absolute right-3 top-1/2 -translate-y-1/2" />
            </div>

            {/* 独立防遮挡浮动弹层 */}
            {showSchoolDropdown && schools.length > 0 && (
              <div className="absolute left-0 right-0 top-full mt-1.5 max-h-56 overflow-y-auto rounded-xl bg-[#13112c]/95 border border-white/30 shadow-2xl z-50 divide-y divide-white/10 backdrop-blur-2xl">
                {schools.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => selectSchool(s)}
                    className="w-full px-3.5 py-2.5 text-left text-xs hover:bg-white/15 flex items-center justify-between transition-colors cursor-pointer"
                  >
                    <span className="font-medium text-white truncate">{s.name}</span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-white/15 text-cyan-200 shrink-0 ml-2">
                      {s.protocol}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 认证协议 */}
          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">认证协议体系</label>
            <select
              value={config.auth_protocol || 'drcom'}
              onChange={(e) => updateField('auth_protocol', e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-[#1e1b4b]/90 border border-white/30 text-xs text-white focus:outline-none focus:border-cyan-300 font-mono"
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
      <section className="twilight-glass-card rounded-2xl p-5 space-y-4 relative z-10">
        <div className="flex items-center gap-2 pb-2 border-b border-white/20">
          <KeyRound className="w-4 h-4 text-emerald-300" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">账号与安全凭据</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">校园网学号 / 账号</label>
            <input
              type="text"
              value={config.campus_account || ''}
              onChange={(e) => updateField('campus_account', e.target.value)}
              placeholder="请输入校园网认证账号"
              className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300 font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-white/80 font-medium flex items-center justify-between">
              <span>校园网认证密码</span>
              <span className="text-[10px] text-emerald-300 flex items-center gap-1 font-mono">
                <Shield className="w-3 h-3" /> 本地 Fernet 加密
              </span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={config.campus_password || ''}
                onChange={(e) => updateField('campus_password', e.target.value)}
                placeholder="请输入认证密码"
                className="w-full px-3.5 py-2 pr-10 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white"
              >
                {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 3: 网络与网关参数 */}
      {/* ------------------------------------------------------------------- */}
      <section className="twilight-glass-card rounded-2xl p-5 space-y-4 relative z-10">
        <div className="flex items-center gap-2 pb-2 border-b border-white/20">
          <Network className="w-4 h-4 text-cyan-300" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">网络与认证参数</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">认证接口 URL</label>
            <input
              type="text"
              value={config.campus_auth_url || ''}
              onChange={(e) => updateField('campus_auth_url', e.target.value)}
              placeholder="http://10.200.84.3:801/eportal/portal/login"
              className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">网关探测 IP</label>
            <input
              type="text"
              value={config.campus_gateway || ''}
              onChange={(e) => updateField('campus_gateway', e.target.value)}
              placeholder="10.200.84.3"
              className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">校园 WiFi SSID 名单 (逗号分隔)</label>
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
              className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">信任免认证 WiFi (宿舍热点/家庭)</label>
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
              className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300"
            />
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 4: 守护策略与自启 */}
      {/* ------------------------------------------------------------------- */}
      <section className="twilight-glass-card rounded-2xl p-5 space-y-4 relative z-10">
        <div className="flex items-center gap-2 pb-2 border-b border-white/20">
          <Battery className="w-4 h-4 text-purple-300" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider font-mono">后台守护策略</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">掉线探针周期 (秒)</label>
            <input
              type="number"
              min={1}
              max={60}
              value={config.network_check_interval_seconds ?? 2}
              onChange={(e) => updateField('network_check_interval_seconds', parseInt(e.target.value, 10))}
              className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white focus:outline-none focus:border-cyan-300"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-white/80 font-medium">断电安全关机阈值 (%)</label>
            <input
              type="number"
              min={5}
              max={50}
              value={config.auto_shutdown_threshold ?? 20}
              onChange={(e) => updateField('auto_shutdown_threshold', parseInt(e.target.value, 10))}
              className="w-full px-3.5 py-2 rounded-xl bg-white/10 border border-white/30 text-xs text-white focus:outline-none focus:border-cyan-300"
            />
          </div>

          <div className="space-y-1.5 flex flex-col justify-end">
            <label className="flex items-center gap-2.5 cursor-pointer py-2">
              <input
                type="checkbox"
                checked={config.autostart ?? true}
                onChange={(e) => updateField('autostart', e.target.checked)}
                className="w-4 h-4 rounded text-cyan-400 focus:ring-cyan-400 bg-white/20 border-white/40"
              />
              <span className="text-white font-medium font-sans">开机静默启动并在后台常驻</span>
            </label>
          </div>
        </div>
      </section>
    </div>
  );
};
