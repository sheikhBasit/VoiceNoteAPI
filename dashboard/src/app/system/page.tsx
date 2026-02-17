'use client';

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
                        <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs space-y-2 overflow-y-auto max-h-80 border border-slate-800">
                            <p className="text-emerald-500 text-[10px] uppercase font-bold">[INFO] 2026-02-18 01:52:12 - Celery worker heart-beat received</p>
                            <p className="text-slate-400">[DEBUG] Connection established to postgresql://db:5432</p>
                            <p className="text-slate-400">[INFO] Processing task: note_process_pipeline[7d1a2b]</p>
                            <p className="text-amber-400 text-[10px] uppercase font-bold">[WARN] 2026-02-18 01:52:05 - Cache miss on key: analytics:usage_24h</p>
                            <p className="text-slate-400">[INFO] Request completed: GET /api/v1/admin/dashboard/overview [200 OK]</p>
                            <p className="text-emerald-500 text-[10px] uppercase font-bold">[INFO] 2026-02-18 01:51:42 - Celery worker heart-beat received</p>
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
