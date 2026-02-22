import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
    id: string;
    email: string;
    name: string;
    is_admin: boolean;
}

interface AuthState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    setAuth: (user: User, token: string) => void;
    checkAuth: () => Promise<void>;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            isLoading: true,
            setAuth: (user, token) => set({ user, token, isLoading: false }),
            checkAuth: async () => {
                const { token } = useAuthStore.getState();
                if (!token) {
                    set({ user: null, token: null, isLoading: false });
                    return;
                }

                // Basic JWT expiry check (M-12)
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    if (payload.exp && payload.exp * 1000 < Date.now()) {
                        set({ user: null, token: null, isLoading: false });
                        return;
                    }
                } catch (e) {
                    // Invalid token format
                    set({ user: null, token: null, isLoading: false });
                    return;
                }

                const api = (await import('@/lib/api')).default;
                try {
                    const { data } = await api.get('/users/me');
                    set({ user: data, isLoading: false });
                } catch (error) {
                    set({ user: null, token: null, isLoading: false });
                }
            },
            logout: () => {
                set({ user: null, token: null, isLoading: false });
                if (typeof window !== 'undefined') {
                    localStorage.removeItem('admin_token');
                }
            },
        }),
        {
            name: 'auth-storage',
        }
    )
);
