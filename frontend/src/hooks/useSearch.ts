/**
 * AI Call Analytics — Semantic Vector Search Mutation Hook.
 */

import { useMutation } from '@tanstack/react-query'
import { semanticSearch } from '../api/search'
import type { SemanticSearchRequest, SemanticSearchResponse } from '../api/types'

export function useSemanticSearch() {
  return useMutation<SemanticSearchResponse, Error, SemanticSearchRequest>({
    mutationFn: (payload: SemanticSearchRequest) => semanticSearch(payload),
  })
}
