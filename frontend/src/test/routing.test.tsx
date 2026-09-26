import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppRouter } from '../router'
import { useAuthStore } from '../stores/authStore'
import { authApi, type UserResponse } from '../api/auth'

function renderWithProviders(initialRoute: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <AppRouter />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const mockUser: UserResponse = {
  id: 'user-1',
  email: 'test@example.com',
  full_name: 'Test Admin',
  role: 'ADMIN',
  is_active: true,
  company_id: 'comp-1',
  company: {
    id: 'comp-1',
    name: 'Acme Test Corp',
    slug: 'acme-test',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('Application Routing', () => {
  beforeEach(() => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue(mockUser)
    useAuthStore.getState().setAuth('mock-token', mockUser)
  })
  it('renders Overview page on /overview', async () => {
    renderWithProviders('/overview')
    expect(await screen.findByText('Executive Operations Overview')).toBeInTheDocument()
  })

  it('renders Calls page on /calls', async () => {
    renderWithProviders('/calls')
    expect(await screen.findByText('Call Recordings Management')).toBeInTheDocument()
  })

  it('renders Search page on /search', async () => {
    renderWithProviders('/search')
    expect(await screen.findByText('Semantic Vector Search')).toBeInTheDocument()
  })

  it('renders Themes page on /themes', async () => {
    renderWithProviders('/themes')
    expect(await screen.findByText('Customer Conversation Themes')).toBeInTheDocument()
  })

  it('renders Risk page on /risk', async () => {
    renderWithProviders('/risk')
    expect(await screen.findByText('Escalation Risk Intelligence')).toBeInTheDocument()
  })

  it('renders Settings page on /settings', async () => {
    renderWithProviders('/settings')
    expect(
      await screen.findByText('System Configuration & Model Registry'),
    ).toBeInTheDocument()
  })

  it('renders 404 page for unknown routes', async () => {
    renderWithProviders('/non-existent-route-xyz')
    expect(await screen.findByText('Page Not Found')).toBeInTheDocument()
  })
})
