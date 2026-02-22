'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import {
    CheckCircle2,
    AlertCircle,
    Info,
    XCircle,
    X
} from 'lucide-react';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
    id: string;
    message: string;
    type: ToastType;
}

interface ToastContextType {
    showToast: (message: string, type?: ToastType) => void;
    success: (message: string) => void;
    error: (message: string) => void;
    info: (message: string) => void;
    warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider = ({ children }: { children: ReactNode }) => {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const showToast = useCallback((message: string, type: ToastType = 'info') => {
        const id = Math.random().toString(36).substring(2, 9);
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => removeToast(id), 5000);
    }, [removeToast]);

    const success = (msg: string) => showToast(msg, 'success');
    const error = (msg: string) => showToast(msg, 'error');
    const info = (msg: string) => showToast(msg, 'info');
    const warning = (msg: string) => showToast(msg, 'warning');

    return (
        <ToastContext.Provider value={{ showToast, success, error, info, warning }}>
            {children}
            <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border glass-card shadow-2xl animate-in slide-in-from-right-4 duration-300 ${toast.type === 'success' ? 'border-emerald-500/30' :
                                toast.type === 'error' ? 'border-rose-500/30' :
                                    toast.type === 'warning' ? 'border-amber-500/30' :
                                        'border-indigo-500/30'
                            }`}
                    >
                        {toast.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                        {toast.type === 'error' && <XCircle className="w-5 h-5 text-rose-500" />}
                        {toast.type === 'warning' && <AlertCircle className="w-5 h-5 text-amber-500" />}
                        {toast.type === 'info' && <Info className="w-5 h-5 text-indigo-500" />}

                        <p className="text-sm font-medium text-slate-200 min-w-[200px]">{toast.message}</p>

                        <button
                            onClick={() => removeToast(toast.id)}
                            className="hover:bg-slate-800 p-1 rounded-lg transition-colors"
                        >
                            <X className="w-4 h-4 text-slate-500" />
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
};

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) throw new Error('useToast must be used within ToastProvider');
    return context;
};
