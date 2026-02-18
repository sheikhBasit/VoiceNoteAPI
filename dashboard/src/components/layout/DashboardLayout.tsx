'use client';

import { useAuthStore } from "@/store/useAuthStore";
import { Sidebar } from "./Sidebar";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
    const { user, logout } = useAuthStore();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (!user && pathname !== '/login') {
            router.push('/login');
        }
    }, [user, pathname, router]);

    if (!user && pathname !== '/login') {
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
            <Sidebar user={user} onLogout={logout} />
            <main className="flex-1 overflow-y-auto custom-scrollbar p-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900/50 via-slate-950 to-black">
                {children}
            </main>
        </div>
    );
}
