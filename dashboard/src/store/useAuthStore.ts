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
    setAuth: (user: User, token: string) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            setAuth: (user, token) => set({ user, token }),
            logout: () => {
                set({ user: null, token: null });
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
