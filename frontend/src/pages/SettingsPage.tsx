import {
  CheckCircle2,
  Cpu,
  RefreshCw,
  Server,
  Settings,
  XCircle,
} from 'lucide-react'
import { Button } from '../components/ui/Button'
import { useSystemHealth, useSystemReadiness } from '../hooks/useSystemHealth'
import { API_BASE_URL } from '../lib/constants'

export function SettingsPage() {
  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useSystemHealth()
  const { data: readiness, isLoading: readyLoading, refetch: refetchReady } = useSystemReadiness()

  const handleRefresh = () => {
    refetchHealth()
    refetchReady()
  }

  const isDbConnected = readiness?.dependencies?.database === 'connected'
  const isRedisConnected = readiness?.dependencies?.redis === 'connected'

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#E5E5E2]">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C] flex items-center gap-2">
            <Settings className="h-5 w-5 text-[#6D5AE6]" />
            System Configuration & Model Registry
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
            Backend infrastructure health, production AI model inventory, and operational parameters
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          isLoading={healthLoading || readyLoading}
          leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
        >
          Check Connectivity
        </Button>
      </div>

      {/* Infrastructure Connectivity */}
      <div className="rounded-xl border border-[#E5E5E2] bg-white p-5 shadow-xs space-y-4">
        <h3 className="text-sm font-semibold text-[#17181C] flex items-center gap-2">
          <Server className="h-4 w-4 text-[#6D5AE6]" />
          Backend Service Health Status
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
          {/* FastAPI Core */}
          <div className="p-4 rounded-lg bg-[#FAFAF9] border border-[#E5E5E2] space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[#60636B]">FastAPI Backend</span>
              {health?.status === 'ok' ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : (
                <XCircle className="h-4 w-4 text-rose-600" />
              )}
            </div>
            <div className="text-[#17181C] font-bold text-sm">
              {health?.status === 'ok' ? 'HEALTHY / ONLINE' : 'DISCONNECTED'}
            </div>
            <div className="text-[11px] text-[#60636B]">
              {health?.service || 'ai-call-analytics-backend'}
            </div>
          </div>

          {/* PostgreSQL + pgvector */}
          <div className="p-4 rounded-lg bg-[#FAFAF9] border border-[#E5E5E2] space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[#60636B]">PostgreSQL (pgvector)</span>
              {isDbConnected ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : (
                <XCircle className="h-4 w-4 text-rose-600" />
              )}
            </div>
            <div className="text-[#17181C] font-bold text-sm">
              {isDbConnected ? 'CONNECTED' : 'UNREACHABLE'}
            </div>
            <div className="text-[11px] text-[#60636B]">
              Tables, transcripts, vector index
            </div>
          </div>

          {/* Redis Broker */}
          <div className="p-4 rounded-lg bg-[#FAFAF9] border border-[#E5E5E2] space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[#60636B]">Redis Broker</span>
              {isRedisConnected ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : (
                <XCircle className="h-4 w-4 text-rose-600" />
              )}
            </div>
            <div className="text-[#17181C] font-bold text-sm">
              {isRedisConnected ? 'CONNECTED' : 'UNREACHABLE'}
            </div>
            <div className="text-[11px] text-[#60636B]">
              Celery task queue & caching
            </div>
          </div>
        </div>
      </div>

      {/* Production AI Model Registry */}
      <div className="rounded-xl border border-[#E5E5E2] bg-white p-5 shadow-xs space-y-4">
        <h3 className="text-sm font-semibold text-[#17181C] flex items-center gap-2">
          <Cpu className="h-4 w-4 text-[#6D5AE6]" />
          Active Production AI Model Inventory
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="border-b border-[#E5E5E2] bg-[#FAFAF9] text-[#60636B] text-[11px]">
              <tr>
                <th className="py-2.5 px-3 font-semibold font-sans">Pipeline Stage</th>
                <th className="py-2.5 px-3 font-semibold">Model Engine</th>
                <th className="py-2.5 px-3 font-semibold">Quantization / Type</th>
                <th className="py-2.5 px-3 font-semibold font-sans">Purpose</th>
                <th className="py-2.5 px-3 text-right font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EFEFEC]">
              <tr className="hover:bg-[#FAFAF9] transition-colors">
                <td className="py-3 px-3 font-semibold text-[#17181C] font-sans">ASR Transcription</td>
                <td className="py-3 px-3 text-[#6D5AE6]">faster-whisper-base.en</td>
                <td className="py-3 px-3 text-[#60636B]">CTranslate2 int8 (CPU)</td>
                <td className="py-3 px-3 text-[#60636B] font-sans">Acoustic speech-to-text</td>
                <td className="py-3 px-3 text-right text-emerald-700 font-bold">READY</td>
              </tr>
              <tr className="hover:bg-[#FAFAF9] transition-colors">
                <td className="py-3 px-3 font-semibold text-[#17181C] font-sans">Speaker Diarization</td>
                <td className="py-3 px-3 text-[#6D5AE6]">pyannote.audio + whisper aligner</td>
                <td className="py-3 px-3 text-[#60636B]">float32</td>
                <td className="py-3 px-3 text-[#60636B] font-sans">Speaker turn segmentation</td>
                <td className="py-3 px-3 text-right text-emerald-700 font-bold">READY</td>
              </tr>
              <tr className="hover:bg-[#FAFAF9] transition-colors">
                <td className="py-3 px-3 font-semibold text-[#17181C] font-sans">Intent Classifier</td>
                <td className="py-3 px-3 text-[#6D5AE6]">TF-IDF + LogisticRegression / SetFit</td>
                <td className="py-3 px-3 text-[#60636B]">Configured intent classes</td>
                <td className="py-3 px-3 text-[#60636B] font-sans">Customer intent detection</td>
                <td className="py-3 px-3 text-right text-emerald-700 font-bold">READY</td>
              </tr>
              <tr className="hover:bg-[#FAFAF9] transition-colors">
                <td className="py-3 px-3 font-semibold text-[#17181C] font-sans">Sentiment Analyzer</td>
                <td className="py-3 px-3 text-[#6D5AE6]">RoBERTa / VADER hybrid</td>
                <td className="py-3 px-3 text-[#60636B]">3-class polarity</td>
                <td className="py-3 px-3 text-[#60636B] font-sans">Customer & agent polarity</td>
                <td className="py-3 px-3 text-right text-emerald-700 font-bold">READY</td>
              </tr>
              <tr className="hover:bg-[#FAFAF9] transition-colors">
                <td className="py-3 px-3 font-semibold text-[#17181C] font-sans">Vector Embeddings</td>
                <td className="py-3 px-3 text-[#6D5AE6]">BAAI/bge-small-en-v1.5</td>
                <td className="py-3 px-3 text-[#60636B]">384 dimensions</td>
                <td className="py-3 px-3 text-[#60636B] font-sans">Semantic search & theme clustering</td>
                <td className="py-3 px-3 text-right text-emerald-700 font-bold">READY</td>
              </tr>
              <tr className="hover:bg-[#FAFAF9] transition-colors">
                <td className="py-3 px-3 font-semibold text-[#17181C] font-sans">Theme Discovery</td>
                <td className="py-3 px-3 text-[#6D5AE6]">UMAP + HDBSCAN + c-TF-IDF</td>
                <td className="py-3 px-3 text-[#60636B]">Unsupervised</td>
                <td className="py-3 px-3 text-[#60636B] font-sans">Caller topic clustering</td>
                <td className="py-3 px-3 text-right text-emerald-700 font-bold">READY</td>
              </tr>
              <tr className="hover:bg-[#FAFAF9] transition-colors">
                <td className="py-3 px-3 font-semibold text-[#17181C] font-sans">Escalation Risk</td>
                <td className="py-3 px-3 text-[#6D5AE6]">Multi-modal Escalation Detector</td>
                <td className="py-3 px-3 text-[#60636B]">Acoustic + Temporal NLP</td>
                <td className="py-3 px-3 text-[#60636B] font-sans">Supervisor alert early-warning</td>
                <td className="py-3 px-3 text-right text-emerald-700 font-bold">READY</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* API Endpoint Configuration */}
      <div className="p-5 rounded-xl border border-[#E5E5E2] bg-white shadow-xs space-y-3 font-mono text-xs">
        <h4 className="text-[#17181C] font-semibold font-sans">
          Client Environment Configuration
        </h4>
        <div className="flex justify-between items-center py-2 border-b border-[#E5E5E2]">
          <span className="text-[#60636B]">VITE_API_BASE_URL:</span>
          <span className="text-[#6D5AE6] font-bold">{API_BASE_URL}</span>
        </div>
        <div className="flex justify-between items-center py-2">
          <span className="text-[#60636B]">Security / PII Masking:</span>
          <span className="text-emerald-700 font-bold">ACTIVE (Privacy-Preserving NER)</span>
        </div>
      </div>
    </div>
  )
}
