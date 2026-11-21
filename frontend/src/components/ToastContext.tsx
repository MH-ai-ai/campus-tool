import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  showToast: (type: ToastType, message: string) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * 全局右上角悬浮轻提示容器：脱离文档流，避免挤压工具栏或顶跳页面卡片。
 */
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextIdRef = useRef(1);
  const timersRef = useRef<Record<number, number>>({});

  const dismiss = useCallback((id: number) => {
    if (timersRef.current[id]) {
      window.clearTimeout(timersRef.current[id]);
      delete timersRef.current[id];
    }
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const showToast = useCallback(
    (type: ToastType, message: string) => {
      const id = nextIdRef.current++;
      setToasts((prev) => [...prev.slice(-2), { id, type, message }]);
      timersRef.current[id] = window.setTimeout(() => {
        dismiss(id);
      }, 3500);
    },
    [dismiss]
  );

  useEffect(() => {
    return () => {
      Object.values(timersRef.current).forEach((t) => window.clearTimeout(t));
      timersRef.current = {};
    };
  }, []);

  const value: ToastContextValue = {
    showToast,
    success: useCallback((msg: string) => showToast('success', msg), [showToast]),
    error: useCallback((msg: string) => showToast('error', msg), [showToast]),
    info: useCallback((msg: string) => showToast('info', msg), [showToast]),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)] pointer-events-none"
      >
        {toasts.map((item) => {
          const isSuccess = item.type === 'success';
          const isError = item.type === 'error';

          return (
            <div
              key={item.id}
              role="status"
              className="pointer-events-auto toast-enter flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl bg-white/95 backdrop-blur-xl border border-[#142033]/10 shadow-glass-elevated text-xs text-ink-primary"
            >
              {isSuccess ? (
                <CheckCircle2 className="w-4 h-4 text-[#1f7a53] shrink-0 mt-0.5" />
              ) : isError ? (
                <AlertCircle className="w-4 h-4 text-[#b43a40] shrink-0 mt-0.5" />
              ) : (
                <Info className="w-4 h-4 text-[#2b5797] shrink-0 mt-0.5" />
              )}
              <span className="flex-1 leading-relaxed break-words">{item.message}</span>
              <button
                type="button"
                onClick={() => dismiss(item.id)}
                aria-label="关闭提示"
                className="p-0.5 rounded-md text-ink-tertiary hover:text-ink-primary hover:bg-[#142033]/[0.06] transition-colors shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextValue => {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return ctx;
};
