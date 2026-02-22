import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export interface AISettings {
    llm_model: string;
    llm_fast_model: string;
    temperature: number;
    max_tokens: number;
    top_p: number;
    stt_engine: string;
    groq_whisper_model: string;
    deepgram_model: string;
    semantic_analysis_prompt: string | null;
    updated_at: number;
    updated_by: string | null;
}

export const useAISettings = () => {
    return useQuery<AISettings>({
        queryKey: ['settings', 'ai'],
        queryFn: async () => {
            const { data } = await api.get('/admin/settings/ai');
            return data;
        },
    });
};

export const useUpdateAISettings = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (settings: Partial<AISettings>) => {
            const { data } = await api.patch('/admin/settings/ai', settings);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['settings', 'ai'] });
        },
    });
};

export interface APIKey {
    id: string;
    service_name: string;
    masked_key: string;
    priority: number;
    is_active: boolean;
    error_count?: number;
    last_error_at?: string | null;
    notes: string | null;
    created_at: number;
}

export const useAPIKeys = () => {
    return useQuery<APIKey[]>({
        queryKey: ['settings', 'api-keys'],
        queryFn: async () => {
            const { data } = await api.get('/admin/api-keys');
            return data.keys || [];
        },
    });
};
