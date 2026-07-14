import { create } from 'zustand'

// ===== Types matching the backend API =====
export interface World {
  id: string
  name: string
  vision: string
  setting: string
  rules: string[]
  visual_style: Record<string, unknown>
  clock_tick: number
  clock_date: string
  state_flags: Record<string, unknown>
  initial_state: Record<string, unknown>
  llm_config: Record<string, unknown>
  created_at: string
}

export interface SimEvent {
  tick: number
  type: string
  narration: string
  participants: string[]
}

interface StartSimResponse {
  sim_id?: string
  world?: string
  characters?: string[]
  tick?: number
  error?: string
}

interface StepSimResponse {
  tick?: number
  events?: SimEvent[]
  error?: string
}

type View = 'home' | 'sim'

interface State {
  view: View
  worlds: World[]
  selectedWorld: World | null
  health: string
  loadingWorlds: boolean
  // simulation
  simStarted: boolean
  startingSim: boolean
  stepping: boolean
  tick: number
  events: SimEvent[]
  simError: string | null
  // create world
  creating: boolean
  // actions
  goHome: () => void
  openWorld: (w: World) => void
  refreshWorlds: () => Promise<void>
  checkHealth: () => Promise<void>
  createWorld: (payload: Partial<World>) => Promise<void>
  startSim: () => Promise<void>
  stepSim: () => Promise<void>
}

export const useStore = create<State>((set, get) => ({
  view: 'home',
  worlds: [],
  selectedWorld: null,
  health: '...',
  loadingWorlds: false,
  simStarted: false,
  startingSim: false,
  stepping: false,
  tick: 0,
  events: [],
  simError: null,
  creating: false,

  goHome: () =>
    set({
      view: 'home',
      selectedWorld: null,
      simStarted: false,
      events: [],
      tick: 0,
      simError: null,
    }),

  openWorld: (w) =>
    set({
      view: 'sim',
      selectedWorld: w,
      simStarted: false,
      events: [],
      tick: w.clock_tick ?? 0,
      simError: null,
    }),

  checkHealth: async () => {
    try {
      const r = await fetch('/health')
      const j = await r.json()
      set({ health: j?.status === 'ok' ? '在线' : JSON.stringify(j) })
    } catch {
      set({ health: '离线' })
    }
  },

  refreshWorlds: async () => {
    set({ loadingWorlds: true })
    try {
      const r = await fetch('/worlds')
      const j = (await r.json()) as World[]
      set({ worlds: Array.isArray(j) ? j : [] })
    } catch {
      set({ worlds: [] })
    } finally {
      set({ loadingWorlds: false })
    }
  },

  createWorld: async (payload) => {
    set({ creating: true })
    try {
      const r = await fetch('/worlds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const w = (await r.json()) as World
      await get().refreshWorlds()
      set({ selectedWorld: w, view: 'sim', simStarted: false, events: [], tick: 0 })
    } finally {
      set({ creating: false })
    }
  },

  startSim: async () => {
    const w = get().selectedWorld
    if (!w) return
    set({ startingSim: true, simError: null })
    try {
      const r = await fetch(`/worlds/${w.id}/simulate/start`, { method: 'POST' })
      const j = (await r.json()) as StartSimResponse
      if (j.error) {
        set({ simError: j.error })
        return
      }
      set({
        simStarted: true,
        tick: j.tick ?? w.clock_tick ?? 0,
        events: [],
        simError: null,
      })
    } catch (e) {
      set({ simError: e instanceof Error ? e.message : String(e) })
    } finally {
      set({ startingSim: false })
    }
  },

  stepSim: async () => {
    const w = get().selectedWorld
    if (!w) return
    set({ stepping: true, simError: null })
    try {
      const r = await fetch(`/worlds/${w.id}/simulate/step`, { method: 'POST' })
      const j = (await r.json()) as StepSimResponse
      if (j.error) {
        set({ simError: j.error })
        return
      }
      const newEvents = j.events ?? []
      set((s) => ({
        tick: j.tick ?? s.tick,
        events: [...s.events, ...newEvents],
      }))
    } catch (e) {
      set({ simError: e instanceof Error ? e.message : String(e) })
    } finally {
      set({ stepping: false })
    }
  },
}))
