import { useEffect, useRef, useState } from 'react'
import { Search, User } from 'lucide-react'
import { SentimentBadge } from '../ui/SentimentBadge'
import { Badge } from '../ui/Badge'
import { EmptyState } from '../ui/EmptyState'
import { formatDuration } from '../../lib/utils'
import { useAudioPlayerStore } from '../../stores/audioPlayerStore'
import type { TranscriptTurnResponse } from '../../api/types'

export interface TranscriptViewerProps {
  turns: TranscriptTurnResponse[]
  isLoading?: boolean
  highlightTimestamp?: number | null
}

export function TranscriptViewer({
  turns,
  isLoading = false,
  highlightTimestamp,
}: TranscriptViewerProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [speakerFilter, setSpeakerFilter] = useState<string>('all')
  const { currentTime, seekTo } = useAudioPlayerStore()
  const activeTurnRef = useRef<HTMLDivElement | null>(null)

  // Find unique speakers
  const speakers = Array.from(new Set(turns.map((t) => t.speaker_id))).sort()

  // Find active turn based on current audio playback time or highlightTimestamp
  const activeTurn = turns.find((t) => {
    if (highlightTimestamp !== null && highlightTimestamp !== undefined) {
      return highlightTimestamp >= t.start_time && highlightTimestamp <= t.end_time
    }
    return currentTime >= t.start_time && currentTime <= t.end_time
  })

  // Auto-scroll active turn into view
  useEffect(() => {
    if (activeTurnRef.current) {
      activeTurnRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [activeTurn?.id])

  // Filter turns
  const filteredTurns = turns.filter((turn) => {
    const matchesSpeaker = speakerFilter === 'all' || turn.speaker_id === speakerFilter
    const matchesQuery =
      !searchQuery ||
      turn.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      turn.intent?.intent.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSpeaker && matchesQuery
  })

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="animate-pulse space-y-2 p-4 rounded-xl bg-white border border-[#E5E5E2]">
            <div className="h-4 bg-[#F2F2F0] rounded w-1/4" />
            <div className="h-10 bg-[#F2F2F0] rounded w-full" />
          </div>
        ))}
      </div>
    )
  }

  if (turns.length === 0) {
    return (
      <EmptyState
        title="No transcript turns available"
        description="The audio transcription is still processing or has not generated turns yet."
      />
    )
  }

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* Transcript Filter & Search Bar */}
      <div className="flex flex-wrap items-center gap-2.5 px-1 py-1">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-neutral-400" />
          <input
            type="text"
            placeholder="Search within transcript..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-[#E5E5E2] bg-white text-xs text-[#17181C] placeholder-[#8A8D95] focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6] transition-colors"
          />
        </div>

        {/* Speaker Filter */}
        <select
          value={speakerFilter}
          onChange={(e) => setSpeakerFilter(e.target.value)}
          aria-label="Filter by speaker"
          className="rounded-lg border border-[#E5E5E2] bg-white px-3 py-1.5 text-xs text-[#17181C] focus:outline-none focus:border-[#6D5AE6] focus:ring-1 focus:ring-[#6D5AE6] cursor-pointer"
        >
          <option value="all">All Speakers ({turns.length} turns)</option>
          {speakers.map((spk) => (
            <option key={spk} value={spk}>
              {spk}
            </option>
          ))}
        </select>
      </div>

      {/* Turns Feed */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
        {filteredTurns.map((turn) => {
          const isActive = activeTurn?.id === turn.id
          const isSpeaker0 = turn.speaker_id.includes('00') || turn.speaker_id.toLowerCase().includes('0')

          return (
            <div
              key={turn.id}
              ref={isActive ? activeTurnRef : null}
              onClick={() => seekTo(turn.start_time)}
              className={`group p-4 rounded-xl border transition-all cursor-pointer ${
                isActive
                  ? 'border-[#6D5AE6] bg-[#F2F0FD]/60 shadow-xs ring-1 ring-[#6D5AE6]/30'
                  : 'border-[#E5E5E2] bg-white hover:border-[#D1D1CD] hover:bg-[#FAFAF9]'
              }`}
            >
              {/* Turn Header */}
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${
                      isSpeaker0
                        ? 'bg-[#F2F0FD] text-[#5844D6] border border-[#DDD6FE]'
                        : 'bg-neutral-100 text-neutral-700 border border-neutral-200'
                    }`}
                  >
                    <User className="h-3 w-3" />
                  </div>
                  <span className="font-medium text-xs text-[#17181C]">
                    {turn.speaker_id}
                  </span>
                  <span className="font-mono text-[11px] text-[#8A8D95] tabular-nums">
                    {formatDuration(turn.start_time)} - {formatDuration(turn.end_time)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {turn.sentiment && (
                    <SentimentBadge
                      sentiment={turn.sentiment.label}
                      score={turn.sentiment.score}
                    />
                  )}
                  {turn.intent && (
                    <Badge variant="primary">
                      {turn.intent.intent} ({Math.round(turn.intent.confidence * 100)}%)
                    </Badge>
                  )}
                </div>
              </div>

              {/* Dialogue Text */}
              <p className="text-sm text-[#17181C] leading-relaxed font-normal">
                {turn.text}
              </p>

              {/* Entity Badges (Masked PII) */}
              {turn.entities && turn.entities.length > 0 && (
                <div className="mt-2.5 flex flex-wrap items-center gap-1.5 pt-2 border-t border-[#E5E5E2]/80">
                  <span className="text-[10px] text-[#8A8D95] uppercase font-mono tracking-wider">
                    Entities:
                  </span>
                  {turn.entities.map((ent, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#FAFAF9] text-[#5844D6] border border-[#E5E5E2]"
                      title={`Type: ${ent.entity_type}`}
                    >
                      [{ent.entity_type}] {ent.text}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
