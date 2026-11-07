import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Search,
  Trash2,
  RefreshCw,
  ArrowDown,
  ShieldAlert,
  CheckCircle,
  Info,
  Download,
  FolderOpen,
} from 'lucide-react';
import { api } from '../api';

export const LogView: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<'ALL' | 'INFO' | 'WARNING' | 'ERROR'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getLogs();
      setLogs(data);
    } catch (err) {
      console.error('Failed to get logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const timer = setInterval(fetchLogs, 4000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (autoScroll && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleClear = async () => {
    if (confirm('确定要清空当前的运行日志文件吗？')) {
      await api.clearLogs();
      fetchLogs();
      showToast('日志已清空');
    }
  };

  const handleExport = async () => {
    try {
      const res = await api.exportLogs();
      const content = res?.data?.content || logs.join('\n');
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const dateStr = new Date().toISOString().slice(0, 10);
      a.href = url;
      a.download = `campus_guard_logs_${dateStr}.log`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('日志文件已成功导出');
    } catch (err: any) {
      console.error(err);
      showToast(`导出失败: ${err.message || err}`);
    }
  };

  const handleOpenFolder = async () => {
    try {
      const res = await api.openLogFolder();
      showToast(res.message || '已打开日志目录');
    } catch (err: any) {
      console.error(err);
      showToast(`打开失败: ${err.message || err}`);
    }
  };

  // 过滤日志行
  const filteredLogs = logs.filter((line) => {
    if (search && !line.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (levelFilter === 'ALL') return true;
    if (levelFilter === 'INFO' && line.includes('INFO')) return true;
    if (levelFilter === 'WARNING' && (line.includes('WARNING') || line.includes('WARN'))) return true;
    if (levelFilter === 'ERROR' && line.includes('ERROR')) return true;
    return false;
  });

  return (
    <div className="flex-1 h-full p-6 flex flex-col space-y-4 overflow-hidden">
      {/* 头部标题与操作 */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2 drop-shadow-sm">
            <Terminal className="w-5 h-5 text-cyan-300" />
            运行与守护日志
          </h2>
          <p className="text-xs text-white/70">实时滚动呈现网络探针、重连事件与系统电源日志流</p>
        </div>

        <div className="flex items-center gap-2">
          {toastMsg && (
            <span className="text-[11px] px-2.5 py-1 rounded-lg bg-cyan-500/20 text-cyan-200 border border-cyan-400/30 animate-in fade-in duration-150">
              {toastMsg}
            </span>
          )}

          <button
            onClick={handleExport}
            className="px-3 py-1.5 rounded-xl twilight-btn-secondary text-cyan-200 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm"
            title="导出全量日志文件 (.log)"
          >
            <Download className="w-3.5 h-3.5" />
            导出日志
          </button>

          <button
            onClick={handleOpenFolder}
            className="px-3 py-1.5 rounded-xl twilight-btn-secondary text-white/80 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-all"
            title="在系统资源管理器中打开日志目录"
          >
            <FolderOpen className="w-3.5 h-3.5" />
            打开目录
          </button>

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-medium flex items-center gap-1.5 transition-all ${
              autoScroll
                ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400/40 shadow-sm'
                : 'twilight-btn-secondary text-white/70'
            }`}
          >
            <ArrowDown className="w-3.5 h-3.5" />
            自动滚动
          </button>

          <button
            onClick={fetchLogs}
            disabled={loading}
            className="p-2 rounded-xl twilight-btn-secondary text-white/80 hover:text-white transition-all disabled:opacity-50"
            title="刷新日志"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleClear}
            className="p-2 rounded-xl twilight-btn-secondary text-white/70 hover:text-rose-300 transition-all"
            title="清空日志"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 搜索与级别过滤栏 */}
      <div className="flex items-center justify-between gap-3 shrink-0">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 text-white/50 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="搜索日志关键词..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3.5 py-1.5 rounded-xl bg-white/10 border border-white/20 text-xs text-white placeholder-white/40 focus:outline-none focus:border-cyan-300 transition-all"
          />
        </div>

        {/* 级别过滤器 */}
        <div className="flex p-1 rounded-xl bg-white/10 border border-white/20 text-[11px]">
          {(['ALL', 'INFO', 'WARNING', 'ERROR'] as const).map((lvl) => (
            <button
              key={lvl}
              onClick={() => setLevelFilter(lvl)}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                levelFilter === lvl
                  ? 'bg-gradient-to-r from-indigo-500 to-pink-500 text-white shadow-sm'
                  : 'text-white/70 hover:text-white'
              }`}
            >
              {lvl === 'ALL' ? '全部' : lvl}
            </button>
          ))}
        </div>
      </div>

      {/* 日志终端显示容器 (高透暮色终端) */}
      <div className="flex-1 rounded-2xl p-4 overflow-y-auto font-mono text-xs leading-relaxed space-y-1 twilight-glass-card border border-white/25">
        {filteredLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-white/50 text-xs">
            暂无匹配的运行日志
          </div>
        ) : (
          filteredLogs.map((line, idx) => {
            const isError = line.includes('ERROR');
            const isWarning = line.includes('WARNING') || line.includes('WARN');
            const isInfo = line.includes('INFO');

            let color = 'text-white/80';
            let icon = null;

            if (isError) {
              color = 'text-rose-300 font-semibold';
              icon = <ShieldAlert className="w-3 h-3 text-rose-300 shrink-0 inline mr-1.5" />;
            } else if (isWarning) {
              color = 'text-amber-300';
              icon = <Info className="w-3 h-3 text-amber-300 shrink-0 inline mr-1.5" />;
            } else if (isInfo && (line.includes('成功') || line.includes('在线'))) {
              color = 'text-emerald-300';
              icon = <CheckCircle className="w-3 h-3 text-emerald-300 shrink-0 inline mr-1.5" />;
            }

            return (
              <div key={idx} className={`hover:bg-white/10 px-2 py-0.5 rounded transition-colors ${color} flex items-start`}>
                <span className="text-white/30 mr-2 select-none shrink-0">{String(idx + 1).padStart(3, '0')}</span>
                <span className="break-all">
                  {icon}
                  {line}
                </span>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
};
