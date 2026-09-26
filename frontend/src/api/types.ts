/**
 * AI Call Analytics — Frontend TypeScript Domain Contracts.
 * Strictly mirrors Phase 10 FastAPI Pydantic schemas.
 */

export interface PaginationMeta {
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AudioFileResponse {
  id: string
  call_id: string
  filename: string
  size: number
  duration: number | null
  sample_rate: number
  channels: number
  mime_type: string
  created_at: string
}

export interface CallCreate {
  external_id?: string
  language?: string
}

export interface CallResponse {
  id: string
  external_id: string | null
  status: 'UPLOADED' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | string
  duration: number | null
  language: string | null
  created_at: string
  updated_at: string
  audio_file: AudioFileResponse | null
}

export interface CallDetailResponse extends CallResponse {
  has_transcript: boolean
  has_risk_analysis: boolean
  latest_job_id: string | null
}

export interface CallListResponse {
  items: CallResponse[]
  pagination: PaginationMeta
}

export interface SkippedFileInfo {
  filename: string
  reason: string
}

export interface BulkIngestResponse {
  total_files: number
  processed_count: number
  created_calls: CallResponse[]
  skipped_files: SkippedFileInfo[]
}

export interface ReportGenerateRequest {
  report_type?: 'INDIVIDUAL_CALL' | 'COMPANY_ANALYTICS' | 'DATE_RANGE' | string
  call_id?: string
  date_from?: string
  date_to?: string
  title?: string
}

export interface ReportResponse {
  id: string
  company_id: string
  call_id: string | null
  title: string
  report_type: string
  status: 'PENDING' | 'GENERATING' | 'COMPLETED' | 'FAILED' | string
  date_from: string | null
  date_to: string | null
  has_pdf: boolean
  has_json: boolean
  has_csv: boolean
  summary_data: Record<string, unknown> | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ReportListResponse {
  items: ReportResponse[]
  pagination: PaginationMeta
}

export interface ReportListParams {
  call_id?: string
  report_type?: string
  page?: number
  page_size?: number
}

export interface CallListParams {
  status?: string
  language?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface TranscriptTurnResponse {
  id: string
  speaker_id: string
  start_time: number
  end_time: number
  text: string
  sequence_number: number
  sentiment: {
    label: 'positive' | 'neutral' | 'negative' | string
    score: number
  } | null
  intent: {
    intent: string
    confidence: number
  } | null
  entities: Array<{
    entity_type: string
    text?: string
    masked_text?: string
    start?: number
    end?: number
  }> | null
}

export interface TranscriptResponse {
  id: string
  call_id: string
  language: string
  text: string
  duration: number | null
  model: string
  model_version: string
  created_at: string
  turn_count: number
}

export interface TranscriptTurnListResponse {
  call_id: string
  transcript_id: string
  items: TranscriptTurnResponse[]
  pagination: PaginationMeta
}

export interface StartAnalysisRequest {
  pipeline_stages?: string[]
  force_reprocess?: boolean
}

export interface AnalysisStatusResponse {
  call_id: string
  status: string
  progress: number
  current_stage: string | null
  stages: Record<string, string>
  job_id: string | null
  error_code?: string | null
  error_message?: string | null
}

export interface AnalysisSummaryResponse {
  call_id: string
  status: string
  duration: number | null
  transcript_summary: string | null
  speaker_count: number
  dominant_sentiment: string | null
  primary_intent: string | null
  risk_level: 'low' | 'medium' | 'high' | string | null
  risk_score: number | null
  theme_count: number
  themes: string[]
  created_at: string
}

export interface RiskFactor {
  feature?: string
  display_name?: string
  value?: number
  contribution?: number
  score?: number
  factor?: string
  name?: string
  description?: string
  [key: string]: unknown
}

export interface EscalationRiskResponse {
  id: string
  call_id: string
  risk_score: number
  risk_probability: number
  risk_level: 'low' | 'medium' | 'high' | string
  model_type: string
  model_name: string
  model_version: string
  explanation: string
  top_factors: RiskFactor[]
  temporal_risk: Array<Record<string, unknown>>
  created_at: string
}

export interface SemanticSearchRequest {
  query: string
  top_k?: number
  similarity_threshold?: number
  call_id?: string
}

export interface SearchResultItem {
  chunk_id: number
  call_id: string
  text: string
  similarity: number
  start_time: number
  end_time: number
  speaker_ids: string[]
}

export interface SemanticSearchResponse {
  query: string
  total_results: number
  results: SearchResultItem[]
}

export interface ThemeItemResponse {
  id: string
  cluster_id: number
  title: string
  summary: string
  size: number
  top_keywords: string[]
  exemplar_turn_ids: number[]
}

export interface ThemeListResponse {
  run_id: string | null
  run_name: string | null
  total_themes: number
  noise_count: number | null
  noise_percentage: number | null
  silhouette_score: number | null
  themes: ThemeItemResponse[]
}

export interface JobResponse {
  id: string
  call_id: string
  task_id: string | null
  job_type: string
  status: 'PENDING' | 'STARTED' | 'PROCESSING' | 'SUCCESS' | 'FAILURE' | 'RETRY' | string
  progress: number
  current_stage: string | null
  stages: Record<string, unknown>
  error_code: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface JobListResponse {
  items: JobResponse[]
  pagination: PaginationMeta
}

export interface EvaluationComponentResult {
  component: string
  evaluation_type: string
  status: 'PASSED' | 'WARNING' | 'FAILED' | string
  metrics: Record<string, unknown>
  sample_count: number
  dataset_name: string
  model_name: string
  model_version: string
  summary: string
  details?: Record<string, unknown>
}

export interface EvaluationResponse {
  evaluation_id: string
  timestamp: string
  git_commit: string | null
  components: Record<string, EvaluationComponentResult>
}
