import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export const useUsageAnalytics = (startDate: number, endDate: number, groupBy = 'day') => {
    return useQuery({
        queryKey: ['analytics-usage', startDate, endDate, groupBy],
        queryFn: async () => {
            const { data } = await api.get('/admin/analytics/usage', {
                params: { start_date: startDate, end_date: endDate, group_by: groupBy }
            });
            return data;
        }
    });
};

export const useGrowthAnalytics = () => {
    return useQuery({
        queryKey: ['analytics-growth'],
        queryFn: async () => {
            const { data } = await api.get('/admin/analytics/growth');
            return data;
        }
    });
};

export const useRevenueAnalytics = (startDate: number, endDate: number) => {
    return useQuery({
        queryKey: ['analytics-revenue', startDate, endDate],
        queryFn: async () => {
            const { data } = await api.get('/admin/analytics/revenue', {
                params: { start_date: startDate, end_date: endDate }
            });
            return data;
        }
    });
};
