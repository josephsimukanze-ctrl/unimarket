import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from './types'

interface AuthState {
  user: User | null
  access: string | null
  refresh: string | null
  isAuthenticated: boolean
  setAuth: (user: User, access: string, refresh: string) => void
  setUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      access: null,
      refresh: null,
      isAuthenticated: false,
      setAuth: (user, access, refresh) =>
        set({ user, access, refresh, isAuthenticated: true }),
      setUser: (user) => set({ user }),
      logout: () => set({ user: null, access: null, refresh: null, isAuthenticated: false }),
    }),
    {
      name: 'unimarket-auth',
    },
  ),
)
