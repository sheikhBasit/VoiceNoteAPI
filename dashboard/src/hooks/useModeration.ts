import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export const useAuditNotes = (page = 0, limit = 20) => {
    return useQuery({
        queryKey: ['audit-notes', page, limit],
        queryFn: async () => {
            const { data } = await api.get('/admin/content/notes', {
                params: { skip: page * limit, limit }
            });
            return data;
        }
    });
};

export const useAuditTasks = (page = 0, limit = 20) => {
    return useQuery({
        queryKey: ['audit-tasks', page, limit],
        queryFn: async () => {
            const { data } = await api.get('/admin/content/tasks', {
                params: { skip: page * limit, limit }
            });
            return data;
        }
    });
};

export const useDeleteNote = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (noteId: string) => {
            const { data } = await api.delete(`/admin/content/notes/${noteId}`);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['audit-notes'] });
        }
    });
};
