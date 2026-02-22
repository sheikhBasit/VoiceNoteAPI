import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export interface AuditLog {
    id: string;
    admin_id: string;
    action: string;
    target_id: string | null;
    details: any;
    ip_address: string | null;
    user_agent: string | null;
    timestamp: number;
}

export const useAuditLogs = (offset = 0, limit = 50, filters: any = {}) => {
    return useQuery({
        queryKey: ['audit-logs', offset, limit, filters],
        queryFn: async () => {
            const { data } = await api.get('/admin/audit-logs', {
                params: { offset, limit, ...filters },
            });
            return data;
        },
    });
};
