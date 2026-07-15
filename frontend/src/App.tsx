import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useStore, type World, type DirectorDirectiveType } from './store'
import { CanvasBackground } from './CanvasBackground'
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
      <CanvasBackground />
      <TopBar />
      <div className="home-wrap">
        <div className="home-kicker">Story Dream Factory</div>
        <h1 className="home-title">
          让故事 <em>自行生长</em>
        </h1>
        <p className="home-sub">
          构建一个世界，启动模拟，看角色、冲突与命运在叙述中自行涌现。
        </p>
        <div style={{ marginTop: 26, display: 'flex', gap: 10 }}>
          <button
            className="btn primary"
            onClick={() => setShowCreate((v) => !v)}
          >
            {showCreate ? '收起新建' : '＋ 新建世界'}
          </button>
          {showCreate && (
            <button
              className="btn"
              onClick={() => setShowCreate(false)}
            >
              ✕ 关闭
            </button>
          )}
        </div>
      </div>

      <div className="home-list">
        {showCreate && (
          <BuilderFlow
            onDone={() => setShowCreate(false)}
            onCancel={() => setShowCreate(false)}
          />
        )}

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

// ============ World Builder (对话式世界构建) ============
type BuilderPhase = 'select' | 'chat'
type ChatMsg = { role: 'user' | 'assistant'; content: string }

const BUILDER_STAGES: { key: string; name: string; desc: string }[] = [
  { key: 'vision', name: '愿景', desc: '类型与基调' },
  { key: 'setting', name: '世界观', desc: '时代与核心矛盾' },
  { key: 'rules', name: '规则', desc: '世界法则' },
  { key: 'locations', name: '地点', desc: '抽象地图' },
  { key: 'characters', name: '角色', desc: '性格·目标' },
  { key: 'inciting', name: '开场', desc: '引爆事件' },
  { key: 'finalize', name: '定稿', desc: '健康检查·开拍' },
]

const BUILDER_TEMPLATES = [
  { idx: 0, name: '中世纪奇幻', en: 'Fantasy', desc: '魔法衰落中的王国', glyph: '奇', grad: 'linear-gradient(135deg,#3a4a6b,#1a2238)' },
  { idx: 1, name: '权谋宫廷', en: 'Court', desc: '王座空悬，群狼环伺', glyph: '权', grad: 'linear-gradient(135deg,#5a2a2a,#2a1010)' },
  { idx: 2, name: '东方仙侠', en: 'Xianxia', desc: '仙门林立的修仙界', glyph: '霄', grad: 'linear-gradient(135deg,#3a5a3a,#1a2818)' },
  { idx: 3, name: '克苏鲁恐怖', en: 'Lovecraft', desc: '海雾笼罩的孤镇', glyph: '雾', grad: 'linear-gradient(135deg,#1a4a4a,#082828)' },
  { idx: 4, name: '末日废土', en: 'Wasteland', desc: '核冬后的荒原', glyph: '废', grad: 'linear-gradient(135deg,#5a4a2a,#2a2010)' },
  { idx: 5, name: '赛博朋克', en: 'Cyberpunk', desc: '2087 企业垄断的未来', glyph: '霓', grad: 'linear-gradient(135deg,#6b3a5a,#381a2a)' },
  { idx: 6, name: '太空歌剧', en: 'Space', desc: '星际帝国的黄昏', glyph: '星', grad: 'linear-gradient(135deg,#1a2a5a,#0a1028)' },
  { idx: 7, name: 'AI觉醒', en: 'AI', desc: '人工智能觉醒的那一天', glyph: '智', grad: 'linear-gradient(135deg,#2a4a5a,#101a28)' },
  { idx: 8, name: '时间旅行', en: 'Time', desc: '时间线断裂的危机', glyph: '时', grad: 'linear-gradient(135deg,#3a2a5a,#1a1038)' },
  { idx: 9, name: '盛唐暗影', en: 'Tang', desc: '天宝末年的长安城', glyph: '唐', grad: 'linear-gradient(135deg,#5a3a1a,#2a1a08)' },
  { idx: 10, name: '民国谍战', en: 'Spy', desc: '1940年代谍影重重', glyph: '谍', grad: 'linear-gradient(135deg,#2a3a2a,#101a10)' },
  { idx: 11, name: '推理悬案', en: 'Mystery', desc: '密室杀人案', glyph: '谜', grad: 'linear-gradient(135deg,#3a2a1a,#1a1408)' },
  { idx: 12, name: '都市情感', en: 'Urban', desc: '霓虹灯下的相遇', glyph: '都', grad: 'linear-gradient(135deg,#5a3a4a,#2a1a2a)' },
  { idx: 13, name: '校园青春', en: 'Campus', desc: '大学最后一年', glyph: '园', grad: 'linear-gradient(135deg,#3a4a2a,#1a2010)' },
  { idx: 14, name: '武侠江湖', en: 'Wuxia', desc: '刀光剑影的江湖', glyph: '侠', grad: 'linear-gradient(135deg,#2a4a3a,#102018)' },
  { idx: 15, name: '盗墓探险', en: 'Tomb', desc: '古墓中的生死', glyph: '墓', grad: 'linear-gradient(135deg,#4a3a1a,#2a2008)' },
]

const BUILDER_HEADINGS: { h: ReactNode; d: string }[] = [
  { h: <>讲一个怎样的 <em>故事</em>？</>, d: '先定下类型、基调与规模——这也决定世界的视觉风格基底。' },
  { h: <>世界 <em>从何而来</em>？</>, d: '时代、世界设定，以及最核心的矛盾。' },
  { h: <>世界 <em>遵循什么</em>？</>, d: '把模糊想法变成清晰、可执行的世界规则——它们会约束物理引擎。' },
  { h: <>发生在 <em>哪里</em>？</>, d: '关键地点，以及它们之间如何连通。角色将在这些地点间移动。' },
  { h: <>谁来 <em>登场</em>？</>, d: '为每个角色立传——性格、目标、关系。记得在角色之间埋下张力。' },
  { h: <>从哪个 <em>瞬间</em> 开始？</>, d: '初始态势，以及一个打破平衡的引爆事件——开拍时作为 Tick 0 注入。' },
  { h: <>准备好 <em>开拍</em> 了吗？</>, d: '一致性健康检查。通过即可开拍，世界将带着你的设定自主演化。' },
]

function arrLen(collected: Record<string, unknown>, key: string): number {
  const v = collected[key]
  return Array.isArray(v) ? v.length : 0
}

function BuilderFlow({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const refreshWorlds = useStore((s) => s.refreshWorlds)
  const openWorld = useStore((s) => s.openWorld)

  const [phase, setPhase] = useState<BuilderPhase>('select')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [stage, setStage] = useState<string>('vision')
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [checklist, setChecklist] = useState<Record<string, { covered: number; total: number }>>({})
  const [collected, setCollected] = useState<Record<string, unknown>>({})
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [starting, setStarting] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [health, setHealth] = useState<{ passed: boolean; errors: string[]; warnings: string[] } | null>(null)

  const chatRef = useRef<HTMLDivElement>(null)

  function resetBuilder() {
    setPhase('select')
    setSessionId(null)
    setStage('vision')
    setMessages([])
    setChecklist({})
    setCollected({})
    setInput('')
    setError(null)
    setHealth(null)
  }

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  const currentStageIdx = Math.max(0, BUILDER_STAGES.findIndex((s) => s.key === stage))
  const stageInfo = BUILDER_STAGES[currentStageIdx]
  const heading = BUILDER_HEADINGS[currentStageIdx]

  async function fetchProgress(sid: string) {
    try {
      const r = await fetch(`/worlds/builder/session/${sid}/progress`)
      const j = await r.json()
      if (j.checklist) setChecklist(j.checklist)
      if (j.collected) setCollected(j.collected)
      if (j.stage) setStage(j.stage)
    } catch {
      /* 进度查询失败不阻塞对话 */
    }
  }

  async function selectTemplate(idx: number) {
    setStarting(true)
    setError(null)
    try {
      const r = await fetch('/worlds/builder/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_index: idx }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const j = await r.json()
      setSessionId(j.session_id)
      setStage(j.stage)
      setMessages([
        { role: 'assistant', content: j.prompt_hint || `开始「${j.stage_title || '愿景'}」阶段。` },
      ])
      await fetchProgress(j.session_id)
      setPhase('chat')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setStarting(false)
    }
  }

  async function sendMessage(text: string) {
    const sid = sessionId
    const content = text.trim()
    if (!sid || !content || sending || finalizing) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content }])
    setSending(true)
    setError(null)
    try {
      const r = await fetch(`/worlds/builder/session/${sid}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const j = await r.json()
      if (j.reply) setMessages((m) => [...m, { role: 'assistant', content: j.reply }])
      if (j.stage) setStage(j.stage)
      await fetchProgress(sid)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSending(false)
    }
  }

  async function goBack() {
    const sid = sessionId
    if (!sid || sending || finalizing || currentStageIdx === 0) return
    setSending(true)
    setError(null)
    try {
      const r = await fetch(`/worlds/builder/session/${sid}/go-back`, { method: 'POST' })
      const j = await r.json()
      if (j.stage) setStage(j.stage)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: j.stage_title ? `回到「${j.stage_title}」阶段，可以重新描述。` : '已返回上一步。',
        },
      ])
      await fetchProgress(sid)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSending(false)
    }
  }

  // 后端仅支持 go-back，所以仅在向前回退阶段时可点击跳转
  async function jumpToStage(targetIdx: number) {
    const sid = sessionId
    if (!sid || sending || finalizing || targetIdx >= currentStageIdx) return
    setSending(true)
    setError(null)
    try {
      let remaining = currentStageIdx - targetIdx
      while (remaining > 0) {
        const r = await fetch(`/worlds/builder/session/${sid}/go-back`, { method: 'POST' })
        const j = await r.json()
        if (j.stage) setStage(j.stage)
        remaining -= 1
      }
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: `已回到「${BUILDER_STAGES[targetIdx].name}」阶段，可以重新描述。` },
      ])
      await fetchProgress(sid)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSending(false)
    }
  }

  async function finalize() {
    const sid = sessionId
    if (!sid || finalizing || sending) return
    setFinalizing(true)
    setError(null)
    try {
      const r = await fetch(`/worlds/builder/session/${sid}/finalize`, { method: 'POST' })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const j = await r.json()
      if (j.error) {
        setError(j.error)
        return
      }
      setHealth(j.health)
      const worldId = j.world_id
      await refreshWorlds()
      const w = useStore.getState().worlds.find((x) => x.id === worldId)
      if (w) {
        openWorld(w)
        onDone()
      } else {
        setError('世界已创建，但未能从列表中读取。请返回主页手动打开。')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setFinalizing(false)
    }
  }

  // ---- 模板选择屏 ----
  if (phase === 'select') {
    return (
      <div className="builder-overlay">
        <header className="topbar">
          <button className="btn" onClick={() => { resetBuilder(); onCancel(); }} title="返回主页">
            ← 返回主页
          </button>
          <div className="brand">
            <span className="dot" />
            <span className="name">新建世界</span>
          </div>
          <span className="spacer" />
          <span className="builder-progress">
            选择模板 · <b>第 0 / 7 步</b>
          </span>
        </header>
        <div className="builder-select-wrap">
          <div className="bm-label">世界构建助手</div>
          <h2 className="builder-select-title">
            从 <em>模板</em> 开始，或与 AI 自由构建
          </h2>
          <p className="builder-select-sub">
            选一个预设模板会预填规则、地点与视觉风格，然后通过 7 步对话把世界讲清楚。
          </p>
          <div className="tpl-grid">
            {BUILDER_TEMPLATES.map((t) => (
              <button
                key={t.idx}
                className="tpl-card"
                disabled={starting}
                onClick={() => selectTemplate(t.idx)}
              >
                <div className="tpl-cover" style={{ background: t.grad }}>
                  <span className="tpl-glyph">{t.glyph}</span>
                </div>
                <div className="tpl-body">
                  <h3>
                    {t.name}
                    <em>{t.en}</em>
                  </h3>
                  <div className="tpl-desc">{t.desc}</div>
                </div>
              </button>
            ))}
          </div>
          {starting && (
            <div className="loading" style={{ marginTop: 18 }}>
              正在创建构建会话…
            </div>
          )}
          {error && <div className="builder-error">⚠ {error}</div>}
        </div>
      </div>
    )
  }

  // ---- 对话屏 ----
  return (
    <div className="builder-overlay">
      <header className="topbar">
        <button className="btn" onClick={() => { resetBuilder(); onCancel(); }} title="放弃构建，返回主页">
          ← 返回主页
        </button>
        <div className="brand">
          <span className="dot" />
          <span className="name">世界构建助手</span>
        </div>
        <span className="builder-progress">
          新世界 · <b>第 {currentStageIdx + 1} / 7 步 · {stageInfo?.name}</b>
        </span>
      </header>
      <div className="builder-wrap">
        <aside className="builder-stages">
          <div className="bs-title">世界构建 · 7 步</div>
          {BUILDER_STAGES.map((s, i) => {
            const done = i < currentStageIdx
            const current = i === currentStageIdx
            const cp = checklist[s.key]
            const sub = cp ? `${s.desc} · ${cp.covered}/${cp.total}` : s.desc
            const clickable = i < currentStageIdx
            return (
              <div
                key={s.key}
                className={'stage-item' + (current ? ' current' : done ? ' done' : '')}
                onClick={() => clickable && jumpToStage(i)}
                style={{ cursor: clickable ? 'pointer' : 'default' }}
                title={clickable ? '点击回到此阶段' : ''}
              >
                <div className="num">{done ? '✓' : i + 1}</div>
                <div className="txt">
                  <div className="n">{s.name}</div>
                  <div className="d">{sub}</div>
                </div>
                {i < BUILDER_STAGES.length - 1 && <div className="stage-line" />}
              </div>
            )
          })}
          <div className="bs-collected">
            <div className="bs-c-title">已收集</div>
            <div className="bs-c-item">
              <span>规则</span>
              <b>{arrLen(collected, 'rules')}</b>
            </div>
            <div className="bs-c-item">
              <span>地点</span>
              <b>{arrLen(collected, 'locations')}</b>
            </div>
            <div className="bs-c-item">
              <span>角色</span>
              <b>{arrLen(collected, 'characters')}</b>
            </div>
          </div>
        </aside>

        <div className="builder-main">
          <div className="bm-head">
            <div className="bm-label">
              第 {currentStageIdx + 1} 步 · {stageInfo?.name}
            </div>
            <h2>{heading?.h}</h2>
            <div className="desc">{heading?.d}</div>
          </div>

          <div className="chat" ref={chatRef}>
            {messages.map((m, i) => (
              <div key={i} className={'msg ' + (m.role === 'user' ? 'me' : 'ai')}>
                <div className="who">{m.role === 'user' ? '你' : '世界构建助手'}</div>
                {m.content}
              </div>
            ))}
            {sending && (
              <div className="msg ai">
                <div className="who">世界构建助手</div>
                <span className="builder-typing">思考中…</span>
              </div>
            )}
          </div>

          {health && (
            <div className="builder-health">
              <div className="bh-title">健康检查 · {health.passed ? '通过' : '存在问题'}</div>
              {health.errors.map((e, i) => (
                <div key={'e' + i} className="bh-item bad">
                  ✕ {e}
                </div>
              ))}
              {health.warnings.map((w, i) => (
                <div key={'w' + i} className="bh-item warn">
                  ! {w}
                </div>
              ))}
              {health.errors.length === 0 && health.warnings.length === 0 && (
                <div className="bh-item ok">✓ 一切就绪，可以进入世界。</div>
              )}
            </div>
          )}

          {error && <div className="builder-error">⚠ {error}</div>}

          <div className="builder-input">
            <input
              placeholder={
                sending
                  ? '助手正在思考…'
                  : `描述「${stageInfo?.name ?? ''}」…（说"完成"进入下一步）`
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage(input)
                }
              }}
              disabled={sending || finalizing}
            />
            <button
              className="btn"
              onClick={() => sendMessage(input)}
              disabled={sending || finalizing || !input.trim()}
            >
              发送
            </button>
            <button
              className="btn"
              onClick={goBack}
              disabled={sending || finalizing || currentStageIdx === 0}
              title="返回上一步"
            >
              ↑ 返回
            </button>
          </div>

          <div className="step-actions">
            <button
              className="btn"
              onClick={() => sendMessage('完成，进入下一步')}
              disabled={sending || finalizing}
            >
              完成，进入下一步 →
            </button>
            <button
              className="btn primary"
              onClick={finalize}
              disabled={finalizing || sending}
            >
              {finalizing ? '定稿中…' : '定稿并进入世界 ▸'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============ SIM ============
type Dimension = 'worldview' | 'workbench' | 'chronicle' | 'cast' | 'story'

function SimView() {
  const [dim, setDim] = useState<Dimension>('workbench')
  const [showDirector, setShowDirector] = useState(false)
  const world = useStore((s) => s.selectedWorld)
  // 记录打开导演面板前是否在自动播放，提交/关闭后据此恢复
  const wasPlayingRef = useRef(false)

  // lock body scroll while inside the world workspace
  // (mirrors prototype `body[data-mode=world]{overflow:hidden}`)
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  // 离开世界视图时断开 WebSocket，避免后台持续推演
  useEffect(() => {
    return () => useStore.getState().disconnectWS()
  }, [])

  const openDirector = () => {
    wasPlayingRef.current = useStore.getState().autoPlay
    if (wasPlayingRef.current) useStore.getState().toggleAutoPlay()
    setShowDirector(true)
  }
  const resumeAutoPlay = () => {
    if (wasPlayingRef.current) {
      wasPlayingRef.current = false
      useStore.getState().toggleAutoPlay()
    }
  }
  const closeDirector = () => {
    setShowDirector(false)
    resumeAutoPlay()
  }

  if (!world) return null

  return (
    <>
      <WorldTopBar onOpenDirector={openDirector} />
      <WorldNav dim={dim} onChange={setDim} />
      <main className="world-main">
        <section className="view active" data-view={dim}>
          {dim === 'workbench' && <Workbench />}
          {dim === 'worldview' && <Worldview />}
          {dim === 'chronicle' && <Chronicle />}
          {dim === 'cast' && <Cast />}
          {dim === 'story' && <Story />}
        </section>
      </main>
      {showDirector && (
        <DirectorPanel
          worldId={world.id}
          onSubmitted={() => {
            setShowDirector(false)
            resumeAutoPlay()
          }}
          onClose={closeDirector}
        />
      )}
    </>
  )
}

// ============ World top bar ============
function WorldTopBar({ onOpenDirector }: { onOpenDirector: () => void }) {
  const goHome = useStore((s) => s.goHome)
  const world = useStore((s) => s.selectedWorld)
  const tick = useStore((s) => s.tick)
  const simStarted = useStore((s) => s.simStarted)
  const startingSim = useStore((s) => s.startingSim)
  const stepping = useStore((s) => s.stepping)
  const startSim = useStore((s) => s.startSim)
  const stepSim = useStore((s) => s.stepSim)

  const clockText = [world?.clock_date, `Tick ${tick}`]
    .filter(Boolean)
    .join(' · ')

  return (
    <header className="topbar">
      <button className="back-btn" onClick={goHome} title="返回世界库">
        ←
      </button>
      <div className="world-name">
        <span className="glyph">{glyphOf(world?.name ?? '?')}</span>
        {world?.name ?? '世界'}
      </div>
      <div className="clock-info">{clockText || `Tick ${tick}`}</div>
      {simStarted && (
        <span className="meter live">
          <span className="live-dot" />
          运行中
        </span>
      )}
      <span className="spacer" />
      <div className="stage-controls">
        <button
          className="btn-ctrl primary"
          onClick={simStarted ? stepSim : startSim}
          disabled={simStarted ? stepping : startingSim}
          title={simStarted ? '推进一拍 (Step)' : '启动模拟'}
        >
          ▶
        </button>
        <button
          className="btn-ctrl"
          onClick={onOpenDirector}
          disabled={!simStarted}
          title="导演介入"
        >
          🎬
        </button>
      </div>
    </header>
  )
}

// ============ World left nav ============
function WorldNav({
  dim,
  onChange,
}: {
  dim: Dimension
  onChange: (d: Dimension) => void
}) {
  const items: { key: Dimension; label: string }[] = [
    { key: 'worldview', label: '🌍 世界背景' },
    { key: 'workbench', label: '🎭 剧目舞台' },
    { key: 'chronicle', label: '⏳ 时间事件' },
    { key: 'cast', label: '👥 角色关系' },
    { key: 'story', label: '📖 故事' },
  ]
  return (
    <nav className="world-nav">
      {items.map((it) => (
        <a
          key={it.key}
          className={'wnav' + (dim === it.key ? ' active' : '')}
          onClick={() => onChange(it.key)}
        >
          {it.label}
        </a>
      ))}
    </nav>
  )
}

function useCharacters() {
  const fromSim = useStore((s) => s.characters)
  const world = useStore((s) => s.selectedWorld)
  if (fromSim.length > 0) return fromSim
  return world?.characters ?? []
}

// ============ Workbench 剧目舞台 ============
function Workbench() {
  const world = useStore((s) => s.selectedWorld)
  const characters = useCharacters()
  const events = useStore((s) => s.events)
  const simStarted = useStore((s) => s.simStarted)
  const stepping = useStore((s) => s.stepping)
  const simError = useStore((s) => s.simError)
  const tick = useStore((s) => s.tick)
  const autoPlay = useStore((s) => s.autoPlay)
  const playSpeed = useStore((s) => s.playSpeed)
  const wsStatus = useStore((s) => s.wsStatus)
  const toggleAutoPlay = useStore((s) => s.toggleAutoPlay)
  const setPlaySpeed = useStore((s) => s.setPlaySpeed)

  const wsReady = wsStatus === 'connected'
  const wsLabel =
    wsStatus === 'connected'
      ? '已连接'
      : wsStatus === 'connecting'
        ? '连接中'
        : wsStatus === 'error'
          ? '连接错误'
          : '未连接'

  return (
    <div className="wb">
      <div className="wb-panel wb-char">
        <div className="ph">登场 · {characters.length}</div>
        {characters.length === 0 ? (
          <div className="wb-empty">启动模拟后，角色将在此登场。</div>
        ) : (
          characters.map((c, i) => (
            <div className="cb-chip present" key={c + i}>
              <div className={'portrait p' + ((i % 3) + 1)}>{glyphOf(c)}</div>
              <div>
                {c}
                <div className="cb-mini">角色</div>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="wb-panel wb-center">
        <div className="ph">
          {world?.vision || world?.name || '剧目舞台'}
          <span className="ph-sub">
            Tick {tick}
            {world?.clock_date ? ' · ' + world.clock_date : ''}
          </span>
        </div>
        {world?.setting && <p className="synopsis">{world.setting}</p>}
        {simStarted && (
          <div className="wb-controls">
            <button
              className={'play-btn' + (autoPlay ? ' playing' : '')}
              onClick={toggleAutoPlay}
              disabled={!wsReady}
              title={
                autoPlay
                  ? '暂停自动推进'
                  : wsReady
                    ? '开始自动播放'
                    : 'WebSocket 未连接'
              }
            >
              {autoPlay ? '⏸ 暂停' : '▶ 自动播放'}
            </button>
            <div className="speed-group">
              <span className="speed-label">间隔</span>
              {[3000, 5000, 10000].map((ms) => (
                <button
                  key={ms}
                  className={'speed-opt' + (playSpeed === ms ? ' active' : '')}
                  onClick={() => setPlaySpeed(ms)}
                  disabled={!wsReady || autoPlay}
                  title={`${ms / 1000} 秒一拍`}
                >
                  {ms / 1000}s
                </button>
              ))}
            </div>
            <span
              className={'ws-mini ' + wsStatus}
              title={'WebSocket · ' + wsLabel}
            >
              <span className="ws-dot" />
              {wsLabel}
            </span>
          </div>
        )}
        {simError && <div className="sim-error">⚠ {simError}</div>}
        <Narrative events={events} simStarted={simStarted} stepping={stepping} />
      </div>
    </div>
  )
}

// ============ Worldview 世界背景 ============
type WvEntry = {
  group: string
  title: string
  type: 'p' | 'l'
  content: string | string[]
}

function buildWvEntries(world: World): WvEntry[] {
  const entries: WvEntry[] = []
  if (world.setting) {
    entries.push({
      group: '世界根基',
      title: '世界设定',
      type: 'p',
      content: world.setting,
    })
  }
  if (world.rules && world.rules.length > 0) {
    entries.push({
      group: '世界根基',
      title: '世界规则',
      type: 'l',
      content: world.rules,
    })
  }
  const vs = world.visual_style as Record<string, unknown> | undefined
  if (vs) {
    Object.entries(vs).forEach(([k, v]) => {
      entries.push({
        group: '视觉风格',
        title: k,
        type: 'p',
        content: String(v),
      })
    })
  }
  return entries
}

function Worldview() {
  const world = useStore((s) => s.selectedWorld)
  const [sel, setSel] = useState(0)
  if (!world) return null

  const entries = buildWvEntries(world)
  const vs = world.visual_style as Record<string, unknown> | undefined
  const vsCount = vs ? Object.keys(vs).length : 0

  const groups: string[] = []
  entries.forEach((e) => {
    if (!groups.includes(e.group)) groups.push(e.group)
  })
  const current = entries[sel]

  return (
    <div className="wv-book">
      <div className="wv-head">
        <div className="wv-title">
          {world.name} <em>{world.vision}</em>
        </div>
        <div className="meters static">
          <div className="meter live">
            <span className="live-dot" />
            {world.clock_date || 'Tick ' + (world.clock_tick ?? 0)}
          </div>
          <div className="meter">
            <span className="m-k">Tick</span>
            <span className="m-v">{world.clock_tick ?? 0}</span>
          </div>
          <div className="meter">
            <span className="m-k">规则</span>
            <span className="m-v">{world.rules?.length ?? 0}</span>
          </div>
          <div className="meter">
            <span className="m-k">视觉项</span>
            <span className="m-v">{vsCount}</span>
          </div>
        </div>
      </div>
      <div className="wv-body">
        <div className="wv-toc">
          {entries.length === 0 && (
            <div className="wv-toc-item" style={{ cursor: 'default' }}>
              尚无条目
            </div>
          )}
          {groups.map((g) => (
            <div key={g}>
              <div className="wv-toc-group">{g}</div>
              {entries
                .map((e, i) => ({ e, i }))
                .filter(({ e }) => e.group === g)
                .map(({ e, i }) => (
                  <div
                    key={e.title + i}
                    className={'wv-toc-item' + (sel === i ? ' active' : '')}
                    onClick={() => setSel(i)}
                  >
                    {e.title}
                  </div>
                ))}
            </div>
          ))}
        </div>
        <div className="wv-content">
          {!current ? (
            <div className="placeholder">
              <div className="glyph">✦</div>
              这个世界还没有更详细的设定。
            </div>
          ) : (
            <>
              <h2>{current.title}</h2>
              {current.type === 'p' ? (
                <p>{current.content as string}</p>
              ) : (
                <ul>
                  {(current.content as string[]).map((li, i) => (
                    <li key={i}>{li}</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ============ Chronicle 时间事件 ============
function Chronicle() {
  const events = useStore((s) => s.events)
  const tick = useStore((s) => s.tick)
  const world = useStore((s) => s.selectedWorld)
  const sorted = [...events].sort((a, b) => a.tick - b.tick)
  const lastEventTick = sorted.length > 0 ? sorted[sorted.length - 1].tick : 0
  const span = Math.max(tick, lastEventTick, 1)

  return (
    <div className="chr">
      <div className="chr-head">
        <div className="chr-title">时间事件</div>
        <div className="chr-sub">{world?.name ?? ''} · 按时间排列</div>
        <div className="chr-cur">
          当前 · Tick {tick}
          {world?.clock_date ? ' · ' + world.clock_date : ''}
        </div>
      </div>
      <div className="chr-tl">
        <div className="tl-bar">
          <div className="tl-ruler">
            <span className="tl-rname" />
            <span>T0</span>
            <span>T{Math.round(span / 4)}</span>
            <span>T{Math.round(span / 2)}</span>
            <span>T{Math.round((span * 3) / 4)}</span>
            <span>T{span}</span>
          </div>
          <div className="tl-row">
            <span className="tl-name">事件</span>
            <div className="tl-lane">
              {sorted.length === 0 ? (
                <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>
                  尚无事件
                </span>
              ) : (
                sorted.map((e, i) => {
                  const left = (e.tick / span) * 100
                  return (
                    <div
                      key={i}
                      className={
                        'tl-evt' + (i === sorted.length - 1 ? ' now' : '')
                      }
                      style={{ left: `${left}%` }}
                      title={`Tick ${e.tick} · ${e.type || ''}`}
                    >
                      ●{e.type || ''}
                    </div>
                  )
                })
              )}
            </div>
          </div>
          <div
            className="tl-playhead"
            style={{
              left: `calc(60px + (100% - 64px) * ${Math.min(tick / span, 1)})`,
            }}
          />
        </div>
      </div>
      <div className="chr-stream">
        {sorted.length === 0 ? (
          <div className="placeholder">
            <div className="glyph">⏳</div>
            还没有事件。启动模拟并推进时间，事件将在此按序呈现。
          </div>
        ) : (
          sorted.map((e, i) => {
            const isLast = i === sorted.length - 1
            const preview = (e.narration || '（无叙述）').slice(0, 46)
            const ellipsis =
              e.narration && e.narration.length > 46 ? '…' : ''
            return (
              <div key={i} className={'chr-evt' + (isLast ? ' now' : '')}>
                <span className="chr-t">Tick {e.tick}</span>
                <span className="chr-type">{e.type || '事件'}</span>
                <span className="chr-name">
                  {preview}
                  {ellipsis}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// ============ Cast 角色关系 ============
function Cast() {
  const characters = useCharacters()
  const world = useStore((s) => s.selectedWorld)
  return (
    <div className="cast-grid">
      <div className="cast-left">
        <div className="ph">角色 · {characters.length}</div>
        {characters.length === 0 ? (
          <div className="placeholder">
            <div className="glyph">👥</div>
            启动模拟后，登场角色会出现在这里。
          </div>
        ) : (
          <div className="char-cards">
            {characters.map((c, i) => (
              <div className="char-big" key={c + i}>
                <div className={'cb-portrait p' + ((i % 3) + 1)}>
                  {glyphOf(c)}
                </div>
                <div className="cb-body">
                  <div className="n">{c}</div>
                  <div className="r">角色</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="cast-right">
        <div className="ph">
          关系图谱 <span className="ph-sub">需要角色关系数据</span>
        </div>
        <div className="relation-map">
          <h3>关系图谱</h3>
          <div className="sub">
            {characters.length > 0
              ? `${characters.join(' · ')} 之间的关系将在数据齐备后绘制。`
              : '尚无角色。启动模拟后，角色关系会在此呈现。'}
          </div>
        </div>
        {world?.rules && world.rules.length > 0 && (
          <div className="ws-grid" style={{ marginTop: 18 }}>
            <div className="ws-card">
              <h3>世界规则</h3>
              <ul className="rule-list">
                {world.rules.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ============ Story 故事 ============
function Story() {
  const events = useStore((s) => s.events)
  const world = useStore((s) => s.selectedWorld)
  const sorted = [...events].sort((a, b) => a.tick - b.tick)
  const lastTick = sorted.length > 0 ? sorted[sorted.length - 1].tick : 0
  const wordCount = sorted.reduce((n, e) => n + (e.narration?.length ?? 0), 0)

  return (
    <div className="story-wrap">
      <div className="story-head">
        <div className="sh-label">
          {world?.name ?? ''} · {world?.vision || '叙述长卷'}
        </div>
        <h2>{world?.vision || world?.name || '故事'}</h2>
        <div className="sh-meta">
          {sorted.length} 段叙述 · 截至 Tick {lastTick} · 约 {wordCount} 字
        </div>
      </div>
      {sorted.length === 0 ? (
        <div className="placeholder">
          <div className="glyph">📖</div>
          故事尚未开始。启动模拟并推进时间，叙述将自行生长。
        </div>
      ) : (
        <article className="chapter">
          <div className="chap-no">第 一 章</div>
          <h3 className="chap-title">
            {world?.vision || world?.name || '开篇'}
          </h3>
          {sorted.map((e, i) => (
            <p key={i}>{e.narration || '（无叙述）'}</p>
          ))}
          <p className="wip">▍ 故事仍在自行生长……</p>
        </article>
      )}
    </div>
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

// ============ Director Panel 导演介入 ============
const DIRECTOR_TYPES: {
  key: DirectorDirectiveType
  soft: 'green' | 'amber' | 'red'
  softLabel: string
  title: string
  desc: string
  needsTarget: boolean
  placeholder: string
}[] = [
  {
    key: 'inject_event',
    soft: 'green',
    softLabel: '软',
    title: '注入事件',
    desc: '暴风雨、陌生人到来…',
    needsTarget: false,
    placeholder: '描述要注入的事件… 例如：一名披斗篷的旅人此刻推门而入，目光锁定艾伦。',
  },
  {
    key: 'set_goal',
    soft: 'green',
    softLabel: '软',
    title: '改角色目标',
    desc: '赋予某人新的动机',
    needsTarget: true,
    placeholder: '描述新的目标… 例如：复仇 / 守护妹妹。',
  },
  {
    key: 'modify_world',
    soft: 'amber',
    softLabel: '硬',
    title: '改世界规则',
    desc: '战争爆发、魔法失效…',
    needsTarget: false,
    placeholder: '描述世界变化… 例如：战争全面爆发，商路断绝。',
  },
  {
    key: 'force_action',
    soft: 'red',
    softLabel: '硬',
    title: '强制行动',
    desc: '令某角色做出指定行为',
    needsTarget: true,
    placeholder: '描述强制的行为… 例如：艾伦当场放下剑，跪倒在贝拉面前。',
  },
]

function DirectorPanel({
  worldId,
  onSubmitted,
  onClose,
}: {
  worldId: string
  onSubmitted: () => void
  onClose: () => void
}) {
  const injectDirective = useStore((s) => s.injectDirective)
  const characters = useCharacters()
  const [selIdx, setSelIdx] = useState(0)
  const [text, setText] = useState('')
  const [target, setTarget] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sel = DIRECTOR_TYPES[selIdx]

  async function submit() {
    const content = text.trim()
    if (!content || submitting) return
    setSubmitting(true)
    setError(null)
    let payload: Record<string, unknown>
    switch (sel.key) {
      case 'inject_event':
        payload = { description: content }
        break
      case 'set_goal':
        payload = { goal: content }
        break
      case 'modify_world':
        // 写入 state_flags，用时间戳作 key 避免相互覆盖
        payload = { key: 'state_flags', value: { [`d${Date.now()}`]: content } }
        break
      case 'force_action':
        payload = { description: content, action: content }
        break
    }
    const ok = await injectDirective(
      worldId,
      {
        type: sel.key,
        payload,
        target: sel.needsTarget ? target.trim() : '',
      },
    )
    setSubmitting(false)
    if (ok) {
      onSubmitted()
    } else {
      setError('提交失败，请查看错误提示后重试。')
    }
  }

  return (
    <>
      <div className="dp-backdrop" onClick={onClose} />
      <aside className="director-panel" role="dialog" aria-label="导演介入">
        <div className="dp-head">
          <h2>导演介入</h2>
          <button
            className="dp-close"
            onClick={onClose}
            title="关闭"
            aria-label="关闭"
          >
            ×
          </button>
        </div>
        <div className="dp-sub">
          世界将在下一 tick 接受你的意志。软介入尊重角色自主，硬介入确定生效。
        </div>

        {DIRECTOR_TYPES.map((t, i) => (
          <div
            key={t.key}
            className={'intervene-type' + (i === selIdx ? ' selected' : '')}
            onClick={() => setSelIdx(i)}
          >
            <span className={`it-soft ${t.soft}`}>{t.softLabel}</span>
            <div className="it-text">
              <div className="t">{t.title}</div>
              <div className="d">{t.desc}</div>
            </div>
          </div>
        ))}

        {sel.needsTarget && (
          <input
            className="dp-target"
            list="dp-char-list"
            placeholder="目标角色名（如：艾伦）"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            disabled={submitting}
          />
        )}
        <datalist id="dp-char-list">
          {characters.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>

        <textarea
          className="dp-textarea"
          placeholder={sel.placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={submitting}
        />

        {error && <div className="dp-error">⚠ {error}</div>}

        <button
          className="dp-submit"
          onClick={submit}
          disabled={submitting || !text.trim()}
        >
          {submitting ? '提交中…' : '提交 · 下个 tick 生效'}
        </button>
      </aside>
    </>
  )
}

export default App
