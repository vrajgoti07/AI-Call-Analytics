/**
AI Call Analytics — Authentication & Tenant Session Store.
 */

import { create } from 'zustand'
import { authApi, type UserResponse } from '../api/auth'

interface AuthState {
  token: string | null
  user: UserResponse | null
  isAuthenticated: boolean
  isInitializing: boolean
  setAuth: (token: string, user: UserResponse) => void
  logout: () => void
  updateUser: (user: UserResponse) => void
  switchWorkspace: (companyId: string) => Promise<void>
  initializeAuth: () => Promise<void>
}

const TOKEN_KEY = 'ai_call_token'
const USER_KEY = 'ai_call_user'

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem(TOKEN_KEY),
  user: (() => {
    try {
      const stored = localStorage.getItem(USER_KEY)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })(),
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  isInitializing: true,

  setAuth: (token: string, user: UserResponse) => {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    set({
      token,
      user,
      isAuthenticated: true,
      isInitializing: false,
    })
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      isInitializing: false,
    })
  },

  updateUser: (user: UserResponse) => {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    set({ user })
  },

  switchWorkspace: async (companyId: string) => {
    const res = await authApi.switchCompany(companyId)
    get().setAuth(res.access_token, res.user)
  },

  initializeAuth: async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      set({ isInitializing: false, isAuthenticated: false })
      return
    }

    try {
      const user = await authApi.getMe()
      set({
        user,
        isAuthenticated: true,
        isInitializing: false,
      })
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    } catch {
      // Invalid/expired token
      get().logout()
    }
  },
}))
