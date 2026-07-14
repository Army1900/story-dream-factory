import { useEffect, useRef } from 'react'

/** 首页光影背景：横竖线密疏不均 + 4道光带从边缘扫过（原型移植）。 */
export function CanvasBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const cv = canvasRef.current
    if (!cv) return
    const ctx = cv.getContext('2d')!
    let W = 0, H = 0
    let lines: { t: number; p: number; w: number }[] = []
    let stars: { x: number; y: number; r: number; o: number; ph: number; sp: number }[] = []

    const rnd = (a: number, b: number) => a + Math.random() * (b - a)

    function build() {
      lines = []
      const avgH = H / 72, avgV = W / 72
      let y = rnd(avgH * 0.3, avgH * 0.8)
      while (y < H) { lines.push({ t: 0, p: y, w: rnd(0.7, 1.6) }); y += rnd(avgH * 0.4, avgH * 1.7) }
      let x = rnd(avgV * 0.3, avgV * 0.8)
      while (x < W) { lines.push({ t: 1, p: x, w: rnd(0.7, 1.6) }); x += rnd(avgV * 0.4, avgV * 1.7) }
      stars = []
      for (let i = 0; i < 90; i++) stars.push({ x: rnd(0, W), y: rnd(0, H), r: rnd(0.3, 1.3), o: rnd(0.2, 0.6), ph: rnd(0, 6.283), sp: rnd(0.6, 2.2) })
    }

    function resize() { W = cv!.width = innerWidth; H = cv!.height = innerHeight; build() }

    let t = 0
    let rafId: number

    function frame() {
      t += 0.016
      ctx.clearRect(0, 0, W, H)
      ctx.strokeStyle = '#ffffff'
      ctx.lineCap = 'round'
      ctx.shadowColor = 'rgba(255,255,255,.9)'

      const Hr = H + 300, Vr = W + 300
      const bh1 = ((t * 52) % Hr) - 150
      const bh2 = ((t * 38 + Hr * 0.5) % Hr) - 150
      const bv1 = ((t * 46) % Vr) - 150
      const bv2 = ((t * 33 + Vr * 0.4) % Vr) - 150
      const D = 24200

      for (let i = 0; i < lines.length; i++) {
        const l = lines[i]
        let c: number
        if (l.t === 0) { const d1 = l.p - bh1, d2 = l.p - bh2; c = Math.exp(-d1 * d1 / D) + Math.exp(-d2 * d2 / D) }
        else { const e1 = l.p - bv1, e2 = l.p - bv2; c = Math.exp(-e1 * e1 / D) + Math.exp(-e2 * e2 / D) }
        let o = 0.16 + 0.34 * c; if (o > 0.85) o = 0.85
        ctx.globalAlpha = o
        ctx.lineWidth = l.w
        ctx.shadowBlur = 3 + o * 9
        ctx.beginPath()
        if (l.t === 0) { ctx.moveTo(0, l.p); ctx.lineTo(W, l.p) } else { ctx.moveTo(l.p, 0); ctx.lineTo(l.p, H) }
        ctx.stroke()
      }

      ctx.shadowBlur = 0
      ctx.fillStyle = '#ffffff'
      for (let j = 0; j < stars.length; j++) {
        const s2 = stars[j]
        ctx.globalAlpha = s2.o * (0.4 + 0.6 * Math.sin(t * s2.sp + s2.ph))
        ctx.beginPath()
        ctx.arc(s2.x, s2.y, s2.r, 0, 6.283)
        ctx.fill()
      }
      ctx.globalAlpha = 1
      rafId = requestAnimationFrame(frame)
    }

    resize()
    frame()
    addEventListener('resize', resize)

    return () => { cancelAnimationFrame(rafId); removeEventListener('resize', resize) }
  }, [])

  return (
    <div className="cosmos">
      <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
    </div>
  )
}
