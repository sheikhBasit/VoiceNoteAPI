'use client';

import { useDashboardOverview } from "@/hooks/useDashboard";
import {
  Users,
  FileAudio,
  CheckSquare,
  TrendingUp,
  Activity,
  AlertCircle
} from 'lucide-react';

export default function DashboardPage() {
  const { data: metrics, isLoading, error } = useDashboardOverview();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 flex items-center space-x-3">
        <AlertCircle className="w-5 h-5" />
        <span>Failed to load dashboard metrics. Ensure the API is running.</span>
      </div>
    );
  }

  const statCards = [
    { name: 'Total Users', value: metrics?.users.total, sub: `${metrics?.users.new_this_month} new`, icon: Users, color: 'text-blue-400' },
    { name: 'Active Notes', value: metrics?.content.total_notes, sub: `${metrics?.activity.notes_today} today`, icon: FileAudio, color: 'text-purple-400' },
    { name: 'Tasks Completed', value: metrics?.content.total_tasks, sub: `${metrics?.activity.tasks_today} today`, icon: CheckSquare, color: 'text-emerald-400' },
    { name: 'Monthly Revenue', value: `$${metrics?.revenue.revenue_this_month}`, sub: 'From deposits', icon: TrendingUp, color: 'text-cyan-400' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div>
        <h2 className="text-3xl font-bold text-slate-100">System Overview</h2>
        <p className="text-slate-400 mt-1">Real-time platform performance and growth metrics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => (
          <div key={stat.name} className="glass-card stat-card-gradient-1 p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-slate-400">{stat.name}</p>
                <h3 className="text-2xl font-bold mt-2 text-slate-100">{stat.value}</h3>
                <p className="text-xs text-slate-500 mt-1">{stat.sub}</p>
              </div>
              <div className={`p-2 bg-slate-950/40 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold flex items-center">
              <Activity className="w-5 h-5 mr-2 text-indigo-400" />
              System Health
            </h3>
          </div>
          <div className="space-y-4">
            <HealthItem label="PostgreSQL" status={metrics?.system.database_status} />
            <HealthItem label="Redis Cache" status={metrics?.system.redis_status} />
            <HealthItem label="Celery Workers" status={metrics?.system.celery_workers ? 'healthy' : 'warning'} info={`${metrics?.system.celery_workers} active`} />
          </div>
        </div>

        <div className="glass-card p-6 bg-gradient-to-br stat-card-gradient-2">
          <h3 className="text-lg font-semibold mb-4">Platform Insights</h3>
          <p className="text-sm text-slate-400 mb-6">
            Platform usage is trending upward by 12% compared to last week. Top features used today:
            <span className="text-indigo-300 ml-1 italic">Audio Transcription, Semantic Search.</span>
          </p>
          <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors">
            View Analytics Detail
          </button>
        </div>
      </div>
    </div>
  );
}

function HealthItem({ label, status, info }: { label: string; status?: string; info?: string }) {
  const isHealthy = status === 'healthy';
  return (
    <div className="flex items-center justify-between p-3 bg-slate-950/30 rounded-lg border border-slate-800/30">
      <span className="text-sm text-slate-300 font-medium">{label}</span>
      <div className="flex items-center space-x-2">
        {info && <span className="text-xs text-slate-500">{info}</span>}
        <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-amber-500'}`} />
        <span className={`text-xs font-semibold uppercase tracking-wider ${isHealthy ? 'text-emerald-500' : 'text-amber-500'}`}>
          {status}
        </span>
      </div>
    </div>
  );
}
