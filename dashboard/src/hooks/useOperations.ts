import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export const useActiveTasks = () => {
    return useQuery({
        queryKey: ['active-tasks'],
        queryFn: async () => {
            const { data } = await api.get('/admin/tasks/active');
            return data;
        },
        refetchInterval: 5000,
    });
};

export const useTransactions = (page = 0, limit = 20) => {
    return useQuery({
        queryKey: ['transactions', page, limit],
        queryFn: async () => {
            const { data } = await api.get('/admin/wallet/transactions', {
                params: { skip: page * limit, limit }
            });
            return data;
        }
    });
};

export const useRefundTransaction = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (transactionId: string) => {
            const { data } = await api.post(`/admin/wallet/transactions/${transactionId}/refund`);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['transactions'] });
        },
        onError: (error: Error) => {
            console.error('Failed to refund transaction:', error.message);
        },
    });
};
