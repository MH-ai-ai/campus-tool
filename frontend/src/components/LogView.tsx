import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Search,
  Trash2,
  RefreshCw,
  ArrowDown,
  ShieldAlert,
  CheckCircle2,
  Info,
  Download,
  FolderOpen,
  Check,
  Loader2,
  X,
  FileArchive,
} from 'lucide-react';
import { api } from '../api';
import { useToast } from './ToastContext';

type ExportState = 'idle' | 'exporting' | 'done';

export const LogView: React.FC = () => {
  const toast = useToast();
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<'ALL' | 'INFO' | 'WARNING' | 'ERROR'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [exportState, setExportState] = useState<ExportState>('idle');
  const [diagExporting, setDiagExporting] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const endRef = useRef<HTMLDivElement>(null);
  const exportTimerRef = useRef<number | null>(null);
  const clearTimerRef = useRef<number | null>(null);

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
    const timer = window.setInterval(fetchLogs, 4000);
    return () => {
      window.clearInterval(timer);
      if (exportTimerRef.current) window.clearTimeout(exportTimerRef.current);
      if (clearTimerRef.current) window.clearTimeout(clearTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (autoScroll && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleClearClick = async () => {
    if (!confirmClear) {
      setConfirmClear(true);
      if (clearTimerRef.current) window.clearTimeout(clearTimerRef.current);
      clearTimerRef.current = window.setTimeout(() => {
        setConfirmClear(false);
      }, 3000);
      return;
    }

    if (clearTimerRef.current) window.clearTimeout(clearTimerRef.current);
    setConfirmClear(false);
    try {
      const res = await api.clearLogs();
      await fetchLogs();
      if (res.success) {
        toast.success(res.message || '运行日志已清空');
      } else {
        toast.error(res.message || '清空日志失败');
      }
    } catch (err: any) {
      toast.error(`清空失败: ${err?.message || err}`);
    }
  };

  const handleExport = async () => {
    if (exportState === 'exporting') return;
    setExportState('exporting');
    if (exportTimerRef.current) window.clearTimeout(exportTimerRef.current);

    try {
      const res = await api.exportLogs();
      const content = res?.content || res?.data?.content || logs.join('\n');
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

      setExportState('done');
      toast.success('全量日志文件已导出');
      exportTimerRef.current = window.setTimeout(() => {
        setExportState('idle');
      }, 1800);
    } catch (err: any) {
      console.error(err);
      setExportState('idle');
      toast.error(`导出失败: ${err?.message || err}`);
    }
  };

  const handleOpenFolder = async () => {
    try {
      const res = await api.openLogFolder();
      if (res.success) {
        toast.info(res.message || '已打开日志目录');
      } else {
        toast.error(res.message || '打开日志目录失败');
      }
    } catch (err: any) {
      console.error(err);
      toast.error(`打开失败: ${err?.message || err}`);
    }
  };

  const handleExportDiagnosticBundle = async () => {
    if (diagExporting) return;
    setDiagExporting(true);
    try {
      const res = await api.exportDiagnosticBundle();
      if (res.success) {
        toast.success(res.path ? `脱敏诊断包已生成: ${res.path}` : res.message || '脱敏诊断包已生成');
      } else {
        toast.error(res.message || '生成诊断包失败');
      }
    } catch (err: any) {
      toast.error(`生成诊断包失败: ${err?.message || err}`);
    } finally {
      setDiagExporting(false);
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

  const hasFilter = Boolean(search) || levelFilter !== 'ALL';

  return (
    <div className="flex-1 h-full flex flex-col overflow-hidden">
      {/* 顶部固定玻璃页头与单行工具栏 */}
      <header className="shrink-0 ios-glass-header px-6 pt-5 pb-4 z-20">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-lg font-bold tracking-tight text-ink-primary flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[#2b5797] shrink-0" />
              <span className="truncate">运行与守护日志</span>
            </h2>
            <p className="text-xs text-ink-secondary mt-0.5 truncate">
              实时呈现网络探针、断网自愈与系统电源记录
            </p>
          </div>

          <span className="shrink-0 whitespace-nowrap px-2.5 py-1 rounded-full text-[11px] font-medium ios-glass-inset text-ink-secondary font-mono">
            {hasFilter ? `显示 ${filteredLogs.length} / ${logs.length} 条` : `共 ${logs.length} 条`}
          </span>
        </div>

        {/* 第二行：检索过滤 + 固定宽度不折行按钮组 */}
        <div className="mt-3.5 flex items-center justify-between gap-2.5">
          {/* 左侧搜索与级别过滤 */}
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <div className="relative min-w-[96px] flex-1 max-w-[200px]">
              <Search className="w-3.5 h-3.5 text-ink-tertiary absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder="搜索关键词..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="搜索日志关键词"
                className="ios-input w-full h-8 pl-8 pr-7 rounded-lg text-xs"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  aria-label="清除搜索"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-tertiary hover:text-ink-primary"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            <div
              role="group"
              aria-label="日志级别过滤"
              className="flex items-center p-0.5 h-8 rounded-lg ios-glass-inset text-[11px] shrink-0"
            >
              {(
                [
                  { id: 'ALL', label: '全部' },
                  { id: 'INFO', label: 'INFO' },
                  { id: 'WARNING', label: 'WARN' },
                  { id: 'ERROR', label: 'ERROR' },
                ] as const
              ).map((lvl) => (
                <button
                  key={lvl.id}
                  type="button"
                  onClick={() => setLevelFilter(lvl.id)}
                  className={`px-2 py-1 rounded-md font-medium whitespace-nowrap transition-all ${
                    levelFilter === lvl.id
                      ? 'bg-white text-ink-primary shadow-sm'
                      : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  {lvl.label}
                </button>
              ))}
            </div>
          </div>

          {/* 右侧操作按钮组：全部强制单行防折行，导出按钮固定 min-w 杜绝位移 */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={handleExport}
              disabled={exportState === 'exporting'}
              title="导出全量日志文件 (.log)"
              className={`h-8 min-w-[84px] px-2.5 rounded-lg text-xs font-medium whitespace-nowrap shrink-0 inline-flex items-center justify-center gap-1.5 transition-all ${
                exportState === 'done'
                  ? 'bg-[#1f7a53]/10 text-[#1f7a53] border border-[#1f7a53]/25'
                  : 'ios-btn-secondary text-[#2b5797]'
              }`}
            >
              {exportState === 'exporting' ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" />
                  <span>导出中</span>
                </>
              ) : exportState === 'done' ? (
                <>
                  <Check className="w-3.5 h-3.5 shrink-0" />
                  <span>已导出</span>
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5 shrink-0" />
                  <span>导出日志</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleExportDiagnosticBundle}
              disabled={diagExporting}
              title="一键生成脱敏诊断压缩包 (.zip)"
              className="h-8 px-2.5 rounded-lg ios-btn-secondary text-xs font-medium text-[#2b5797] whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 disabled:opacity-60"
            >
              {diagExporting ? (
                <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" />
              ) : (
                <FileArchive className="w-3.5 h-3.5 shrink-0" />
              )}
              <span>{diagExporting ? '打包中' : '诊断包'}</span>
            </button>

            <button
              type="button"
              onClick={handleOpenFolder}
              title="在系统资源管理器中打开日志目录"
              className="h-8 px-2.5 rounded-lg ios-btn-secondary text-xs font-medium text-ink-secondary hover:text-ink-primary whitespace-nowrap shrink-0 inline-flex items-center gap-1.5"
            >
              <FolderOpen className="w-3.5 h-3.5 shrink-0" />
              <span>目录</span>
            </button>

            <button
              type="button"
              onClick={() => setAutoScroll(!autoScroll)}
              aria-pressed={autoScroll}
              title={autoScroll ? '已开启自动滚动追踪最新日志' : '已暂停自动滚动'}
              className={`h-8 px-2.5 rounded-lg text-xs font-medium whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 transition-all ${
                autoScroll
                  ? 'bg-[#2b5797]/10 text-[#2b5797] border border-[#2b5797]/25'
                  : 'ios-btn-secondary text-ink-secondary hover:text-ink-primary'
              }`}
            >
              <ArrowDown className="w-3.5 h-3.5 shrink-0" />
              <span>追踪</span>
            </button>

            <button
              type="button"
              onClick={fetchLogs}
              disabled={loading}
              aria-label="刷新日志"
              title="刷新日志"
              className="w-8 h-8 rounded-lg ios-btn-secondary text-ink-secondary hover:text-ink-primary shrink-0 inline-flex items-center justify-center disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>

            <button
              type="button"
              onClick={handleClearClick}
              aria-label={confirmClear ? '确认清空日志' : '清空日志'}
              title={confirmClear ? '再次点击立即清空全部日志' : '清空日志'}
              className={`h-8 rounded-lg text-xs font-medium whitespace-nowrap shrink-0 inline-flex items-center justify-center gap-1 transition-all ${
                confirmClear
                  ? 'ios-btn-danger px-2.5'
                  : 'w-8 ios-btn-secondary text-ink-secondary hover:text-[#b43a40]'
              }`}
            >
              <Trash2 className="w-3.5 h-3.5 shrink-0" />
              {confirmClear && <span>确认清空</span>}
            </button>
          </div>
        </div>
      </header>

      {/* 浅色瓷白微透日志面板 */}
      <div className="flex-1 min-h-0 p-5 pt-4 overflow-hidden">
        <div className="h-full ios-glass-card rounded-2xl flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-3.5 font-mono text-[11.5px] leading-6 space-y-0.5 select-text">
            {filteredLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-ink-tertiary text-xs gap-2.5 select-none">
                <Terminal className="w-7 h-7 text-ink-tertiary/50" />
                <span>{hasFilter ? '当前筛选条件下暂无匹配的日志记录' : '暂无运行日志记录'}</span>
                {hasFilter && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearch('');
                      setLevelFilter('ALL');
                    }}
                    className="px-3 py-1.5 rounded-lg ios-btn-secondary text-xs text-[#2b5797]"
                  >
                    清除筛选条件
                  </button>
                )}
              </div>
            ) : (
              filteredLogs.map((line, idx) => {
                const isError = line.includes('ERROR');
                const isWarning = line.includes('WARNING') || line.includes('WARN');
                const isSuccess = !isError && !isWarning && (line.includes('成功') || line.includes('在线'));

                let badgeText = 'INFO';
                let badgeClass = 'bg-[#142033]/[0.06] text-ink-secondary';
                let textClass = 'text-ink-primary';
                let icon = null;

                if (isError) {
                  badgeText = 'ERR';
                  badgeClass = 'bg-[#b43a40]/10 text-[#b43a40]';
                  textClass = 'text-[#9e2c32] font-medium';
                  icon = <ShieldAlert className="w-3 h-3 text-[#b43a40] shrink-0 mr-1 inline" />;
                } else if (isWarning) {
                  badgeText = 'WARN';
                  badgeClass = 'bg-[#b47319]/10 text-[#9a5b13]';
                  textClass = 'text-[#844d10]';
                  icon = <Info className="w-3 h-3 text-[#9a5b13] shrink-0 mr-1 inline" />;
                } else if (isSuccess) {
                  badgeText = 'OK';
                  badgeClass = 'bg-[#1f7a53]/10 text-[#1f7a53]';
                  textClass = 'text-[#196343]';
                  icon = <CheckCircle2 className="w-3 h-3 text-[#1f7a53] shrink-0 mr-1 inline" />;
                }

                return (
                  <div
                    key={idx}
                    className="px-2 py-0.5 rounded-lg hover:bg-[#142033]/[0.04] transition-colors flex items-baseline gap-2"
                  >
                    <span className="text-ink-tertiary/70 w-8 text-right shrink-0 select-none text-[10.5px]">
                      {String(idx + 1).padStart(3, '0')}
                    </span>
                    <span
                      className={`px-1.5 py-0 rounded text-[10px] font-semibold shrink-0 select-none ${badgeClass}`}
                    >
                      {badgeText}
                    </span>
                    <span className={`break-all ${textClass}`}>
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
      </div>
    </div>
  );
};
