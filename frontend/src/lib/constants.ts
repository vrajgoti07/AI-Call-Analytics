/**
 * AI Call Analytics — Global Application Constants, Visual Palette & Dual-Indicator Maps.
 * Formulated for clean, warm-neutral light mode with high-contrast accessibility.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const API_V1 = `${API_BASE_URL}/api/v1`

/**
 * Deliberate 6-tier categorical data visualization palette for light backgrounds.
 * Respects strict separation:
 * - Brand Accent: Violet (#6D5AE6)
 * - Status / Risk Semantics: Emerald (Completed/Low), Amber (Processing/Med), Red (Failed/High)
 * - Categorical Facets: Multi-color non-semantic assignments (Sky, Iris, Rose, Emerald, Amber, Violet)
 */
export const CHART_PALETTE = {
  primary: '#6D5AE6',   // Sophisticated Violet / Plum (Brand)
  success: '#10B981',   // Emerald Green (Completed / Low Risk)
  warning: '#F59E0B',   // Warm Amber (Processing / Medium Risk)
  danger: '#EF4444',    // Crimson Red (Failed / High Risk)
  sky: '#0EA5E9',       // Sky Blue (Acoustic / Alternate Speaker)
  violet: '#8B5CF6',    // Iris (Topic / Cluster)
  neutral: '#94A3B8',   // Slate Neutral (Background / Outliers)
  status: {
    completed: '#10B981',
    processing: '#F59E0B',
    failed: '#EF4444',
    uploaded: '#6D5AE6',
    queued: '#94A3B8',
  },
  categorical: [
    '#6D5AE6',
    '#0EA5E9',
    '#F59E0B',
    '#10B981',
    '#8B5CF6',
    '#F43F5E',
  ],
} as const

/**
 * Standard Recharts tooltip styling matching design tokens.
 */
export const RECHARTS_TOOLTIP_STYLE: React.CSSProperties = {
  backgroundColor: '#FFFFFF',
  borderColor: '#E5E5E2',
  borderRadius: '8px',
  color: '#17181C',
  fontSize: '12px',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
  padding: '8px 12px',
}

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
