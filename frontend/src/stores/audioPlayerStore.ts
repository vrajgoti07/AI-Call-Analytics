/**
 * AI Call Analytics — Audio Player Synchronization Store (Zustand).
 * Synchronizes browser audio playback timestamp with transcript turns and waveform scrubber.
 */

import { create } from 'zustand'

interface AudioPlayerState {
  activeCallId: string | null
  audioUrl: string | null
  currentTime: number
  duration: number
  isPlaying: boolean
  playbackRate: number
  activeTurnIndex: number | null
  seekTargetTime: number | null

  loadAudio: (callId: string, url: string, duration?: number | null) => void
  setCurrentTime: (time: number) => void
  setDuration: (duration: number) => void
  setIsPlaying: (playing: boolean) => void
  setPlaybackRate: (rate: number) => void
  seekTo: (time: number) => void
  clearSeekTarget: () => void
  setActiveTurnIndex: (index: number | null) => void
  reset: () => void
}

export const useAudioPlayerStore = create<AudioPlayerState>((set) => ({
  activeCallId: null,
  audioUrl: null,
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  playbackRate: 1.0,
  activeTurnIndex: null,
  seekTargetTime: null,

  loadAudio: (callId, url, duration) =>
    set({
      activeCallId: callId,
      audioUrl: url,
      currentTime: 0,
      duration: duration ?? 0,
      isPlaying: false,
      activeTurnIndex: null,
      seekTargetTime: null,
    }),

  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setPlaybackRate: (rate) => set({ playbackRate: rate }),
  seekTo: (time) => set({ seekTargetTime: time, currentTime: time }),
  clearSeekTarget: () => set({ seekTargetTime: null }),
  setActiveTurnIndex: (index) => set({ activeTurnIndex: index }),
  reset: () =>
    set({
      activeCallId: null,
      audioUrl: null,
      currentTime: 0,
      duration: 0,
      isPlaying: false,
      activeTurnIndex: null,
      seekTargetTime: null,
    }),
}))
