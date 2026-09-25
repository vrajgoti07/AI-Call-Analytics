/**
 * AI Call Analytics — Semantic Vector Search API Service.
 */

import { apiClient } from './client'
import type { SemanticSearchRequest, SemanticSearchResponse } from './types'

export async function semanticSearch(
  payload: SemanticSearchRequest,
): Promise<SemanticSearchResponse> {
  return apiClient<SemanticSearchResponse>('/api/v1/search/semantic', {
    method: 'POST',
    body: JSON.stringify({
      query: payload.query,
      top_k: payload.top_k ?? 10,
      similarity_threshold: payload.similarity_threshold ?? 0.0,
      call_id: payload.call_id || undefined,
    }),
  })
}
