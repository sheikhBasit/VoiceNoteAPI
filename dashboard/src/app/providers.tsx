'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState } from 'react';
import { ToastProvider } from '@/components/ui/Toast';

import { useAuthStore } from '@/store/useAuthStore';
import { useEffect } from 'react';

export default function Providers({ children }: { children: React.ReactNode }) {
    const { checkAuth, isLoading } = useAuthStore();

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 30 * 1000,
                retry: 1,
            },
        },
    }));

    return (
        <ToastProvider>
            <QueryClientProvider client={queryClient}>
                {isLoading ? (
                    <div className="fixed inset-0 bg-slate-950 flex items-center justify-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
                    </div>
                ) : (
                    <>
                        {children}
                        {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
                    </>
                )}
            </QueryClientProvider>
        </ToastProvider>
    );
}
