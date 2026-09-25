/**
 * AI Call Analytics — Global UI State (Zustand).
 * Strictly limited to local client interaction states (sidebar, drawers, active tabs).
 */

import { create } from 'zustand'

interface UiState {
  sidebarCollapsed: boolean
  mobileDrawerOpen: boolean
  searchModalOpen: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  setMobileDrawerOpen: (open: boolean) => void
  setSearchModalOpen: (open: boolean) => void
}

export const useUiStore = create<UiState>((set) => ({
  sidebarCollapsed: false,
  mobileDrawerOpen: false,
  searchModalOpen: false,
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setMobileDrawerOpen: (open) => set({ mobileDrawerOpen: open }),
  setSearchModalOpen: (open) => set({ searchModalOpen: open }),
}))
