import { useEffect, useState } from 'react'
import { useStore, type World } from './store'
import './App.css'

function App() {
  const view = useStore((s) => s.view)
  const checkHealth = useStore((s) => s.checkHealth)
  const refreshWorlds = useStore((s) => s.refreshWorlds)

  useEffect(() => {
    checkHealth()
    refreshWorlds()
  }, [checkHealth, refreshWorlds])

  return (
    <div className="app">
      {view === 'home' ? <HomeView /> : <SimView />}
    </div>
  )
}

// ============ TOP BAR ============
function TopBar() {
  const view = useStore((s) => s.view)
  const goHome = useStore((s) => s.goHome)
  const health = useStore((s) => s.health)
  const selectedWorld = useStore((s) => s.selectedWorld)

  return (
    <header className="topbar">
      {view === 'home' ? (
        <>
          <div className="brand" onClick={goHome}>
            <span className="dot" />
            <span className="name">故事梦工厂</span>
            <span className="en">Story Dream Factory</span>
          </div>
          <span className="spacer" />
          <span className="health">
            <span className="live-dot" />
            后端 {health}
          </span>
        </>
      ) : (
        <>
          <button className="back-btn" onClick={goHome} title="返回世界库">
            ←
          </button>
          <div className="brand" onClick={goHome}>
            <span className="dot" />
            <span className="name">{selectedWorld?.name ?? '世界'}</span>
          </div>
          <span className="spacer" />
        </>
      )}
    </header>
  )
}

// ============ HOME ============
function HomeView() {
  const worlds = useStore((s) => s.worlds)
  const loadingWorlds = useStore((s) => s.loadingWorlds)
  const openWorld = useStore((s) => s.openWorld)
  const [showCreate, setShowCreate] = useState(false)

  return (
    <>
      <TopBar />
      <div className="home-wrap">
        <div className="home-kicker">Story Dream Factory</div>
        <h1 className="home-title">
          让故事 <em>自行生长</em>
        </h1>
        <p className="home-sub">
          构建一个世界，启动模拟，看角色、冲突与命运在叙述中自行涌现。
        </p>
        <div style={{ marginTop: 26 }}>
          <button
            className="btn primary"
            onClick={() => setShowCreate((v) => !v)}
          >
            {showCreate ? '收起新建' : '＋ 新建世界'}
          </button>
        </div>
      </div>

      <div className="home-list">
        {showCreate && <CreateForm onDone={() => setShowCreate(false)} />}

        <div className="home-section">
          你的世界 <span className="count">· {worlds.length}</span>
        </div>

        {loadingWorlds ? (
          <div className="placeholder">
            <div className="loading">加载世界列表中…</div>
          </div>
        ) : worlds.length === 0 ? (
          <div className="empty-card">
            还没有世界。点击右上「新建世界」开始你的第一个故事。
          </div>
        ) : (
          <div className="world-grid">
            {worlds.map((w) => (
              <WorldCard key={w.id} world={w} onClick={() => openWorld(w)} />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

function glyphOf(name: string) {
  const t = (name || '?').trim()
  return t.charAt(0) || '?'
}

function WorldCard({ world, onClick }: { world: World; onClick: () => void }) {
  const vision = world.vision || world.setting || '尚未设定愿景的世界。'
  const tick = world.clock_tick ?? 0
  const rulesCount = world.rules?.length ?? 0
  return (
    <div className="world-card" onClick={onClick}>
      <div className="wc-cover">
        <span className="wc-glyph">{glyphOf(world.name)}</span>
      </div>
      <div className="wc-body">
        <h3>{world.name || '未命名'}</h3>
        <div className="vis">{vision}</div>
        <div className="wc-meta">
          <span>{rulesCount} 条规则</span>
          <span>Tick {tick}</span>
        </div>
      </div>
    </div>
  )
}

function CreateForm({ onDone }: { onDone: () => void }) {
  const createWorld = useStore((s) => s.createWorld)
  const creating = useStore((s) => s.creating)
  const [name, setName] = useState('')
  const [vision, setVision] = useState('')
  const [setting, setSetting] = useState('')
  const [rulesText, setRulesText] = useState('')

  const submit = async () => {
    if (!name.trim()) return
    const rules = rulesText
      .split('\n')
      .map((r) => r.trim())
      .filter(Boolean)
    await createWorld({ name: name.trim(), vision, setting, rules })
    onDone()
  }

  return (
    <div className="create-card">
      <div className="bm-label">新建世界</div>
      <h2>
        讲一个怎样的 <em>故事</em>？
      </h2>
      <div className="field-label">名称</div>
      <input
        className="field-input"
        placeholder="例如：艾尔德兰"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <div className="field-label">愿景（一句话基调）</div>
      <input
        className="field-input"
        placeholder="例如：魔法衰落的王国"
        value={vision}
        onChange={(e) => setVision(e.target.value)}
      />
      <div className="field-label">世界设定</div>
      <textarea
        className="field-textarea"
        placeholder="时代、核心矛盾、地理…"
        value={setting}
        onChange={(e) => setSetting(e.target.value)}
      />
      <div className="field-label">世界规则（每行一条）</div>
      <textarea
        className="field-textarea"
        placeholder={'魔法稀有，施法付代价\n誓言有约束力'}
        value={rulesText}
        onChange={(e) => setRulesText(e.target.value)}
      />
      <button
        className="btn primary big"
        disabled={creating || !name.trim()}
        onClick={submit}
      >
        {creating ? '创建中…' : '创建并进入 →'}
      </button>
    </div>
  )
}

// ============ SIM ============
function SimView() {
  const world = useStore((s) => s.selectedWorld)
  const simStarted = useStore((s) => s.simStarted)
  const startingSim = useStore((s) => s.startingSim)
  const stepping = useStore((s) => s.stepping)
  const tick = useStore((s) => s.tick)
  const events = useStore((s) => s.events)
  const simError = useStore((s) => s.simError)
  const startSim = useStore((s) => s.startSim)
  const stepSim = useStore((s) => s.stepSim)

  if (!world) return null

  return (
    <>
      <TopBar />
      <div className="sim-wrap">
        <div className="sim-head">
          <div className="sh-label">剧目舞台</div>
          <h2>
            {world.name} <em>{world.vision ? '' : ''}</em>
          </h2>
          {world.vision && (
            <div style={{ fontSize: 14, color: 'var(--ink-2)', marginTop: 6 }}>
              {world.vision}
            </div>
          )}
          <div className="sh-meta">
            {[world.vision, world.setting].filter(Boolean).join(' · ') ||
              '尚无设定'}
          </div>
        </div>

        <div className="sim-controls">
          {!simStarted ? (
            <button
              className="btn primary"
              onClick={startSim}
              disabled={startingSim}
            >
              {startingSim ? '启动中…' : '▶ 启动模拟'}
            </button>
          ) : (
            <>
              <span className="tick-pill">
                Tick <b>{tick}</b>
              </span>
              <span className="live-pill">
                <span className="live-dot" />
                运行中
              </span>
              <span className="spacer" />
              <button
                className="btn primary"
                onClick={stepSim}
                disabled={stepping}
              >
                {stepping ? '推演中…' : '⏵ 推进一拍 (Step)'}
              </button>
            </>
          )}
        </div>

        {simError && <div className="sim-error">⚠ {simError}</div>}

        <Narrative events={events} simStarted={simStarted} stepping={stepping} />
      </div>
    </>
  )
}

function Narrative({
  events,
  simStarted,
  stepping,
}: {
  events: ReturnType<typeof useStore.getState>['events']
  simStarted: boolean
  stepping: boolean
}) {
  if (!simStarted) {
    return (
      <div className="placeholder">
        <div className="glyph">✦</div>
        点击「启动模拟」唤醒这个世界。
        <br />
        角色、规则与设定将开始相互作用，故事会自行生长。
      </div>
    )
  }
  if (events.length === 0 && !stepping) {
    return (
      <div className="placeholder">
        <div className="glyph">✦</div>
        模拟已就绪。点击「推进一拍 (Step)」让时间流动，看叙述涌现。
      </div>
    )
  }
  return (
    <div className="narrative">
      {events.map((e, i) => (
        <div className="beat" key={i}>
          <div className="beat-label">
            <span className="beat-dot" />
            <span className="beat-meta">
              <b>Tick {e.tick}</b> · {e.type || '事件'}
            </span>
          </div>
          <p className="prose">{e.narration || '（无叙述）'}</p>
          {e.participants && e.participants.length > 0 && (
            <div className="event-participants">
              {e.participants.map((p, j) => (
                <span key={j}>{p}</span>
              ))}
            </div>
          )}
        </div>
      ))}
      {stepping && (
        <div className="beat">
          <div className="beat-label">
            <span className="beat-dot" />
            <span className="beat-meta">推演中…</span>
          </div>
          <p className="prose loading">世界正在演化这一拍。</p>
        </div>
      )}
    </div>
  )
}

export default App
