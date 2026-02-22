import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export interface Wallet {
    id: string;
    user_id: string;
    balance: number;
    currency: string;
    is_frozen: boolean;
    monthly_limit?: number;
    used_this_month?: number;
    user_email?: string;
    user_name?: string;
}

export const useWallets = (page = 0, limit = 20, search = '') => {
    return useQuery({
        queryKey: ['wallets', page, limit, search],
        queryFn: async () => {
            const { data } = await api.get('/admin/wallets', {
                params: { skip: page * limit, limit, q: search },
            });
            return data.wallets || [];
        },
    });
};

export const useRevenueReport = (startDate: number, endDate: number) => {
    return useQuery({
        queryKey: ['revenue-report', startDate, endDate],
        queryFn: async () => {
            const { data } = await api.get('/admin/reports/revenue', {
                params: { start_date: startDate, end_date: endDate },
            });
            return data;
        },
    });
};

export const useCreditWallet = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ userId, amount, reason }: { userId: string; amount: number; reason: string }) => {
            const { data } = await api.post(`/admin/wallets/${userId}/credit`, null, {
                params: { amount, reason }
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['wallets'] });
            queryClient.invalidateQueries({ queryKey: ['users'] });
        },
        onError: (error: Error) => {
            console.error('Failed to credit wallet:', error.message);
        },
    });
};

export const useDebitWallet = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ userId, amount, reason }: { userId: string; amount: number; reason: string }) => {
            const { data } = await api.post(`/admin/wallets/${userId}/debit`, null, {
                params: { amount, reason }
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['wallets'] });
            queryClient.invalidateQueries({ queryKey: ['users'] });
        },
        onError: (error: Error) => {
            console.error('Failed to debit wallet:', error.message);
        },
    });
};

export const useToggleFreeze = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (userId: string) => {
            const { data } = await api.post(`/admin/wallets/${userId}/toggle-freeze`);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['wallets'] });
        },
        onError: (error: Error) => {
            console.error('Failed to toggle wallet freeze:', error.message);
        },
    });
};
