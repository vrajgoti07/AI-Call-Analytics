/**
 * AI Call Analytics — Evaluation Query Hook.
 */

import { useQuery } from '@tanstack/react-query'
import { getEvaluationResults } from '../api/evaluation'
import type { EvaluationResponse } from '../api/types'

export function useEvaluation() {
  return useQuery<EvaluationResponse>({
    queryKey: ['evaluation'],
    queryFn: getEvaluationResults,
    staleTime: 5 * 60_000, // 5 min cache
  })
}
