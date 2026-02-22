'use client';

import { useAuditNotes, useDeleteNote } from "@/hooks/useModeration";
import {
    ShieldAlert,
    Trash2,
    Eye,
    CheckCircle,
    Clock,
    Filter,
    MoreVertical,
    AlertCircle
} from 'lucide-react';

export default function ModerationPage() {
    const { data, isLoading, error } = useAuditNotes();
    const deleteMutation = useDeleteNote();

    if (error) {
        return (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 flex items-center space-x-3">
                <AlertCircle className="w-5 h-5" />
                <span>Failed to load moderation queue.</span>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold text-slate-100">Content Moderation</h2>
                    <p className="text-slate-400 mt-1">Review, flag, and manage user-generated content for platform safety.</p>
                </div>
                <div className="flex space-x-3 text-xs">
                    {/* TODO: implement Filter by Flag */}
                    <button disabled className="flex items-center space-x-2 px-3 py-1.5 bg-slate-900 border border-slate-800 text-slate-400 rounded-md hover:text-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                        <Filter className="w-3.5 h-3.5" />
                        <span>Filter by Flag</span>
                    </button>
                </div>
            </div>

            <div className="glass-card overflow-hidden">
                <div className="p-4 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Note Review Queue</h3>
                    <span className="px-2 py-0.5 bg-slate-800 text-slate-400 text-[10px] rounded-full font-bold">
                        {data?.total || 0} ITEMS
                    </span>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="border-b border-slate-800">
                                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Content Preview</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Creator</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Flags</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Created</th>
                                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40">
                            {isLoading ? (
                                Array(3).fill(0).map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td colSpan={5} className="px-6 py-8 h-20 bg-slate-900/10"></td>
                                    </tr>
                                ))
                            ) : (
                                data?.notes?.map((note: any) => (
                                    <tr key={note.id} className="hover:bg-slate-800/10 transition-colors group">
                                        <td className="px-6 py-6 max-w-md">
                                            <p className="text-sm text-slate-200 line-clamp-2 leading-relaxed">
                                                {note.transcript || <span className="italic text-slate-500">No transcript available (Audio Only)</span>}
                                            </p>
                                        </td>
                                        <td className="px-6 py-6 text-sm text-slate-400 font-medium">
                                            {note.userName || 'Anonymous'}
                                        </td>
                                        <td className="px-6 py-6">
                                            <div className="flex items-center space-x-1.5">
                                                <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                                                <span className="text-xs text-slate-500">None detected</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-6">
                                            <div className="flex items-center text-xs text-slate-500">
                                                <Clock className="w-3 h-3 mr-2" />
                                                {new Date(note.timestamp).toLocaleDateString()}
                                            </div>
                                        </td>
                                        <td className="px-6 py-6 text-right">
                                            <div className="flex justify-end space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                {/* TODO: implement Review Context */}
                                                <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-indigo-400 transition-colors disabled:opacity-30" title="Review Context" disabled>
                                                    <Eye className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => deleteMutation.mutate(note.id)}
                                                    disabled={deleteMutation.isPending}
                                                    className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-red-400 transition-colors disabled:opacity-30"
                                                    title="Delete Content"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                                {/* TODO: implement Mark as Safe */}
                                                <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-emerald-400 transition-colors disabled:opacity-30" title="Mark as Safe" disabled>
                                                    <CheckCircle className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {!isLoading && (!data?.notes || data.notes.length === 0) && (
                    <div className="py-20 flex flex-col items-center justify-center text-slate-600">
                        <ShieldAlert className="w-12 h-12 mb-4 opacity-10" />
                        <p className="text-sm">Moderation queue is empty. Content safe.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
