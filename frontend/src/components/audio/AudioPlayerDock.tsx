import { useEffect, useRef } from 'react'
import { Pause, Play, RotateCcw, RotateCw } from 'lucide-react'
import { useAudioPlayerStore } from '../../stores/audioPlayerStore'
import { formatDuration } from '../../lib/utils'

export interface AudioPlayerDockProps {
  callId: string
  audioUrl: string
  audioFilename?: string
  totalDuration?: number | null
}

export function AudioPlayerDock({
  callId,
  audioUrl,
  audioFilename = 'audio.wav',
  totalDuration = 0,
}: AudioPlayerDockProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const {
    currentTime,
    duration,
    isPlaying,
    playbackRate,
    seekTargetTime,
    loadAudio,
    setCurrentTime,
    setDuration,
    setIsPlaying,
    setPlaybackRate,
    clearSeekTarget,
  } = useAudioPlayerStore()

  // Initialize store on mount or callId change
  useEffect(() => {
    loadAudio(callId, audioUrl, totalDuration)
  }, [callId, audioUrl, totalDuration, loadAudio])

  // Handle external seek requests (from clicking transcript turns)
  useEffect(() => {
    if (seekTargetTime !== null && audioRef.current) {
      audioRef.current.currentTime = seekTargetTime
      clearSeekTarget()
      if (!isPlaying) {
        audioRef.current.play().catch(() => {})
        setIsPlaying(true)
      }
    }
  }, [seekTargetTime, clearSeekTarget, isPlaying, setIsPlaying])

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play().catch(() => {})
      setIsPlaying(true)
    }
  }

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime)
    }
  }

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      const dur = audioRef.current.duration || totalDuration || 0
      setDuration(dur)
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    if (audioRef.current) {
      audioRef.current.currentTime = val
      setCurrentTime(val)
    }
  }

  const handleRateChange = (rate: number) => {
    setPlaybackRate(rate)
    if (audioRef.current) {
      audioRef.current.playbackRate = rate
    }
  }

  const skipSeconds = (secs: number) => {
    if (audioRef.current) {
      const newTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + secs))
      audioRef.current.currentTime = newTime
      setCurrentTime(newTime)
    }
  }

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="rounded-xl border border-[#E5E5E2] bg-white p-3 sm:p-4 shadow-xs">
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setIsPlaying(false)}
      />

      <div className="flex flex-col gap-2.5">
        {/* Top Scrubber & Time */}
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-[#5844D6] font-semibold w-12 text-right tabular-nums">
            {formatDuration(currentTime)}
          </span>

          <div className="relative flex-1 flex items-center">
            <input
              type="range"
              min={0}
              max={duration || 1}
              step={0.1}
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-1.5 bg-[#E5E5E2] rounded-lg appearance-none cursor-pointer accent-[#6D5AE6] hover:accent-[#5844D6]"
              style={{
                background: `linear-gradient(to right, #6D5AE6 ${progressPercent}%, #E5E5E2 ${progressPercent}%)`,
              }}
            />
          </div>

          <span className="font-mono text-xs text-[#8A8D95] w-12 tabular-nums">
            {formatDuration(duration || totalDuration)}
          </span>
        </div>

        {/* Playback Controls Row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-[#60636B]">
            <span className="font-mono text-[#17181C] font-medium truncate max-w-[200px]">
              {audioFilename}
            </span>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => skipSeconds(-5)}
              className="p-1.5 text-[#60636B] hover:text-[#17181C] rounded-lg hover:bg-[#F2F2F0] cursor-pointer transition-colors"
              title="Skip backward 5s"
              aria-label="Skip backward 5s"
            >
              <RotateCcw className="h-4 w-4" />
            </button>

            <button
              type="button"
              onClick={togglePlay}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-[#6D5AE6] hover:bg-[#5844D6] active:bg-[#4834C4] text-white shadow-xs cursor-pointer transition-transform active:scale-95"
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
            </button>

            <button
              type="button"
              onClick={() => skipSeconds(5)}
              className="p-1.5 text-[#60636B] hover:text-[#17181C] rounded-lg hover:bg-[#F2F2F0] cursor-pointer transition-colors"
              title="Skip forward 5s"
              aria-label="Skip forward 5s"
            >
              <RotateCw className="h-4 w-4" />
            </button>
          </div>

          {/* Speed Selector */}
          <div className="flex items-center gap-1.5">
            {[0.75, 1.0, 1.25, 1.5].map((rate) => (
              <button
                key={rate}
                type="button"
                onClick={() => handleRateChange(rate)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium tabular-nums cursor-pointer transition-colors ${
                  playbackRate === rate
                    ? 'bg-[#F2F0FD] text-[#5844D6] border border-[#DDD6FE]'
                    : 'text-[#60636B] hover:text-[#17181C] hover:bg-[#F2F2F0]'
                }`}
              >
                {rate}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
