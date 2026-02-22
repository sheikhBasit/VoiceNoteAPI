'use client';

import { useState } from 'react';
import { useToast } from '@/components/ui/Toast';
import {
    useWallets,
    useRevenueReport,
    useCreditWallet,
    useDebitWallet,
    useToggleFreeze
} from "@/hooks/useBilling";
import {
    Wallet,
    TrendingUp,
    TrendingDown,
    DollarSign,
    History,
    RefreshCw,
    PlusCircle,
    MinusCircle,
    Lock,
    Unlock,
    AlertCircle,
    ChevronLeft,
    ChevronRight,
    Search
} from 'lucide-react';

export default function BillingPage() {
    const toast = useToast();
    const [page, setPage] = useState(0);
    const [search, setSearch] = useState('');
    const now = Date.now();
    const thirtyDaysAgo = now - 30 * 24 * 60 * 60 * 1000;

    const { data: report, isLoading: isReportLoading } = useRevenueReport(thirtyDaysAgo, now);
    const { data: walletsData, isLoading: isWalletsLoading, error } = useWallets(page, 20, search);

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalConfig, setModalConfig] = useState<{ userId: string; type: 'credit' | 'debit' } | null>(null);
    const [amount, setAmount] = useState('');

    const creditMutation = useCreditWallet();
    const debitMutation = useDebitWallet();
    const freezeMutation = useToggleFreeze();

    const handleAction = () => {
        if (!modalConfig || !amount) return;
        const val = parseFloat(amount);
        if (isNaN(val)) return;

        if (modalConfig.type === 'credit') {
            creditMutation.mutate({ userId: modalConfig.userId, amount: val, reason: 'Admin Credit' }, {
                onSuccess: () => { setIsModalOpen(false); setAmount(''); },
                onError: (e) => toast.error("Failed: " + e.message)
            });
        } else {
            debitMutation.mutate({ userId: modalConfig.userId, amount: val, reason: 'Admin Debit' }, {
                onSuccess: () => { setIsModalOpen(false); setAmount(''); },
                onError: (e) => toast.error("Failed: " + e.message)
            });
        }
    };

    const handlePageChange = (newOffset: number) => {
        setPage(Math.max(0, page + newOffset));
    };

    if (error) {
        return (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 flex items-center space-x-3">
                <AlertCircle className="w-5 h-5" />
                <span>Error loading billing data. Please check your connection.</span>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold text-slate-100">Billing & Revenue</h2>
                    <p className="text-slate-400 mt-1">Monitor platform income, manage user credits, and track expenses.</p>
                </div>
                <div className="flex space-x-3">
                    <button
                        onClick={() => toast.info('Coming soon')}
                        className="flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium transition-colors border border-slate-700"
                    >
                        <History className="w-4 h-4" />
                        <span>Transaction Logs</span>
                    </button>
                    <button
                        onClick={() => toast.info('Coming soon')}
                        className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                        <PlusCircle className="w-4 h-4" />
                        <span>Manual Adjustment</span>
                    </button>
                </div>
            </div>

            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="glass-card p-6 border-l-4 border-l-emerald-500">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Revenue (30d)</p>
                            <h3 className="text-2xl font-bold text-slate-100 mt-1">
                                ${isReportLoading ? '...' : (report?.total_revenue?.toFixed(2) || '0.00')}
                            </h3>
                        </div>
                        <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500">
                            <TrendingUp className="w-5 h-5" />
                        </div>
                    </div>
                </div>

                <div className="glass-card p-6 border-l-4 border-l-indigo-500">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Net Profit</p>
                            <h3 className="text-2xl font-bold text-slate-100 mt-1">
                                ${isReportLoading ? '...' : (report?.net_revenue?.toFixed(2) || '0.00')}
                            </h3>
                        </div>
                        <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-500">
                            <DollarSign className="w-5 h-5" />
                        </div>
                    </div>
                </div>

                <div className="glass-card p-6 border-l-4 border-l-rose-500">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">AI Expenses</p>
                            <h3 className="text-2xl font-bold text-slate-100 mt-1">
                                ${isReportLoading ? '...' : (report?.total_expenses?.toFixed(2) || '0.00')}
                            </h3>
                        </div>
                        <div className="p-2 bg-rose-500/10 rounded-lg text-rose-500">
                            <TrendingDown className="w-5 h-5" />
                        </div>
                    </div>
                </div>

                <div className="glass-card p-6 border-l-4 border-l-amber-500">
                    <div className="flex justify-between items-start">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">ARPU</p>
                            <h3 className="text-2xl font-bold text-slate-100 mt-1">
                                ${isReportLoading ? '...' : (report?.arpu?.toFixed(2) || '0.00')}
                            </h3>
                        </div>
                        <div className="p-2 bg-amber-500/10 rounded-lg text-amber-500">
                            <RefreshCw className="w-5 h-5" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Wallets Table */}
            <div className="glass-card overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center">
                    <h3 className="font-semibold text-slate-200">User Wallets</h3>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Filter by user ID..."
                            value={search}
                            onChange={(e) => {
                                setSearch(e.target.value);
                                setPage(0);
                            }}
                            className="pl-10 pr-4 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 outline-none w-48"
                        />
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="border-b border-slate-800 bg-slate-950/20">
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">User ID</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Balance</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Monthly Usage</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {isWalletsLoading ? (
                                Array(5).fill(0).map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td colSpan={5} className="px-6 py-6 h-12 bg-slate-900/10"></td>
                                    </tr>
                                ))
                            ) : (
                                walletsData?.map((wallet: any) => (
                                    <tr key={wallet.id} className="hover:bg-slate-800/20 transition-colors group">
                                        <td className="px-6 py-4 text-sm font-mono text-slate-400">
                                            {wallet.user_id.substring(0, 8)}...
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center space-x-1.5 font-bold text-slate-100">
                                                <DollarSign className="w-3.5 h-3.5 text-emerald-500" />
                                                <span>{wallet.balance.toFixed(2)}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {wallet.monthly_limit != null ? (
                                                <div className="w-full max-w-[100px]">
                                                    <div className="flex justify-between text-[10px] mb-1">
                                                        <span className="text-slate-500">${wallet.used_this_month ?? 0}</span>
                                                        <span className="text-slate-400">${wallet.monthly_limit}</span>
                                                    </div>
                                                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full ${(wallet.used_this_month ?? 0) / wallet.monthly_limit > 0.9 ? 'bg-rose-500' : 'bg-indigo-500'}`}
                                                            style={{ width: `${Math.min(100, ((wallet.used_this_month ?? 0) / wallet.monthly_limit) * 100)}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            ) : (
                                                <span className="text-xs text-slate-600">N/A</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${wallet.is_frozen ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'}`}>
                                                {wallet.is_frozen ? 'Frozen' : 'Active'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end space-x-2">
                                                <button
                                                    onClick={() => {
                                                        setModalConfig({ userId: wallet.user_id, type: 'credit' });
                                                        setIsModalOpen(true);
                                                    }}
                                                    disabled={creditMutation.isPending}
                                                    className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-emerald-400 transition-colors disabled:opacity-30"
                                                    title="Add Credit"
                                                >
                                                    <PlusCircle className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        setModalConfig({ userId: wallet.user_id, type: 'debit' });
                                                        setIsModalOpen(true);
                                                    }}
                                                    disabled={debitMutation.isPending}
                                                    className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-rose-400 transition-colors disabled:opacity-30"
                                                    title="Deduct Credit"
                                                >
                                                    <MinusCircle className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => freezeMutation.mutate(wallet.user_id)}
                                                    disabled={freezeMutation.isPending}
                                                    className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-amber-400 transition-colors disabled:opacity-30"
                                                    title={wallet.is_frozen ? "Unfreeze" : "Freeze"}
                                                >
                                                    {wallet.is_frozen ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="glass-card max-w-sm w-full p-6 shadow-2xl border-indigo-500/30">
                        <h3 className="text-lg font-bold text-slate-100 flex items-center">
                            {modalConfig?.type === 'credit' ? <PlusCircle className="w-5 h-5 mr-3 text-emerald-500" /> : <MinusCircle className="w-5 h-5 mr-3 text-rose-500" />}
                            {modalConfig?.type === 'credit' ? 'Credit Wallet' : 'Debit Wallet'}
                        </h3>
                        <p className="text-sm text-slate-400 mt-2">Adjust balance for user <span className="font-mono text-indigo-400">{modalConfig?.userId.substring(0, 8)}...</span></p>

                        <div className="mt-6 space-y-4">
                            <div>
                                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Amount ($)</label>
                                <input
                                    autoFocus
                                    type="number"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                    placeholder="0.00"
                                    className="w-full mt-1 px-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-100 focus:ring-2 focus:ring-indigo-500 outline-none"
                                />
                            </div>
                        </div>

                        <div className="mt-8 flex space-x-3">
                            <button
                                onClick={() => setIsModalOpen(false)}
                                className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors border border-slate-700"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAction}
                                disabled={!amount || creditMutation.isPending || debitMutation.isPending}
                                className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all text-white shadow-lg ${modalConfig?.type === 'credit' ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-500/20' : 'bg-rose-600 hover:bg-rose-500 shadow-rose-500/20'} disabled:opacity-50`}
                            >
                                {creditMutation.isPending || debitMutation.isPending ? 'Processing...' : 'Confirm'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
