import { describe, expect, it } from 'vitest'
import {
  cn,
  formatBytes,
  formatDateTime,
  formatDuration,
  formatPercentage,
  formatSimilarity,
  formatTimestamp,
} from '../lib/utils'

describe('Formatting Utilities', () => {
  it('formats duration in seconds to mm:ss format', () => {
    expect(formatDuration(0)).toBe('00:00')
    expect(formatDuration(65)).toBe('01:05')
    expect(formatDuration(3600)).toBe('01:00:00')
    expect(formatDuration(3665)).toBe('01:01:05')
    expect(formatDuration(null)).toBe('--:--')
    expect(formatDuration(undefined)).toBe('--:--')
  })

  it('formats timestamp matching formatDuration', () => {
    expect(formatTimestamp(125)).toBe('02:05')
  })

  it('formats percentage correctly for fractions and whole numbers', () => {
    expect(formatPercentage(0.852)).toBe('85.2%')
    expect(formatPercentage(85.2, false)).toBe('85.2%')
    expect(formatPercentage(null)).toBe('--%')
  })

  it('formats cosine similarity score', () => {
    expect(formatSimilarity(0.884)).toBe('88%')
    expect(formatSimilarity(0.5)).toBe('50%')
  })

  it('formats file bytes to human readable sizes', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(1024)).toBe('1.0 KB')
    expect(formatBytes(1048576 * 4.5)).toBe('4.5 MB')
  })

  it('handles cn class merging', () => {
    expect(cn('base', undefined, 'text-white')).toBe('base text-white')
  })

  it('formats ISO datetime strings gracefully', () => {
    expect(formatDateTime(null)).toBe('--')
    const formatted = formatDateTime('2026-09-24T17:44:49Z')
    expect(formatted).not.toBe('--')
  })
})
