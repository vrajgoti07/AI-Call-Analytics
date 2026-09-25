/**
 * AI Call Analytics — Theme Discovery Query Hooks.
 */

import { useQuery } from '@tanstack/react-query'
import { getTheme, listThemes } from '../api/themes'
import type { ThemeItemResponse, ThemeListResponse } from '../api/types'

export function useThemes(runId?: string) {
  return useQuery<ThemeListResponse>({
    queryKey: ['themes', runId],
    queryFn: () => listThemes(runId),
    staleTime: 60_000,
  })
}

export function useTheme(themeId: string | undefined) {
  return useQuery<ThemeItemResponse>({
    queryKey: ['theme', themeId],
    queryFn: () => {
      if (!themeId) throw new Error('Theme ID required')
      return getTheme(themeId)
    },
    enabled: Boolean(themeId),
    staleTime: 60_000,
  })
}
