/**
 * AI Call Analytics — Global Application Constants, Visual Palette & Dual-Indicator Maps.
 * Formulated for clean, warm-neutral light mode with high-contrast accessibility.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const API_V1 = `${API_BASE_URL}/api/v1`

/**
 * Deliberate 6-tier categorical data visualization palette for light backgrounds.
 */
export const CHART_PALETTE = {
  primary: '#6D5AE6',   // Sophisticated Violet / Plum (Primary)
  success: '#10B981',   // Emerald Green (Completed / Low Risk)
  warning: '#F59E0B',   // Warm Amber (Processing / Medium Risk)
  danger: '#EF4444',    // Crimson Red (Failed / High Risk)
  sky: '#0EA5E9',       // Sky Blue (Acoustic / Alternate Speaker)
  violet: '#8B5CF6',    // Iris (Topic / Cluster)
  neutral: '#94A3B8',   // Slate Neutral (Background / Outliers)
} as const

export const STATUS_CONFIG: Record<
  string,
  { label: string; icon: string; bgClass: string; textClass: string; borderClass: string }
> = {
  COMPLETED: {
    label: 'COMPLETED',
    icon: '✓',
    bgClass: 'bg-emerald-50',
    textClass: 'text-emerald-700',
    borderClass: 'border-emerald-200',
  },
  PROCESSING: {
    label: 'PROCESSING',
    icon: '●',
    bgClass: 'bg-amber-50',
    textClass: 'text-amber-700',
    borderClass: 'border-amber-200',
  },
  PARTIAL: {
    label: 'PARTIAL',
    icon: '▲',
    bgClass: 'bg-violet-50',
    textClass: 'text-violet-700',
    borderClass: 'border-violet-200',
  },
  QUEUED: {
    label: 'QUEUED',
    icon: '○',
    bgClass: 'bg-neutral-100',
    textClass: 'text-neutral-600',
    borderClass: 'border-neutral-200',
  },
  UPLOADED: {
    label: 'UPLOADED',
    icon: '↑',
    bgClass: 'bg-violet-50',
    textClass: 'text-violet-700',
    borderClass: 'border-violet-200',
  },
  FAILED: {
    label: 'FAILED',
    icon: '✕',
    bgClass: 'bg-rose-50',
    textClass: 'text-rose-700',
    borderClass: 'border-rose-200',
  },
}

export const SENTIMENT_CONFIG: Record<
  string,
  { label: string; symbol: string; bgClass: string; textClass: string; borderClass: string }
> = {
  positive: {
    label: 'POSITIVE',
    symbol: '▲',
    bgClass: 'bg-emerald-50',
    textClass: 'text-emerald-700',
    borderClass: 'border-emerald-200',
  },
  neutral: {
    label: 'NEUTRAL',
    symbol: '―',
    bgClass: 'bg-neutral-100',
    textClass: 'text-neutral-600',
    borderClass: 'border-neutral-200',
  },
  negative: {
    label: 'NEGATIVE',
    symbol: '▼',
    bgClass: 'bg-rose-50',
    textClass: 'text-rose-700',
    borderClass: 'border-rose-200',
  },
}

export const RISK_CONFIG: Record<
  string,
  { label: string; symbol: string; bgClass: string; textClass: string; borderClass: string }
> = {
  low: {
    label: 'LOW RISK',
    symbol: '▼',
    bgClass: 'bg-emerald-50',
    textClass: 'text-emerald-700',
    borderClass: 'border-emerald-200',
  },
  medium: {
    label: 'MEDIUM RISK',
    symbol: '●',
    bgClass: 'bg-amber-50',
    textClass: 'text-amber-700',
    borderClass: 'border-amber-200',
  },
  high: {
    label: 'HIGH RISK',
    symbol: '▲',
    bgClass: 'bg-rose-50',
    textClass: 'text-rose-700',
    borderClass: 'border-rose-200',
  },
}

export const POLLING_INTERVALS = {
  CALL_PROCESSING: 3000,
  SYSTEM_HEALTH: 30000,
} as const
