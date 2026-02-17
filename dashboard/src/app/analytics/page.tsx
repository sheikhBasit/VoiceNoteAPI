'use client';

import { useState } from 'react';
import { useUsageAnalytics, useGrowthAnalytics, useRevenueAnalytics } from "@/hooks/useAnalytics";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area,
    PieChart,
    Pie,
    Cell
} from 'recharts';
import {
    TrendingUp,
    Users,
    DollarSign,
    Calendar,
    Filter,
    Download
} from 'lucide-react';

const COLORS = ['#6366f1', '#06b6d4', '#8b5cf6', '#ec4899', '#f59e0b'];

export default function AnalyticsPage() {
    const [range] = useState(() => {
        const end = Date.now();
        const start = end - 30 * 24 * 60 * 60 * 1000;
        return { start, end };
    });

    const { data: usage } = useUsageAnalytics(range.start, range.end);
    const { data: growth } = useGrowthAnalytics();
    const { data: revenue } = useRevenueAnalytics(range.start, range.end);

    const usageData = usage?.usage_by_period ? Object.entries(usage.usage_by_period).map(([date, vals]: any) => ({
        date,
        audio: Math.round(vals.audio_minutes),
        api: vals.api_calls
    })) : [];

    const tierData = growth?.tier_distribution ? Object.entries(growth.tier_distribution).map(([name, value]) => ({
        name, value
    })) : [];

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold text-slate-100">Analytics Hub</h2>
                    <p className="text-slate-400 mt-1">Deep dives into platform usage, growth, and financial health.</p>
                </div>
                <div className="flex space-x-3">
                    <button className="flex items-center space-x-2 px-4 py-2 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg text-sm font-medium hover:bg-slate-800 transition-colors">
                        <Calendar className="w-4 h-4" />
                        <span>Last 30 Days</span>
                    </button>
                    <button className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-indigo-500/20">
                        <Download className="w-4 h-4" />
                        <span>Export Report</span>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Usage Trend */}
                <div className="lg:col-span-2 glass-card p-6">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-lg font-semibold flex items-center">
                            <TrendingUp className="w-5 h-5 mr-3 text-cyan-400" />
                            Usage Patterns (Audio Minutes)
                        </h3>
                        <div className="flex items-center space-x-2 text-xs text-slate-500">
                            <div className="w-3 h-3 bg-indigo-500 rounded-sm" />
                            <span>Minutes</span>
                        </div>
                    </div>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={usageData}>
                                <defs>
                                    <linearGradient id="colorUsage" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                                <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334115', borderRadius: '8px' }}
                                    itemStyle={{ fontSize: '12px' }}
                                />
                                <Area type="monotone" dataKey="audio" stroke="#6366f1" fillOpacity={1} fill="url(#colorUsage)" strokeWidth={2} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* User Tiers Pie Chart */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-8 flex items-center">
                        <Users className="w-5 h-5 mr-3 text-purple-400" />
                        Tier Distribution
                    </h3>
                    <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={tierData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {tierData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="mt-4 space-y-3">
                        {tierData.map((item, i) => (
                            <div key={item.name} className="flex justify-between items-center px-4 py-2 bg-slate-950/30 rounded-lg">
                                <div className="flex items-center space-x-2">
                                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                                    <span className="text-xs text-slate-300 font-medium">{item.name}</span>
                                </div>
                                <span className="text-xs font-bold text-slate-100">{item.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="glass-card p-6 border-emerald-500/10 bg-emerald-500/[0.01]">
                    <h3 className="text-lg font-semibold mb-6 flex items-center">
                        <DollarSign className="w-5 h-5 mr-3 text-emerald-400" />
                        Revenue Snapshot
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                        <MetricBox label="Net Revenue" value={`$${revenue?.net_revenue || 0}`} />
                        <MetricBox label="ARPU" value={`$${revenue?.arpu || 0}`} />
                        <MetricBox label="Transactions" value={revenue?.transaction_count || 0} />
                    </div>
                </div>

                <div className="glass-card p-6 bg-slate-900/20">
                    <h3 className="text-lg font-semibold mb-4">Retention & Growth</h3>
                    <div className="flex justify-between items-center p-4 bg-slate-950/40 rounded-xl border border-slate-800">
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wider font-bold">Retention Rate</p>
                            <h4 className="text-2xl font-bold text-slate-100 mt-1">{growth?.retention.retention_rate_percent}%</h4>
                        </div>
                        <div className="h-12 w-32">
                            {/* Sparkline could go here */}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function MetricBox({ label, value }: { label: string; value: string | number }) {
    return (
        <div className="p-4 bg-slate-900/40 rounded-xl border border-slate-800/50">
            <p className="text-xs text-slate-500 mb-1">{label}</p>
            <p className="text-xl font-bold text-slate-100">{value}</p>
        </div>
    );
}
