import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export interface DashboardMetrics {
    users: {
        total: number;
        active: number;
        new_this_month: number;
        deleted: number;
        admins: number;
    };
    content: {
        total_notes: number;
        total_tasks: number;
        total_teams: number;
        total_folders: number;
    };
    activity: {
        notes_today: number;
        tasks_today: number;
        active_users_24h: number;
    };
    system: {
        database_status: string;
        redis_status: string;
        celery_workers: number;
    };
    revenue: {
        total_balance: number;
        revenue_this_month: number;
    };
}

export const useDashboardOverview = () => {
    return useQuery<DashboardMetrics>({
        queryKey: ['dashboard-overview'],
        queryFn: async () => {
            const { data } = await api.get('/admin/dashboard/overview');
            return data;
        },
        refetchInterval: 30000, // Refresh every 30s
    });
};

export const useRealtimeMetrics = () => {
    return useQuery({
        queryKey: ['realtime-metrics'],
        queryFn: async () => {
            const { data } = await api.get('/admin/metrics/realtime');
            return data;
        },
        refetchInterval: 5000, // Refresh every 5s for "real-time" feel
    });
};
