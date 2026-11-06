import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Search, Trash2, RefreshCw, ArrowDown, ShieldAlert, CheckCircle, Info } from 'lucide-react';
import { api } from '../api';

export const LogView: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<'ALL' | 'INFO' | 'WARNING' | 'ERROR'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);

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
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Terminal className="w-5 h-5 text-apple-blue" />
            运行与守护日志
          </h2>
          <p className="text-xs text-apple-textTertiary">实时滚动呈现网络探针、重连事件与系统电源日志流</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-medium flex items-center gap-1.5 transition-all ${
              autoScroll
                ? 'bg-apple-blue/15 text-apple-blue border-apple-blue/30 shadow-apple-glow-blue/20'
                : 'bg-white/[0.04] text-apple-textSecondary border-white/[0.08]'
            }`}
          >
            <ArrowDown className="w-3.5 h-3.5" />
            自动滚动
          </button>

          <button
            onClick={fetchLogs}
            disabled={loading}
            className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-apple-textSecondary hover:text-white transition-all disabled:opacity-50"
            title="刷新日志"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleClear}
            className="p-2 rounded-xl bg-white/[0.04] hover:bg-apple-coral/20 border border-white/[0.08] text-apple-textSecondary hover:text-apple-coral transition-all"
            title="清空日志"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 搜索与级别过滤栏 */}
      <div className="flex items-center justify-between gap-3 shrink-0">
        {/* 搜索框 */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 text-apple-textTertiary absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="搜索日志关键词..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3.5 py-1.5 rounded-xl bg-apple-card border border-white/[0.08] text-xs text-apple-textPrimary placeholder:text-apple-textTertiary focus:outline-none focus:border-apple-blue transition-all"
          />
        </div>

        {/* 级别过滤器 */}
        <div className="flex p-1 rounded-xl bg-white/[0.04] border border-white/[0.08] text-[11px]">
          {(['ALL', 'INFO', 'WARNING', 'ERROR'] as const).map((lvl) => (
            <button
              key={lvl}
              onClick={() => setLevelFilter(lvl)}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                levelFilter === lvl ? 'bg-apple-blue text-white shadow-sm' : 'text-apple-textTertiary hover:text-white'
              }`}
            >
              {lvl === 'ALL' ? '全部' : lvl}
            </button>
          ))}
        </div>
      </div>

      {/* 终端日志视窗 */}
      <div className="flex-1 min-h-0 bg-[#090a10]/80 backdrop-blur-2xl rounded-2xl border border-white/[0.12] shadow-[0_20px_45px_rgba(0,0,0,0.6)] p-4 overflow-y-auto font-mono text-[11px] leading-relaxed">
        {filteredLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-apple-textTertiary text-xs">
            暂无匹配的运行日志
          </div>
        ) : (
          <div className="space-y-1">
            {filteredLogs.map((line, idx) => {
              const isErr = line.includes('ERROR');
              const isWarn = line.includes('WARNING') || line.includes('WARN');
              const isInfo = line.includes('INFO');

              return (
                <div
                  key={idx}
                  className={`px-2 py-0.5 rounded transition-colors hover:bg-white/[0.03] flex items-start gap-2 ${
                    isErr
                      ? 'text-apple-coral bg-apple-coral/[0.05]'
                      : isWarn
                      ? 'text-apple-amber bg-apple-amber/[0.05]'
                      : isInfo
                      ? 'text-apple-textSecondary'
                      : 'text-apple-textTertiary'
                  }`}
                >
                  <span className="text-[10px] text-apple-textTertiary select-none w-7 text-right shrink-0">
                    {idx + 1}
                  </span>
                  <span className="break-all whitespace-pre-wrap">{line}</span>
                </div>
              );
            })}
            <div ref={endRef} />
          </div>
        )}
      </div>
    </div>
  );
};
