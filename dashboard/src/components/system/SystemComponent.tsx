'use client';

import { Activity, Server, Database, HardDrive, Cpu } from 'lucide-react';

interface SystemComponentProps {
    name: string;
    status: 'healthy' | 'warning' | 'error';
    value?: string;
    icon: any;
}

export function SystemComponent({ name, status, value, icon: Icon }: SystemComponentProps) {
    const statusColors = {
        healthy: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20 shadow-[0_0_12px_rgba(16,185,129,0.1)]',
        warning: 'text-amber-500 bg-amber-500/10 border-amber-500/20 shadow-[0_0_12px_rgba(245,158,11,0.1)]',
        error: 'text-red-500 bg-red-500/10 border-red-500/20 shadow-[0_0_12px_rgba(239,68,68,0.1)]'
    };

    const dotColors = {
        healthy: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]',
        warning: 'bg-amber-500',
        error: 'bg-red-500 animate-pulse'
    };

    return (
        <div className="glass-card p-5 group transition-all">
            <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-slate-950/50 rounded-lg text-indigo-400 group-hover:text-indigo-300 transition-colors">
                    <Icon className="w-5 h-5" />
                </div>
                <div className={`flex items-center space-x-2 px-2 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider ${statusColors[status]}`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${dotColors[status]}`} />
                    <span>{status}</span>
                </div>
            </div>
            <h4 className="text-slate-200 font-semibold mb-1">{name}</h4>
            <p className="text-xs text-slate-500">{value || 'Operative'}</p>
        </div>
    );
}
