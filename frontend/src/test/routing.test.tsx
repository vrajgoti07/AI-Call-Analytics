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
