import React, { useState } from 'react'
import {
  ArrowRight,
  Search,
  SlidersHorizontal,
  Sparkles,
  User,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { useSemanticSearch } from '../hooks/useSearch'
import { formatDuration, formatSimilarity } from '../lib/utils'

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') || ''

  const [query, setQuery] = useState(initialQuery)
  const [threshold, setThreshold] = useState(0.4)
  const [topK, setTopK] = useState(10)
  const [hasSearched, setHasSearched] = useState(false)

  const searchMutation = useSemanticSearch()

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!query.trim()) return

    setSearchParams({ q: query.trim() })
    setHasSearched(true)
    searchMutation.mutate({
      query: query.trim(),
      similarity_threshold: threshold,
      top_k: topK,
    })
  }

  const results = searchMutation.data?.results ?? []

  const exampleQueries = [
    'customer complaining about card being declined',
    'inquiry about account balance and recent transactions',
    'overdraft fee charged unexpectedly',
    'need help transferring funds to another account',
  ]

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="pb-4 border-b border-[#E5E5E2]">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[#17181C] flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[#6D5AE6]" />
          Semantic Vector Search
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-[#60636B]">
          Query call transcripts by conceptual meaning using text embeddings and pgvector cosine similarity
        </p>
      </div>

      {/* Search Input Box */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="relative flex items-center">
          <Search className="absolute left-4 h-5 w-5 text-[#60636B]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a natural language query (e.g. 'card declined at checkout')..."
            className="w-full pl-12 pr-28 py-3.5 rounded-xl border border-[#E5E5E2] bg-white text-sm text-[#17181C] placeholder-[#60636B] shadow-xs focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6]"
          />
          <div className="absolute right-3">
            <Button
              type="submit"
              size="sm"
              isLoading={searchMutation.isPending}
              disabled={!query.trim()}
            >
              Search
            </Button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="p-4 rounded-xl border border-[#E5E5E2] bg-white shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Similarity Threshold Slider */}
            <div className="flex items-center gap-2.5">
              <SlidersHorizontal className="h-4 w-4 text-[#60636B]" />
              <span className="text-[#17181C] font-medium">Min Similarity:</span>
              <input
                type="range"
                min={0.0}
                max={0.9}
                step={0.05}
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-28 accent-[#6D5AE6] cursor-pointer"
              />
              <span className="font-mono text-[#6D5AE6] font-bold w-10 tabular-nums">
                {(threshold * 100).toFixed(0)}%
              </span>
            </div>

            {/* Top-K Selector */}
            <div className="flex items-center gap-2">
              <span className="text-[#60636B]">Max Results:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value, 10))}
                className="rounded border border-[#E5E5E2] bg-white px-2.5 py-1 text-[#17181C] focus:outline-none focus:border-[#6D5AE6] cursor-pointer"
              >
                <option value={5}>Top 5</option>
                <option value={10}>Top 10</option>
                <option value={20}>Top 20</option>
                <option value={50}>Top 50</option>
              </select>
            </div>
          </div>

          {searchMutation.data && (
            <span className="font-mono text-[#60636B] text-xs">
              Found {searchMutation.data.total_results} matching chunks
            </span>
          )}
        </div>
      </form>

      {/* Error Alert */}
      {searchMutation.isError && (
        <ErrorAlert
          title="Semantic Search Failed"
          message={searchMutation.error.message}
          onRetry={() => handleSearch()}
        />
      )}

      {/* Example Queries (if no search conducted yet) */}
      {!hasSearched && (
        <div className="p-6 rounded-xl border border-[#E5E5E2] bg-[#FAFAF9] space-y-3">
          <span className="text-xs font-semibold text-[#17181C]">
            Suggested Example Queries:
          </span>
          <div className="flex flex-wrap gap-2">
            {exampleQueries.map((ex, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setQuery(ex)
                  setHasSearched(true)
                  searchMutation.mutate({
                    query: ex,
                    similarity_threshold: threshold,
                    top_k: topK,
                  })
                }}
                className="px-3 py-1.5 rounded-lg border border-[#E5E5E2] bg-white hover:border-[#6D5AE6] text-xs text-[#60636B] hover:text-[#5844D6] shadow-xs transition-colors text-left cursor-pointer"
              >
                "{ex}"
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results Feed */}
      {hasSearched && !searchMutation.isPending && results.length > 0 && (
        <div className="space-y-3">
          {results.map((result) => {
            const pct = Math.round(result.similarity * 100)
            return (
              <div
                key={result.chunk_id}
                className="p-4 rounded-xl border border-[#E5E5E2] bg-white hover:border-[#D1D1CD] shadow-xs transition-colors space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-mono font-semibold text-[#6D5AE6]">
                      Call #{result.call_id.slice(0, 8)}
                    </span>
                    <span className="text-[#E5E5E2]">•</span>
                    <div className="flex items-center gap-1 font-mono text-[#60636B]">
                      <User className="h-3 w-3" />
                      <span>{result.speaker_ids.join(', ') || 'SPEAKER'}</span>
                    </div>
                    <span className="text-[#E5E5E2]">•</span>
                    <span className="font-mono text-[#60636B] tabular-nums">
                      {formatDuration(result.start_time)} - {formatDuration(result.end_time)}
                    </span>
                  </div>

                  <Badge variant={pct >= 70 ? 'primary' : 'default'} className="font-mono font-bold tabular-nums">
                    {formatSimilarity(result.similarity)} Match
                  </Badge>
                </div>

                <p className="text-sm text-[#17181C] leading-relaxed font-normal bg-[#FAFAF9] p-3 rounded-lg border border-[#E5E5E2]">
                  "{result.text}"
                </p>

                <div className="flex justify-end pt-1">
                  <Link
                    to={`/calls/${result.call_id}?t=${result.start_time}`}
                    className="inline-flex items-center gap-1.5 text-xs text-[#6D5AE6] hover:text-[#5844D6] font-semibold transition-colors"
                  >
                    Open Call at {formatDuration(result.start_time)} <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* No Results Found */}
      {hasSearched && !searchMutation.isPending && results.length === 0 && (
        <EmptyState
          icon={<Search className="h-10 w-10 text-[#60636B]" />}
          title="No semantic matches found"
          description={`No transcript segments exceeded the ${(threshold * 100).toFixed(0)}% similarity cutoff. Try lowering the similarity threshold or phrasing your query differently.`}
          action={
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setThreshold(0.2)
                searchMutation.mutate({
                  query,
                  similarity_threshold: 0.2,
                  top_k: topK,
                })
              }}
            >
              Lower threshold to 20%
            </Button>
          }
        />
      )}
    </div>
  )
}
