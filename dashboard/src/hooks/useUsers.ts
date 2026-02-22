import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export interface User {
    id: string;
    name: string;
    email: string;
    is_admin: boolean;
    plan_id: string;
    plan_name: string;
    balance: number;
    usage_stats: any;
    is_deleted: boolean;
    last_login: number;
}

export const useUsers = (page = 0, limit = 20, search = '') => {
    return useQuery({
        queryKey: ['users', page, limit, search],
        queryFn: async () => {
            const { data } = await api.get('/admin/users', {
                params: { skip: page * limit, limit, q: search },
            });
            return data;
        },
    });
};

export const usePromoteUser = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ userId, level }: { userId: string; level: string }) => {
            const { data } = await api.post(`/admin/users/${userId}/make-admin`, null, {
                params: { level }
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
        },
        onError: (error: Error) => {
            console.error('Failed to promote user:', error.message);
        },
    });
};

export const useRevokeAdmin = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (userId: string) => {
            const { data } = await api.post(`/admin/users/${userId}/remove-admin`);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
        },
        onError: (error: Error) => {
            console.error('Failed to revoke admin:', error.message);
        },
    });
};
