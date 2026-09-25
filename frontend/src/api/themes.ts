/**
 * AI Call Analytics — Theme Discovery API Service.
 */

import { apiClient } from './client'
import type { ThemeItemResponse, ThemeListResponse } from './types'

export async function listThemes(runId?: string): Promise<ThemeListResponse> {
  return apiClient<ThemeListResponse>('/api/v1/themes', {
    params: { run_id: runId },
  })
}

export async function getTheme(themeId: string): Promise<ThemeItemResponse> {
  return apiClient<ThemeItemResponse>(`/api/v1/themes/${themeId}`)
}
