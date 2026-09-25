import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppRouter } from '../router'

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

describe('Application Routing', () => {
  it('renders Overview page on /overview', () => {
    renderWithProviders('/overview')
    expect(screen.getByText('Executive Operations Overview')).toBeInTheDocument()
  })

  it('renders Calls page on /calls', () => {
    renderWithProviders('/calls')
    expect(screen.getByText('Call Recordings Management')).toBeInTheDocument()
  })

  it('renders Search page on /search', () => {
    renderWithProviders('/search')
    expect(screen.getByText('Semantic Vector Search')).toBeInTheDocument()
  })

  it('renders Themes page on /themes', () => {
    renderWithProviders('/themes')
    expect(screen.getByText('Customer Conversation Themes')).toBeInTheDocument()
  })

  it('renders Risk page on /risk', () => {
    renderWithProviders('/risk')
    expect(screen.getByText('Escalation Risk Intelligence')).toBeInTheDocument()
  })

  it('renders Settings page on /settings', () => {
    renderWithProviders('/settings')
    expect(
      screen.getByText('System Configuration & Model Registry'),
    ).toBeInTheDocument()
  })

  it('renders 404 page for unknown routes', () => {
    renderWithProviders('/non-existent-route-xyz')
    expect(screen.getByText('Page Not Found')).toBeInTheDocument()
  })
})
