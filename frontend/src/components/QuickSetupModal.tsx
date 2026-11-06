import React, { useState, useEffect } from 'react';
import { X, Sparkles, Loader2, CheckCircle2, AlertCircle, School, KeyRound, User, Globe } from 'lucide-react';
import { api, UniversityItem } from '../api';

interface QuickSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const QuickSetupModal: React.FC<QuickSetupModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [sniffing, setSniffing] = useState(false);
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [protocol, setProtocol] = useState('drcom');
  const [universityName, setUniversityName] = useState('延安大学 (默认 · Dr.COM)');
  const [authUrl, setAuthUrl] = useState('');
  const [gateway, setGateway] = useState('');
  const [ssid, setSsid] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      handleAutoSniff();
    }
  }, [isOpen]);

  const handleAutoSniff = async () => {
    setSniffing(true);
    setMessage({ type: 'info', text: '正在拦截未加密 HTTP 探针以嗅探校园网认证网关...' });
    try {
      const res = await api.autoSniff();
      if (res.detected) {
        if (res.detected.campus_auth_url) setAuthUrl(res.detected.campus_auth_url);
        if (res.detected.campus_gateway) setGateway(res.detected.campus_gateway);
        if (res.detected.campus_wifi_ssid) setSsid(res.detected.campus_wifi_ssid);
        if (res.detected.auth_protocol) setProtocol(res.detected.auth_protocol);
        if (res.detected.university_name) setUniversityName(res.detected.university_name);
      }
      setMessage({ type: res.success ? 'success' : 'info', text: res.message });
    } catch (err: any) {
      setMessage({ type: 'error', text: `嗅探失败: ${err.message || err}` });
    } finally {
      setSniffing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!account.trim() || !password.trim()) {
      setMessage({ type: 'error', text: '请填写学号/账号与密码' });
      return;
    }

    setLoading(true);
    setMessage({ type: 'info', text: '正在保存凭据并尝试建立校园网认证...' });
    try {
      const res = await api.quickSetup({
        account,
        password,
        protocol,
        university_name: universityName,
        auth_url: authUrl,
        gateway,
        ssid,
      });

      if (res.success) {
        setMessage({ type: 'success', text: res.message });
        setTimeout(() => {
          onSuccess();
          onClose();
        }, 1200);
      } else {
        setMessage({ type: 'error', text: res.message });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: `打通失败: ${err.message || err}` });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-apple-card border border-white/[0.12] rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* 标题栏 */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-apple-blue/20 text-apple-blue flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">小白一键智能打通</h3>
              <p className="text-[11px] text-apple-textTertiary">自动推断网关，仅需输入学号与密码</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg hover:bg-white/[0.08] text-apple-textSecondary hover:text-white flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 状态提示 */}
        {message && (
          <div
            className={`mx-6 mt-4 p-3 rounded-xl text-xs flex items-center gap-2 border ${
              message.type === 'success'
                ? 'bg-apple-green/10 text-apple-green border-apple-green/20'
                : message.type === 'error'
                ? 'bg-apple-coral/10 text-apple-coral border-apple-coral/20'
                : 'bg-apple-blue/10 text-apple-blue border-apple-blue/20'
            }`}
          >
            {message.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : message.type === 'error' ? (
              <AlertCircle className="w-4 h-4 shrink-0" />
            ) : (
              <Loader2 className="w-4 h-4 shrink-0 animate-spin" />
            )}
            <span className="truncate">{message.text}</span>
          </div>
        )}

        {/* 表单主体 */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* 嗅探回显信息胶囊 */}
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-1.5 text-xs">
            <div className="flex items-center justify-between text-apple-textSecondary">
              <span className="flex items-center gap-1.5 text-[11px]">
                <Globe className="w-3.5 h-3.5 text-apple-blue" />
                嗅探网关 / 协议
              </span>
              <button
                type="button"
                onClick={handleAutoSniff}
                disabled={sniffing}
                className="text-[11px] text-apple-blue hover:text-apple-blueHover flex items-center gap-1 disabled:opacity-50"
              >
                {sniffing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                重新嗅探
              </button>
            </div>
            <div className="text-[11px] text-apple-textPrimary font-mono truncate">
              {gateway ? `${gateway} · ${protocol.toUpperCase()}` : '等待嗅探中...'}
            </div>
            {authUrl && <div className="text-[10px] text-apple-textTertiary font-mono truncate">{authUrl}</div>}
          </div>

          {/* 账号字段 */}
          <div className="space-y-1.5">
            <label className="text-xs text-apple-textSecondary flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-apple-textTertiary" />
              校园网账号 / 学号
            </label>
            <input
              type="text"
              required
              placeholder="例如: 20240901001"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary placeholder:text-apple-textTertiary focus:outline-none focus:border-apple-blue focus:ring-1 focus:ring-apple-blue transition-all"
            />
          </div>

          {/* 密码字段 */}
          <div className="space-y-1.5">
            <label className="text-xs text-apple-textSecondary flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-apple-textTertiary" />
              校园网密码
            </label>
            <input
              type="password"
              required
              placeholder="请输入密码 (本地 Fernet 加密存储)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary placeholder:text-apple-textTertiary focus:outline-none focus:border-apple-blue focus:ring-1 focus:ring-apple-blue transition-all"
            />
          </div>

          {/* 协议与所属高校微调 */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="space-y-1">
              <label className="text-[11px] text-apple-textTertiary">认证协议</label>
              <select
                value={protocol}
                onChange={(e) => setProtocol(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
              >
                <option value="drcom">城市热点 Dr.COM</option>
                <option value="srun">深澜 Srun 4000</option>
                <option value="ruijie">锐捷 Ruijie</option>
                <option value="portal">通用 Web Portal</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-apple-textTertiary">所属高校</label>
              <input
                type="text"
                value={universityName}
                onChange={(e) => setUniversityName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-apple-bg border border-white/[0.1] text-xs text-apple-textPrimary focus:outline-none focus:border-apple-blue"
              />
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="pt-3 flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl border border-white/[0.1] text-xs text-apple-textSecondary hover:bg-white/[0.04] transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading || sniffing}
              className="flex-1 py-2.5 rounded-xl bg-apple-blue hover:bg-apple-blueHover text-white text-xs font-medium shadow-apple-glow-blue/20 shadow-md flex items-center justify-center gap-1.5 disabled:opacity-50 transition-all"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              立即一键打通
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
