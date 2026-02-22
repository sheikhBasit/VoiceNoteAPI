'use client';

import { useState } from 'react';
import { useUsers, usePromoteUser, useRevokeAdmin } from "@/hooks/useUsers";
import {
    Search,
    MoreVertical,
    UserPlus,
    ShieldCheck,
    ShieldOff,
    Info,
    ChevronLeft,
    ChevronRight,
    AlertCircle
} from 'lucide-react';

export default function UsersPage() {
    const [page, setPage] = useState(0);
    const [search, setSearch] = useState('');
    const { data, isLoading, error } = useUsers(page, 20, search);
    const promoteMutation = usePromoteUser();
    const revokeMutation = useRevokeAdmin();

    const handlePageChange = (newOffset: number) => {
        setPage(Math.max(0, page + newOffset));
    };

    if (error) {
        return (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 flex items-center space-x-3">
                <AlertCircle className="w-5 h-5" />
                <span>Error loading users. Please check your connection.</span>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold text-slate-100">User Management</h2>
                    <p className="text-slate-400 mt-1">Manage platform users, permissions, and oversight.</p>
                </div>
                <div className="flex space-x-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search users..."
                            value={search}
                            onChange={(e) => {
                                setSearch(e.target.value);
                                setPage(0);
                            }}
                            className="pl-10 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none w-64"
                        />
                    </div>
                    {/* TODO: implement Add Internal User */}
                    <button
                        disabled
                        className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <UserPlus className="w-4 h-4" />
                        <span>Add Internal User</span>
                    </button>
                </div>
            </div>

            <div className="glass-card overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="border-b border-slate-800 bg-slate-950/20">
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">User</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Tier</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Balance</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {isLoading ? (
                                Array(5).fill(0).map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td colSpan={5} className="px-6 py-8 h-16 bg-slate-900/10"></td>
                                    </tr>
                                ))
                            ) : (
                                data?.users.map((user: any) => (
                                    <tr key={user.id} className="hover:bg-slate-800/20 transition-colors group">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center space-x-3">
                                                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${user.is_admin ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'bg-slate-800 text-slate-400'}`}>
                                                    {user.name.substring(0, 1)}
                                                </div>
                                                <div>
                                                    <p className="text-sm font-medium text-slate-200">{user.name}</p>
                                                    <p className="text-xs text-slate-500">{user.email}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase ${user.plan_name === 'PREMIUM' ? 'bg-purple-500/20 text-purple-400' : 'bg-slate-800 text-slate-400'}`}>
                                                {user.plan_name}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center space-x-2">
                                                <div className={`w-1.5 h-1.5 rounded-full ${user.is_deleted ? 'bg-red-500' : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]'}`} />
                                                <span className="text-xs text-slate-300">{user.is_deleted ? 'Offline' : 'Active'}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-300">
                                            ${user.balance}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                {/* TODO: implement View Detail */}
                                                <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-indigo-400 transition-colors disabled:opacity-30" title="View Detail" disabled>
                                                    <Info className="w-4 h-4" />
                                                </button>
                                                {user.is_admin ? (
                                                    <button
                                                        onClick={() => revokeMutation.mutate(user.id)}
                                                        disabled={revokeMutation.isPending}
                                                        className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-amber-400 transition-colors disabled:opacity-30"
                                                        title="Revoke Admin"
                                                    >
                                                        <ShieldOff className="w-4 h-4" />
                                                    </button>
                                                ) : (
                                                    <button
                                                        onClick={() => promoteMutation.mutate({ userId: user.id, level: 'full' })}
                                                        disabled={promoteMutation.isPending}
                                                        className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-emerald-400 transition-colors disabled:opacity-30"
                                                        title="Make Admin"
                                                    >
                                                        <ShieldCheck className="w-4 h-4" />
                                                    </button>
                                                )}
                                                {/* TODO: implement more actions menu */}
                                                <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-30" disabled>
                                                    <MoreVertical className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="px-6 py-4 bg-slate-950/20 border-t border-slate-800 flex items-center justify-between">
                    <p className="text-xs text-slate-500">
                        Showing <span className="text-slate-300">{page * 20 + 1}</span> to <span className="text-slate-300">{(page + 1) * 20}</span> of <span className="text-slate-300">{data?.total || 0}</span> users
                    </p>
                    <div className="flex space-x-2">
                        <button
                            onClick={() => handlePageChange(-1)}
                            disabled={page === 0}
                            className="p-2 border border-slate-800 rounded-lg hover:bg-slate-900 disabled:opacity-30 transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => handlePageChange(1)}
                            disabled={!data || data.users.length < 20}
                            className="p-2 border border-slate-800 rounded-lg hover:bg-slate-900 disabled:opacity-30 transition-colors"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
