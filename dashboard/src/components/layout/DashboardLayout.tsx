'use client';

import { useAuthStore } from "@/store/useAuthStore";
import { Sidebar } from "./Sidebar";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu } from 'lucide-react';

export function DashboardLayout({ children }: { children: React.ReactNode }) {
    const { user, logout, checkAuth, isLoading } = useAuthStore();
    const router = useRouter();
    const pathname = usePathname();
    const [sidebarOpen, setSidebarOpen] = useState(false);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    useEffect(() => {
        if (!isLoading && !user && pathname !== '/login') {
            router.push('/login');
        }
    }, [user, pathname, router, isLoading]);

    if (isLoading && pathname !== '/login') {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
            </div>
        );
    }

    if (pathname === '/login') {
        return <>{children}</>;
    }

    return (
        <div className="flex h-screen bg-slate-950 overflow-hidden font-inter">
            <Sidebar
                user={user}
                onLogout={logout}
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
            />

            {/* Mobile top bar with hamburger */}
            <div className="fixed top-0 left-0 right-0 z-30 lg:hidden bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 px-4 py-3">
                <button
                    onClick={() => setSidebarOpen(true)}
                    className="p-1.5 text-slate-400 hover:text-slate-200 transition-colors"
                >
                    <Menu className="w-6 h-6" />
                </button>
            </div>

            <main className="flex-1 overflow-y-auto custom-scrollbar p-8 pt-16 lg:pt-8 lg:ml-64 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900/50 via-slate-950 to-black">
                {children}
            </main>
        </div>
    );
}
