import React, { useEffect, useMemo, useRef, useState } from 'react'
import type { AtlasMeta } from '@/lib/api'

type Props = {
  atlas: AtlasMeta
  sheetUrl: string
  pose: string
  fps?: number
  scalePx?: number
}

export default function PosePlayer({ atlas, sheetUrl, pose, fps = 8, scalePx = 2 }: Props) {
  const frames = useMemo(() => {
    const arr = (atlas?.frames || []).filter(f => f.pose === pose)
    arr.sort((a, b) => (a.index ?? 0) - (b.index ?? 0))
    return arr
  }, [atlas, pose])

  const cellW = atlas?.meta?.cell?.w ?? frames[0]?.frame?.w ?? 64
  const cellH = atlas?.meta?.cell?.h ?? frames[0]?.frame?.h ?? 64

  const [playing, setPlaying] = useState(true)
  const [frameIdx, setFrameIdx] = useState(0)
  const [speed, setSpeed] = useState<number>(fps)

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const sheetImgRef = useRef<HTMLImageElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const lastTimeRef = useRef<number>(0)
  const accRef = useRef<number>(0)

  useEffect(() => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      sheetImgRef.current = img
      draw(0)
    }
    img.src = sheetUrl
    return () => { sheetImgRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sheetUrl])

  useEffect(() => { setFrameIdx(0) }, [pose])

  const draw = (idx: number) => {
    const cvs = canvasRef.current
    const img = sheetImgRef.current
    if (!cvs || !img || frames.length === 0) return
    const ctx = cvs.getContext('2d')
    if (!ctx) return

    const fr = frames[Math.max(0, Math.min(idx, frames.length - 1))]
    const { x, y, w, h } = fr.frame

    const W = Math.round(cellW * scalePx)
    const H = Math.round(cellH * scalePx)
    if (cvs.width !== W || cvs.height !== H) {
      cvs.width = W; cvs.height = H
      ;(ctx as any).imageSmoothingEnabled = false
    }
    ctx.clearRect(0, 0, W, H)
    ctx.drawImage(img, x, y, w, h, 0, 0, W, H)
  }

  useEffect(() => {
    if (frames.length === 0) return
    const stepMs = 1000 / Math.max(1, speed)

    const tick = (t: number) => {
      if (!lastTimeRef.current) lastTimeRef.current = t
      const dt = t - lastTimeRef.current
      lastTimeRef.current = t

      if (playing) {
        accRef.current += dt
        while (accRef.current >= stepMs) {
          accRef.current -= stepMs
          setFrameIdx(i => (i + 1) % frames.length)
        }
      }

      draw(frameIdx)
      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rafRef.current = null
      lastTimeRef.current = 0
      accRef.current = 0
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed, frames.length, sheetUrl, pose])

  useEffect(() => { draw(frameIdx) }, [frameIdx]) // eslint-disable-line

  if (frames.length === 0) {
    return <div className="text-sm text-amber-400">No frames for pose “{pose}”.</div>
  }

  return (
    <div className="rounded-xl border border-zinc-700 p-3 bg-zinc-900/70">
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={() => setPlaying(p => !p)}
          className="px-2 py-1 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-xs"
          title={playing ? 'Pause' : 'Play'}
        >
          {playing ? '❚❚ Pause' : '► Play'}
        </button>

        <button
          onClick={() => { setPlaying(false); setFrameIdx(i => (i - 1 + frames.length) % frames.length) }}
          className="ml-2 px-2 py-1 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-xs"
          title="Previous frame"
        >
          ‹
        </button>
        <button
          onClick={() => { setPlaying(false); setFrameIdx(i => (i + 1) % frames.length) }}
          className="px-2 py-1 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-xs"
          title="Next frame"
        >
          ›
        </button>

        <div className="ml-3 text-xs opacity-80">
          frame {frameIdx + 1} / {frames.length}
        </div>

        <div className="ml-auto flex items-center gap-2 text-xs opacity-80">
          <span>FPS</span>
          <input
            type="range"
            min={1}
            max={24}
            step={1}
            value={speed}
            onChange={(e) => setSpeed(parseInt(e.target.value, 10))}
          />
          <span>{speed}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-2 text-xs opacity-80">
        <span>Scrub</span>
        <input
          type="range"
          min={1}
          max={frames.length}
          step={1}
          value={frameIdx + 1}
          onChange={(e) => { setPlaying(false); setFrameIdx(parseInt(e.target.value, 10) - 1) }}
          className="flex-1"
        />
      </div>

      <div className="flex items-center justify-center">
        <canvas
          ref={canvasRef}
          style={{
            imageRendering: 'pixelated',
            borderRadius: '0.75rem',
            background: '#0a0a0a',
            border: '1px solid #3f3f46',
          }}
        />
      </div>
    </div>
  )
}
