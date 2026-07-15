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
  characters?: string[]
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

export type DirectorDirectiveType =
  | 'inject_event'
  | 'set_goal'
  | 'modify_world'
  | 'force_action'

export interface DirectorDirective {
  type: DirectorDirectiveType
  payload: Record<string, unknown>
  target: string
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
  characters: string[]
  simError: string | null
  // websocket auto-advance
  ws: WebSocket | null
  wsStatus: 'disconnected' | 'connecting' | 'connected' | 'error'
  autoPlay: boolean
  playSpeed: number
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
  connectWS: (worldId: string) => void
  disconnectWS: () => void
  toggleAutoPlay: () => void
  setPlaySpeed: (ms: number) => void
  injectDirective: (worldId: string, directive: DirectorDirective) => Promise<boolean>
}

// ---- WebSocket auto-advance scheduler ----
// 模块级定时器：autoPlay 时，每次收到事件后等待 playSpeed 再发下一拍。
let stepTimer: ReturnType<typeof setTimeout> | null = null

function clearStepTimer() {
  if (stepTimer !== null) {
    clearTimeout(stepTimer)
    stepTimer = null
  }
}

function scheduleStep(delay: number) {
  clearStepTimer()
  stepTimer = setTimeout(() => {
    stepTimer = null
    const s = useStore.getState()
    if (s.autoPlay && s.ws && s.ws.readyState === WebSocket.OPEN) {
      useStore.setState({ stepping: true })
      s.ws.send(JSON.stringify({ action: 'step' }))
    }
  }, delay)
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
  characters: [],
  simError: null,
  ws: null,
  wsStatus: 'disconnected',
  autoPlay: false,
  playSpeed: 3000,
  creating: false,

  goHome: () => {
    get().disconnectWS()
    set({
      view: 'home',
      selectedWorld: null,
      simStarted: false,
      events: [],
      characters: [],
      tick: 0,
      simError: null,
      autoPlay: false,
    })
  },

  openWorld: (w) => {
    get().disconnectWS()
    set({
      view: 'sim',
      selectedWorld: w,
      simStarted: false,
      events: [],
      characters: w.characters ?? [],
      tick: w.clock_tick ?? 0,
      simError: null,
      autoPlay: false,
    })
  },

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
      set({ selectedWorld: w, view: 'sim', simStarted: false, events: [], tick: 0, characters: w.characters ?? [] })
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
        characters: j.characters ?? [],
        simError: null,
      })
      // 启动成功后自动连接 WebSocket，用于自动推进
      get().connectWS(w.id)
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

  connectWS: (worldId) => {
    // 先清理可能存在的旧连接
    get().disconnectWS()
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${window.location.host}/worlds/${encodeURIComponent(worldId)}/ws`
    set({ wsStatus: 'connecting' })
    let ws: WebSocket
    try {
      ws = new WebSocket(url)
    } catch {
      set({ wsStatus: 'error' })
      return
    }
    ws.onopen = () => {
      if (get().ws === ws) set({ wsStatus: 'connected' })
    }
    ws.onclose = () => {
      clearStepTimer()
      if (get().ws === ws) set({ wsStatus: 'disconnected', autoPlay: false })
    }
    ws.onerror = () => {
      if (get().ws === ws) set({ wsStatus: 'error' })
    }
    ws.onmessage = (ev) => {
      let j: StepSimResponse
      try {
        j = JSON.parse(ev.data) as StepSimResponse
      } catch {
        return
      }
      if (j.error) {
        // 出错时停止自动推进，避免错误循环
        set({ simError: j.error, stepping: false, autoPlay: false })
        clearStepTimer()
        return
      }
      const newEvents = j.events ?? []
      set((s) => ({
        tick: j.tick ?? s.tick,
        events: [...s.events, ...newEvents],
        stepping: false,
      }))
      // 自动模式：收到事件后，等待 playSpeed 再发下一拍
      if (get().autoPlay) scheduleStep(get().playSpeed)
    }
    set({ ws })
  },

  disconnectWS: () => {
    clearStepTimer()
    const ws = get().ws
    if (ws) {
      ws.onclose = null
      ws.onerror = null
      ws.onmessage = null
      try {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'disconnect' }))
        }
        ws.close()
      } catch {
        /* ignore */
      }
    }
    set({ ws: null, wsStatus: 'disconnected', autoPlay: false })
  },

  toggleAutoPlay: () => {
    const willPlay = !get().autoPlay
    set({ autoPlay: willPlay })
    if (willPlay) {
      // 立即发出第一拍，后续由 onmessage 调度
      const { ws } = get()
      if (ws && ws.readyState === WebSocket.OPEN) {
        useStore.setState({ stepping: true })
        ws.send(JSON.stringify({ action: 'step' }))
      }
    } else {
      clearStepTimer()
    }
  },

  setPlaySpeed: (ms) => {
    set({ playSpeed: ms })
    // 若正在等待下一拍，按新速度重新计时
    if (get().autoPlay && stepTimer !== null) scheduleStep(ms)
  },

  injectDirective: async (worldId, directive) => {
    try {
      const r = await fetch(`/worlds/${encodeURIComponent(worldId)}/director/inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(directive),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return true
    } catch (e) {
      set({ simError: e instanceof Error ? e.message : String(e) })
      return false
    }
  },
}))
