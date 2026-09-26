import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { OverviewPage } from '../pages/OverviewPage'
import { CallsPage } from '../pages/CallsPage'
import { SearchPage } from '../pages/SearchPage'
import { ThemesPage } from '../pages/ThemesPage'
import { EvaluationPage } from '../pages/EvaluationPage'
import { JobsPage } from '../pages/JobsPage'
import { CallDetailPage } from '../pages/CallDetailPage'
import * as callsApi from '../api/calls'
import * as themesApi from '../api/themes'
import * as evaluationApi from '../api/evaluation'
import * as jobsApi from '../api/jobs'
import * as analysisApi from '../api/analysis'
import * as transcriptApi from '../api/transcript'
import * as riskApi from '../api/risk'

function renderPage(ui: React.ReactElement, initialRoute = '/') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Pages Integration & State Handling', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders OverviewPage with calls data and theme discovery', async () => {
    vi.spyOn(callsApi, 'listCalls').mockResolvedValue({
      items: [
        {
          id: 'call-101',
          external_id: 'CRM-101',
          status: 'COMPLETED',
          duration: 45.2,
          language: 'en',
          created_at: '2026-03-20T10:00:00Z',
          updated_at: '2026-03-20T10:05:00Z',
          audio_file: {
            id: 'af-1',
            call_id: 'call-101',
            filename: 'call_101.wav',
            size: 1024000,
            duration: 45.2,
            sample_rate: 16000,
            channels: 1,
            mime_type: 'audio/wav',
            created_at: '2026-03-20T10:00:00Z',
          },
        },
      ],
      pagination: { total: 1, page: 1, page_size: 100, total_pages: 1 },
    })

    vi.spyOn(themesApi, 'listThemes').mockResolvedValue({
      run_id: 'run-1',
      run_name: 'test_run',
      total_themes: 1,
      noise_count: 0,
      noise_percentage: 0,
      silhouette_score: 0.65,
      themes: [
        {
          id: 'th-1',
          cluster_id: 1,
          title: 'Card Decline Inquiries',
          summary: 'Callers inquiring about declined debit cards',
          size: 12,
          top_keywords: ['card', 'decline', 'declined'],
          exemplar_turn_ids: [1, 2],
        },
      ],
    })

    renderPage(<OverviewPage />)

    expect(screen.getByText('Executive Operations Overview')).toBeInTheDocument()
    expect(await screen.findByText('CRM-101')).toBeInTheDocument()
    expect(await screen.findByText('Card Decline Inquiries')).toBeInTheDocument()
  })

  it('renders CallsPage empty state when no calls are returned', async () => {
    vi.spyOn(callsApi, 'listCalls').mockResolvedValue({
      items: [],
      pagination: { total: 0, page: 1, page_size: 15, total_pages: 0 },
    })

    renderPage(<CallsPage />)

    expect(screen.getByText('Call Recordings Management')).toBeInTheDocument()
    expect(await screen.findByText('No calls match your criteria')).toBeInTheDocument()
  })

  it('renders ThemesPage empty state when no clusters exist', async () => {
    vi.spyOn(themesApi, 'listThemes').mockResolvedValue({
      run_id: null,
      run_name: null,
      total_themes: 0,
      noise_count: null,
      noise_percentage: null,
      silhouette_score: null,
      themes: [],
    })

    renderPage(<ThemesPage />)

    expect(screen.getByText('Customer Conversation Themes')).toBeInTheDocument()
    expect(await screen.findByText('No theme discovery runs found')).toBeInTheDocument()
  })

  it('renders SearchPage with search input and initial state', async () => {
    renderPage(<SearchPage />)

    expect(screen.getByText('Semantic Vector Search')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Type a natural language query/i)).toBeInTheDocument()
    expect(screen.getByText('Semantic Search Ready')).toBeInTheDocument()
  })

  it('renders EvaluationPage with real benchmark metrics', async () => {
    vi.spyOn(evaluationApi, 'getEvaluationResults').mockResolvedValue({
      evaluation_id: 'eval-run-9999',
      timestamp: '2026-03-22T14:30:00Z',
      git_commit: 'abc1234',
      components: {
        asr: {
          component: 'asr',
          evaluation_type: 'offline_benchmark',
          status: 'PASSED',
          metrics: { wer: 0.124, cer: 0.045 },
          sample_count: 50,
          dataset_name: 'MInDS-14',
          model_name: 'openai/whisper-tiny',
          model_version: '1.0.0',
          summary: 'ASR meets WER target threshold',
        },
        diarization: {
          component: 'diarization',
          evaluation_type: 'offline_benchmark',
          status: 'PASSED',
          metrics: { average_alignment_coverage: 0.98 },
          sample_count: 50,
          dataset_name: 'MInDS-14',
          model_name: 'pyannote/speaker-diarization',
          model_version: '3.1',
          summary: 'Diarization alignment validated',
        },
        intent: {
          component: 'intent',
          evaluation_type: 'offline_benchmark',
          status: 'PASSED',
          metrics: { macro_f1: 0.88, accuracy: 0.89, top3_accuracy: 0.98 },
          sample_count: 85,
          dataset_name: 'MInDS-14',
          model_name: 'SetFit-MInDS14-Classifier',
          model_version: '1.0',
          summary: 'Intent classifier evaluated on 14 banking intents',
          details: {
            per_class: {
              card_issues: { precision: 0.9, recall: 0.85, f1: 0.87, support: 10 },
            },
          },
        },
      },
    })

    renderPage(<EvaluationPage />)

    expect(await screen.findByText(/AI Model Evaluation & Quality Benchmarks/i)).toBeInTheDocument()
    expect(await screen.findByText('WER: 12.4%')).toBeInTheDocument()
    expect(await screen.findByText('card_issues')).toBeInTheDocument()
  })

  it('renders JobsPage with task execution queue', async () => {
    vi.spyOn(jobsApi, 'listJobs').mockResolvedValue({
      items: [
        {
          id: 'job-task-42',
          call_id: 'call-42-id',
          task_id: 'celery-42',
          job_type: 'full_pipeline',
          status: 'SUCCESS',
          progress: 100,
          current_stage: 'ESCALATION_RISK',
          stages: {},
          error_code: null,
          error_message: null,
          started_at: '2026-03-22T10:00:00Z',
          completed_at: '2026-03-22T10:02:00Z',
          created_at: '2026-03-22T10:00:00Z',
        },
      ],
      pagination: { total: 1, page: 1, page_size: 15, total_pages: 1 },
    })

    renderPage(<JobsPage />)

    expect(screen.getByText('Background Processing Jobs')).toBeInTheDocument()
    expect(await screen.findByText('job-task...')).toBeInTheDocument()
    expect(await screen.findByText('Call #call-42-')).toBeInTheDocument()
  })

  it('renders CallDetailPage error state on call not found', async () => {
    vi.spyOn(callsApi, 'getCall').mockRejectedValue(new Error("Call 'missing-id' not found"))
    vi.spyOn(transcriptApi, 'getTranscript').mockResolvedValue(null as any)
    vi.spyOn(transcriptApi, 'getTranscriptTurns').mockResolvedValue({ items: [], pagination: {} as any, call_id: '', transcript_id: '' })
    vi.spyOn(riskApi, 'getEscalationRisk').mockResolvedValue(null as any)
    vi.spyOn(analysisApi, 'getAnalysisSummary').mockResolvedValue(null as any)
    vi.spyOn(analysisApi, 'getAnalysisStatus').mockResolvedValue(null as any)

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/calls/missing-id']}>
          <Routes>
            <Route path="/calls/:callId" element={<CallDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByText('Failed to load call details')).toBeInTheDocument()
    expect(screen.getByText("Call 'missing-id' not found")).toBeInTheDocument()
  })
})
