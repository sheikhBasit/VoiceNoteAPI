'use client';

import { useActiveTasks, useTransactions } from "@/hooks/useOperations";
import {
    Terminal,
    Cpu,
    CreditCard,
    Clock,
    CheckCircle2,
    XCircle,
    AlertCircle
} from 'lucide-react';

export default function OperationsPage() {
    const { data: activeTasks } = useActiveTasks();
    const { data: transactions, isLoading: isTxLoading } = useTransactions(0, 5);

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h2 className="text-3xl font-bold text-slate-100">Operations Center</h2>
                <p className="text-slate-400 mt-1">Monitor background tasks, workflows, and financial operations.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Active Tasks Table */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-6 flex items-center">
                        <Cpu className="w-5 h-5 mr-3 text-indigo-400" />
                        Active Tasks
                    </h3>
                    <div className="space-y-4">
                        {!activeTasks?.tasks || activeTasks.tasks.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-slate-500 border border-dashed border-slate-800 rounded-xl">
                                <CheckCircle2 className="w-8 h-8 mb-2 opacity-20" />
                                <p className="text-sm italic">All queues clear. No active tasks.</p>
                            </div>
                        ) : (
                            activeTasks.tasks.map((task: any) => (
                                <div key={task.id} className="flex items-center justify-between p-4 bg-slate-950/40 rounded-xl border border-slate-800/50">
                                    <div className="flex items-center space-x-4">
                                        <div className="p-2 bg-indigo-500/10 rounded-lg">
                                            <Terminal className="w-4 h-4 text-indigo-400" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-slate-200">{task.name}</p>
                                            <p className="text-[10px] text-slate-500 font-mono">{task.id.substring(0, 8)}...</p>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end">
                                        <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">{task.status}</span>
                                        <span className="text-[10px] text-slate-600 mt-0.5">{task.runtime}s runtime</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Recent Transactions */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-6 flex items-center">
                        <CreditCard className="w-5 h-5 mr-3 text-emerald-400" />
                        Recent Financial Logs
                    </h3>
                    <div className="space-y-4">
                        {transactions?.items?.length === 0 ? (
                            <p className="text-sm text-slate-500 italic py-8 text-center">No recent transactions.</p>
                        ) : (
                            transactions?.items?.map((tx: any) => (
                                <div key={tx.id} className="flex items-center justify-between p-3 hover:bg-slate-800/20 rounded-lg transition-colors">
                                    <div className="flex items-center space-x-3 text-sm">
                                        <div className={`p-1.5 rounded ${tx.type === 'DEPOSIT' ? 'text-emerald-500 bg-emerald-500/10' : 'text-slate-400 bg-slate-800'}`}>
                                            {tx.type === 'DEPOSIT' ? <DollarSign className="w-4 h-4" /> : <CreditCard className="w-4 h-4" />}
                                        </div>
                                        <div>
                                            <p className="text-slate-300 font-medium">{tx.userName || 'System'}</p>
                                            <p className="text-[10px] text-slate-500">{new Date(tx.created_at).toLocaleString()}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className={`text-sm font-bold ${tx.type === 'DEPOSIT' ? 'text-emerald-500' : 'text-slate-200'}`}>
                                            {tx.type === 'DEPOSIT' ? '+' : '-'}${tx.amount}
                                        </p>
                                        <p className="text-[10px] text-slate-600">{tx.status}</p>
                                    </div>
                                </div>
                            ))
                        )}
                        <button className="w-full py-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium border-t border-slate-800 mt-2 pt-4">
                            View All Transactions
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

function DollarSign(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <line x1="12" x2="12" y1="2" y2="22" />
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
    );
}
