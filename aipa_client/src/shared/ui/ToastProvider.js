import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import styles from './ToastProvider.module.css';

const ToastContext = createContext(null);

function buildToastClassName(type) {
  if (type === 'success') return `${styles.toastItem} ${styles.toastSuccess}`;
  if (type === 'error') return `${styles.toastItem} ${styles.toastError}`;
  return `${styles.toastItem} ${styles.toastInfo}`;
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timerMapRef = useRef(new Map());

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
    const timer = timerMapRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timerMapRef.current.delete(id);
    }
  }, []);

  const showToast = useCallback((message, options = {}) => {
    const text = String(message || '').trim();
    if (!text) return;

    const id = `toast-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    const type = options.type === 'success' || options.type === 'error' ? options.type : 'info';
    const duration = Number.isFinite(options.duration) ? Math.max(600, Number(options.duration)) : 3000;

    setToasts((prev) => [...prev, { id, text, type }]);
    const timer = setTimeout(() => {
      dismissToast(id);
    }, duration);
    timerMapRef.current.set(id, timer);
  }, [dismissToast]);

  const value = useMemo(() => ({ showToast, dismissToast }), [showToast, dismissToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className={styles.toastViewport} aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div key={toast.id} className={buildToastClassName(toast.type)}>
            {toast.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
