import React, { useState, useEffect } from 'react';
import {
  Save,
  Check,
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
  HelpCircle,
} from 'lucide-react';
import { api, UniversityItem } from '../api';

export const SettingsView: React.FC = () => {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sniffing, setSniffing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [schools, setSchools] = useState<UniversityItem[]>([]);
  const [schoolQuery, setSchoolQuery] = useState('');
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
    setSchoolQuery('');
    showToast('success', `已应用「${school.name}」配置模板`);
  };

  const updateField = (key: string, val: any) => {
    setConfig((prev) => ({ ...prev, [key]: val }));
  };

  if (loading) {
    return (
      <div className="flex-1 h-full flex items-center justify-center text-apple-textSecondary text-xs">
        <Loader2 className="w-5 h-5 animate-spin mr-2 text-apple-blue" />
        读取偏好设置中...
      </div>
    );
  }

  return (
    <div className="flex-1 h-full overflow-y-auto p-6 space-y-6">
      {/* 头部标题与保存按钮 */}
      <div className="flex items-center justify-between sticky top-0 z-20 bg-apple-bg/80 backdrop-blur-xl py-2 -my-2 border-b border-white/[0.06]">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">偏好设置</h2>
          <p className="text-xs text-apple-textTertiary">管理高校认证体系、凭据加密、免梯告警与电源阈值</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSniff}
            disabled={sniffing}
            className="px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs text-apple-blue hover:text-apple-blueHover flex items-center gap-1.5 transition-all disabled:opacity-50"
          >
            {sniffing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            自动嗅探网络参数
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
      {/* 分组 1: 高校与核心协议体系 */}
      {/* ------------------------------------------------------------------- */}
      <section className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
          <School className="w-4 h-4 text-apple-blue" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider">高校与认证体系</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* 高校检索选择 */}
          <div className="space-y-1.5 relative">
            <label className="text-apple-textSecondary font-medium flex items-center justify-between">
              <span>所属高校名称</span>
              <span className="text-[10px] text-apple-textTertiary">支持首字母检索全国名录</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={config.university_name || ''}
                onChange={(e) => {
                  updateField('university_name', e.target.value);
                  setSchoolQuery(e.target.value);
                  searchSchools(e.target.value);
                  setShowSchoolDropdown(true);
                }}
                onFocus={() => setShowSchoolDropdown(true)}
                placeholder="搜索高校，如：延安大学、清华、浙大..."
                className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
              />
              <Search className="w-3.5 h-3.5 text-apple-textTertiary absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {/* 模糊下拉匹配面板 */}
            {showSchoolDropdown && schools.length > 0 && (
              <div className="absolute left-0 right-0 top-full mt-1.5 z-30 max-h-56 overflow-y-auto rounded-xl bg-[#1a1c26] border border-white/[0.12] shadow-2xl p-1.5 space-y-1">
                <div className="px-2 py-1 text-[10px] text-apple-textTertiary font-medium flex items-center justify-between">
                  <span>匹配高校模板</span>
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
                    className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-apple-blue/15 hover:text-white transition-colors flex items-center justify-between text-xs"
                  >
                    <span className="font-medium text-apple-textPrimary">{item.name}</span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-white/[0.08] text-apple-textSecondary">
                      {item.protocol}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 核心认证协议 */}
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">核心认证协议</label>
            <select
              value={config.auth_protocol || 'drcom'}
              onChange={(e) => updateField('auth_protocol', e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            >
              <option value="drcom">城市热点 Dr.COM Web (延安大学默认置顶)</option>
              <option value="srun">深澜 Srun 4000 / Portal (清华/浙大/北邮)</option>
              <option value="ruijie">锐捷 Ruijie (RG-ePortal / SAM)</option>
              <option value="portal">通用 Web Portal 启发式网关</option>
            </select>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 2: 校园网账号与密码凭据 */}
      {/* ------------------------------------------------------------------- */}
      <section className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
          <KeyRound className="w-4 h-4 text-apple-green" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider">账号与安全凭据</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">校园网账号 / 学号</label>
            <input
              type="text"
              value={config.campus_account || ''}
              onChange={(e) => updateField('campus_account', e.target.value)}
              placeholder="请输入校园网认证学号"
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium flex items-center justify-between">
              <span>校园网密码</span>
              <span className="text-[10px] text-apple-green flex items-center gap-1">
                <Shield className="w-3 h-3" /> 本地 Fernet 加密存储
              </span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={config.campus_password || ''}
                onChange={(e) => updateField('campus_password', e.target.value)}
                placeholder="请输入校园网密码"
                className="w-full px-3.5 py-2 pr-10 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
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
      {/* 分组 3: 网络与网关参数 */}
      {/* ------------------------------------------------------------------- */}
      <section className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
          <Network className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider">网络与认证接口</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">认证接口 URL</label>
            <input
              type="text"
              value={config.campus_auth_url || ''}
              onChange={(e) => updateField('campus_auth_url', e.target.value)}
              placeholder="例如: http://10.200.84.3:801/eportal/index.jsp"
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">校园网网关 IP</label>
            <input
              type="text"
              value={config.campus_gateway || ''}
              onChange={(e) => updateField('campus_gateway', e.target.value)}
              placeholder="例如: 10.200.84.3"
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">校园 WiFi SSID 列表 (逗号分隔)</label>
            <input
              type="text"
              value={Array.isArray(config.campus_wifi_ssids) ? config.campus_wifi_ssids.join(', ') : config.campus_wifi_ssids || ''}
              onChange={(e) =>
                updateField(
                  'campus_wifi_ssids',
                  e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                )
              }
              placeholder="例如: YADX-STU, YAU-WiFi"
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">家庭 / 免认证信任 WiFi (逗号分隔)</label>
            <input
              type="text"
              value={Array.isArray(config.trusted_home_ssids) ? config.trusted_home_ssids.join(', ') : config.trusted_home_ssids || ''}
              onChange={(e) =>
                updateField(
                  'trusted_home_ssids',
                  e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                )
              }
              placeholder="例如: Home_5G, MyHotspot"
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 4: 国内免梯通知通道 */}
      {/* ------------------------------------------------------------------- */}
      <section className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
          <Bell className="w-4 h-4 text-apple-amber" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
            国内免梯推送通道 (飞书 / 钉钉 / Telegram)
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">飞书自定义机器人 Webhook</label>
            <input
              type="text"
              value={config.feishu_webhook_url || ''}
              onChange={(e) => updateField('feishu_webhook_url', e.target.value)}
              placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">钉钉自定义机器人 Webhook</label>
            <input
              type="text"
              value={config.dingtalk_webhook_url || ''}
              onChange={(e) => updateField('dingtalk_webhook_url', e.target.value)}
              placeholder="https://oapi.dingtalk.com/robot/send?access_token=..."
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------- */}
      {/* 分组 5: 电源保护与运行守护 */}
      {/* ------------------------------------------------------------------- */}
      <section className="rounded-2xl bg-apple-card/80 border border-white/[0.08] p-5 shadow-apple-card space-y-4 backdrop-blur-md">
        <div className="flex items-center gap-2 pb-2 border-b border-white/[0.06]">
          <Battery className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider">电源防护与后台运行</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">安全关机电量阈值 (%)</label>
            <input
              type="number"
              min={5}
              max={50}
              value={config.auto_shutdown_threshold ?? 20}
              onChange={(e) => updateField('auto_shutdown_threshold', parseInt(e.target.value, 10))}
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-apple-textSecondary font-medium">关机倒计时 (秒)</label>
            <input
              type="number"
              min={10}
              max={600}
              value={config.auto_shutdown_delay ?? 60}
              onChange={(e) => updateField('auto_shutdown_delay', parseInt(e.target.value, 10))}
              className="w-full px-3.5 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue font-mono"
            />
          </div>

          <div className="space-y-1.5 flex flex-col justify-end">
            <label className="flex items-center gap-2.5 cursor-pointer py-2">
              <input
                type="checkbox"
                checked={config.autostart ?? true}
                onChange={(e) => updateField('autostart', e.target.checked)}
                className="w-4 h-4 rounded text-apple-blue focus:ring-apple-blue bg-apple-bg border-white/[0.2]"
              />
              <span className="text-apple-textPrimary font-medium">Windows 开机自动后台启动</span>
            </label>
          </div>
        </div>
      </section>
    </div>
  );
};
