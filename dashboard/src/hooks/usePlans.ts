import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export interface ServicePlan {
    id: string;
    name: string;
    price_per_minute: number;
    monthly_credits: number;
    ai_models_allowed: string[];
    can_use_rag: boolean;
    max_storage_mb: number;
    google_play_product_id: string | null;
    description: string | null;
    monthly_note_limit: number;
    monthly_task_limit: number;
    features: Record<string, boolean>;
    is_active: boolean;
    created_at: number;
    updated_at: number;
}

export interface CreatePlanPayload {
    id: string;
    name: string;
    price_per_minute?: number;
    monthly_credits?: number;
    ai_models_allowed?: string[];
    can_use_rag?: boolean;
    max_storage_mb?: number;
    google_play_product_id?: string | null;
    description?: string | null;
    monthly_note_limit?: number;
    monthly_task_limit?: number;
    features?: Record<string, boolean>;
    is_active?: boolean;
}

export type UpdatePlanPayload = Partial<Omit<CreatePlanPayload, 'id'>>;

export const usePlans = () => {
    return useQuery<ServicePlan[]>({
        queryKey: ['plans'],
        queryFn: async () => {
            const { data } = await api.get('/admin/plans');
            return data;
        },
    });
};

export const useCreatePlan = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (plan: CreatePlanPayload) => {
            const { data } = await api.post('/admin/plans', plan);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
        },
    });
};

export const useUpdatePlan = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, updates }: { id: string; updates: UpdatePlanPayload }) => {
            const { data } = await api.patch(`/admin/plans/${id}`, updates);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
        },
    });
};

export const useDeletePlan = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (id: string) => {
            const { data } = await api.delete(`/admin/plans/${id}`);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['plans'] });
        },
    });
};
