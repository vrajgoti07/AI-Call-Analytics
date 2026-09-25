/**
 * AI Call Analytics — General UI and Formatting Utilities.
 */

export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}

/**
 * Format total seconds into mm:ss or hh:mm:ss format.
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return '--:--'
  const s = Math.max(0, Math.floor(seconds))
  const hrs = Math.floor(s / 3600)
  const mins = Math.floor((s % 3600) / 60)
  const secs = s % 60

  if (hrs > 0) {
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

/**
 * Format timestamp for player seeking (e.g. 01:24).
 */
export function formatTimestamp(seconds: number): string {
  return formatDuration(seconds)
}

/**
 * Format ISO datetime string to clean localized display.
 */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '--'
  try {
    const d = new Date(isoString)
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoString
  }
}

/**
 * Format percentage (0.0 - 1.0 or 0 - 100) to clean "XX.X%" string.
 */
export function formatPercentage(val: number | null | undefined, isFraction = true): string {
  if (val === null || val === undefined || isNaN(val)) return '--%'
  const pct = isFraction ? val * 100 : val
  return `${pct.toFixed(1)}%`
}

/**
 * Format cosine similarity (0.0 to 1.0) into a readable score.
 */
export function formatSimilarity(score: number): string {
  return (score * 100).toFixed(0) + '%'
}

/**
 * Format raw byte size to KB/MB.
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}
