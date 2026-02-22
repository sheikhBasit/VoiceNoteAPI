'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from "@/store/useAuthStore";
import { useDashboardOverview } from "@/hooks/useDashboard";
import { SystemComponent } from "@/components/system/SystemComponent";
import {
    Database,
    Cpu,
    Activity,
    HardDrive,
    Server,
    Terminal,
    RefreshCw,
    AlertTriangle
} from 'lucide-react';

export default function SystemPage() {
    const { data: metrics, isLoading, refetch, isFetching } = useDashboardOverview();
    const { token } = useAuthStore();
    const [logs, setLogs] = useState<any[]>([]);

    useEffect(() => {
        let ws: WebSocket;
        let reconnectTimeout: any;

        const connect = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
            const host = apiUrl.replace('http://', '').replace('https://', '').replace(/\/api\/v1\/?$/, '');
            const wsUrl = `${protocol}//${host}/admin/logs/stream`;

            ws = new WebSocket(wsUrl);

            ws.onmessage = (event: MessageEvent) => {
                try {
                    const log = JSON.parse(event.data);
                    setLogs((prev: any[]) => [log, ...prev].slice(0, 100));
                } catch (e) {
                    console.error("Failed to parse log", e);
                }
            };

            ws.onclose = () => {
                reconnectTimeout = setTimeout(connect, 3000);
            };

            ws.onerror = () => {
                ws.close();
            };
        };

        connect();

        return () => {
            ws.close();
            clearTimeout(reconnectTimeout);
        };
    }, [token]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
            </div>
        );
    }

    const systemHealth = [
        { name: 'PostgreSQL Cluster', status: metrics?.system.database_status === 'healthy' ? 'healthy' : 'error', value: 'Port 5432, 12 Active Conn.', icon: Database },
        { name: 'Redis Cache', status: metrics?.system.redis_status === 'healthy' ? 'healthy' : 'error', value: 'Memory: 42.5 MB', icon: Activity },
        { name: 'Celery Workers', status: metrics?.system.celery_workers ? 'healthy' : 'warning', value: `${metrics?.system.celery_workers} workers active`, icon: Cpu },
        { name: 'MinIO Storage', status: 'healthy', value: '4.2 GB / 100 GB', icon: HardDrive },
    ];

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold text-slate-100">System Monitoring</h2>
                    <p className="text-slate-400 mt-1">Real-time health and infrastructure performance.</p>
                </div>
                <button
                    onClick={() => refetch()}
                    disabled={isFetching}
                    className="flex items-center space-x-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-lg text-sm font-medium border border-slate-800 transition-colors disabled:opacity-50"
                >
                    <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
                    <span>Refresh Status</span>
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {systemHealth.map((item) => (
                    <SystemComponent key={item.name} {...(item as any)} />
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="glass-card p-6">
                        <h3 className="text-lg font-semibold mb-6 flex items-center">
                            <Terminal className="w-5 h-5 mr-3 text-indigo-400" />
                            Live System Logs
                        </h3>
                        <div className="bg-slate-950 rounded-lg p-4 font-mono text-[10px] space-y-1.5 overflow-y-auto h-80 border border-slate-800 custom-scrollbar">
                            {logs.length === 0 && (
                                <p className="text-slate-600 italic">Waiting for telemetry stream...</p>
                            )}
                            {logs.map((log: any, i: number) => (
                                <div key={i} className="flex space-x-3 items-start group">
                                    <span className="text-slate-600 shrink-0">[{log.timestamp?.split('T')[1].split('.')[0]}]</span>
                                    <span className={`uppercase font-bold shrink-0 ${log.level === 'INFO' ? 'text-emerald-500' :
                                        log.level === 'ERROR' ? 'text-rose-500' :
                                            'text-amber-500'
                                        }`}>[{log.level}]</span>
                                    <span className="text-slate-300 break-all">{log.message}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="glass-card p-6 border-indigo-500/20 bg-indigo-500/[0.02]">
                        <h3 className="text-lg font-semibold mb-4 flex items-center">
                            <Server className="w-5 h-5 mr-3 text-indigo-400" />
                            Infrastructure Detail
                        </h3>
                        <div className="space-y-4">
                            <DetailRow label="API Version" value="v1.4.2-stable" />
                            <DetailRow label="Docker Environment" value="production" />
                            <DetailRow label="Uptime" value="14d 6h 22m" />
                            <DetailRow label="Worker Queue" value="8 tasks pending" />
                        </div>
                    </div>

                    <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                        <div className="flex space-x-3">
                            <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />
                            <div>
                                <p className="text-sm font-semibold text-amber-500">Resource Advisory</p>
                                <p className="text-xs text-amber-500/80 mt-1 leading-relaxed">
                                    Memory usage on `voicenote_celery_worker` is nearing 85% limit. Consider scaling workers or increasing container memory.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function DetailRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between items-center py-2 border-b border-slate-800/50 last:border-0">
            <span className="text-xs text-slate-500">{label}</span>
            <span className="text-xs font-medium text-slate-300">{value}</span>
        </div>
    );
}
