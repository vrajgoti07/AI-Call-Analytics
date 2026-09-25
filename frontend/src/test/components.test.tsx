import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/StatusBadge'
import { SentimentBadge } from '../components/ui/SentimentBadge'
import { RiskBadge } from '../components/ui/RiskBadge'
import { MetricCard } from '../components/ui/MetricCard'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'

describe('Reusable UI Components', () => {
  it('renders Button with text and handles loading state', () => {
    const { rerender } = render(<Button>Analyze Call</Button>)
    expect(screen.getByText('Analyze Call')).toBeInTheDocument()

    rerender(<Button isLoading>Analyze Call</Button>)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('renders StatusBadge with dual indicators (text and symbol)', () => {
    render(<StatusBadge status="COMPLETED" />)
    expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    expect(screen.getByText('✓')).toBeInTheDocument()
  })

  it('renders SentimentBadge with polarity symbol and score', () => {
    render(<SentimentBadge sentiment="positive" score={0.85} />)
    expect(screen.getByText('POSITIVE')).toBeInTheDocument()
    expect(screen.getByText('▲')).toBeInTheDocument()
    expect(screen.getByText('(+0.85)')).toBeInTheDocument()
  })

  it('renders RiskBadge with dual indicator symbol and numerical score', () => {
    render(<RiskBadge level="high" score={86} />)
    expect(screen.getByText('HIGH RISK')).toBeInTheDocument()
    expect(screen.getByText('▲')).toBeInTheDocument()
    expect(screen.getByText('86')).toBeInTheDocument()
  })

  it('renders MetricCard with title, value, and subtext', () => {
    render(
      <MetricCard
        title="Total Calls"
        value={1248}
        subtext="All ingested recordings"
        trend={{ value: '+12%', isPositive: true }}
      />,
    )
    expect(screen.getByText('Total Calls')).toBeInTheDocument()
    expect(screen.getByText('1248')).toBeInTheDocument()
    expect(screen.getByText('All ingested recordings')).toBeInTheDocument()
    expect(screen.getByText('+12%')).toBeInTheDocument()
  })

  it('renders EmptyState with accessible title and description', () => {
    render(
      <EmptyState
        title="No calls found"
        description="Try adjusting your filters or upload a new recording."
      />,
    )
    expect(screen.getByText('No calls found')).toBeInTheDocument()
    expect(
      screen.getByText('Try adjusting your filters or upload a new recording.'),
    ).toBeInTheDocument()
  })

  it('renders ErrorAlert with title, message, and retry button', () => {
    let retried = false
    render(
      <ErrorAlert
        title="Network Disconnected"
        message="Unable to connect to backend service"
        onRetry={() => {
          retried = true
        }}
      />,
    )
    expect(screen.getByText('Network Disconnected')).toBeInTheDocument()
    expect(screen.getByText('Unable to connect to backend service')).toBeInTheDocument()
    const retryBtn = screen.getByRole('button', { name: /retry/i })
    expect(retryBtn).toBeInTheDocument()
    retryBtn.click()
    expect(retried).toBe(true)
  })
})
