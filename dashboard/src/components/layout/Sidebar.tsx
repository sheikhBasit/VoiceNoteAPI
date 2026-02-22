'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Users,
    BarChart3,
    ShieldAlert,
    Settings,
    Activity,
    CreditCard,
    FileText,
    Package,
    X
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'User Management', href: '/users', icon: Users },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'System Monitoring', href: '/system', icon: Activity },
    { name: 'Moderation', href: '/moderation', icon: ShieldAlert },
    { name: 'Billing', href: '/billing', icon: CreditCard },
    { name: 'Subscription Plans', href: '/plans', icon: Package },
    { name: 'Audit Logs', href: '/logs', icon: FileText },
    { name: 'Settings', href: '/settings', icon: Settings },
];

interface SidebarProps {
    user: any;
    onLogout: () => void;
    isOpen: boolean;
    onClose: () => void;
}

export function Sidebar({ user, onLogout, isOpen, onClose }: SidebarProps) {
    const pathname = usePathname();

    return (
        <>
            {/* Mobile backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/60 z-40 lg:hidden"
                    onClick={onClose}
                />
            )}

            <div
                className={cn(
                    "w-64 bg-slate-900 border-r border-slate-800 h-screen flex flex-col fixed left-0 top-0 z-50 transition-transform duration-300",
                    isOpen ? "translate-x-0" : "-translate-x-full",
                    "lg:translate-x-0"
                )}
            >
                <div className="p-6 flex items-center justify-between">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-indigo-500 bg-clip-text text-transparent">
                        VoiceNote Admin
                    </h1>
                    <button
                        onClick={onClose}
                        className="lg:hidden p-1 text-slate-400 hover:text-slate-200 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <nav className="flex-1 px-4 space-y-1 overflow-y-auto custom-scrollbar">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                onClick={onClose}
                                className={cn(
                                    "flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors group",
                                    isActive
                                        ? "bg-indigo-600/20 text-indigo-400"
                                        : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                                )}
                            >
                                <item.icon className={cn("w-5 h-5", isActive ? "text-indigo-400" : "group-hover:text-indigo-400 transition-colors")} />
                                <span className="font-medium text-sm">{item.name}</span>
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-slate-800 space-y-4">
                    <div className="flex items-center space-x-3 px-3 py-2">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-lg shadow-indigo-500/20">
                            {user?.name?.substring(0, 2).toUpperCase() || 'AD'}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-slate-200 truncate">{user?.name || 'Admin User'}</p>
                            <p className="text-[10px] text-slate-500 truncate uppercase tracking-wider font-bold">{user?.email || 'admin@voicenote.ai'}</p>
                        </div>
                    </div>

                    <button
                        onClick={onLogout}
                        className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition-all font-medium text-sm"
                    >
                        <ShieldAlert className="w-5 h-5" />
                        <span>Logout Session</span>
                    </button>
                </div>
            </div>
        </>
    );
}
