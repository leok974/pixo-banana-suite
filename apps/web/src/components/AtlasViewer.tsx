import { useMemo, useRef, useState, useEffect } from 'react'
import type { AtlasMeta } from '@/lib/api'

type Props = {
  sheetUrl: string   // e.g. /view/1_sheet.png
  atlas: AtlasMeta
  poseFilter?: string | null
}

export default function AtlasViewer({ sheetUrl, atlas, poseFilter }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const [zoom, setZoom] = useState(1)        // 1 = natural size
  const [hoverKey, setHoverKey] = useState<string | null>(null)

  // Filter frames by pose (if set)
  const frames = useMemo(() => {
    const all = atlas?.frames ?? []
    return poseFilter ? all.filter(f => f.pose === poseFilter) : all
  }, [atlas, poseFilter])

  // Compute overlay rects scaled to rendered <img> size
  const rects = useMemo(() => {
    return frames.map((f) => ({
      key: `${f.pose}-${f.index}`,
      x: f.frame.x, y: f.frame.y, w: f.frame.w, h: f.frame.h,
      pose: f.pose, index: f.index
    }))
  }, [frames])

  // Allow wheel zoom with Ctrl/Cmd
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        const dir = e.deltaY > 0 ? -0.1 : 0.1
        setZoom(z => Math.max(0.25, Math.min(4, z + dir)))
      }
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])

  const W = atlas?.meta?.size?.w ?? 0
  const H = atlas?.meta?.size?.h ?? 0
  const cssW = Math.round(W * zoom)
  const cssH = Math.round(H * zoom)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3 text-sm opacity-80">
        <span>Zoom</span>
        <input
          type="range"
          min={0.25} max={4} step={0.05}
          value={zoom}
          onChange={(e)=> setZoom(parseFloat(e.target.value))}
          className="w-48"
        />
        <span>{Math.round(zoom * 100)}%</span>
        <span className="ml-4">Cell: {atlas.meta.cell.w}×{atlas.meta.cell.h}</span>
        <span>Cols: {atlas.meta.columns}</span>
        <span>Size: {W}×{H}px</span>
      </div>

      <div
        ref={containerRef}
        className="relative overflow-auto rounded-xl border border-zinc-700 bg-zinc-950"
        style={{ maxHeight: 480 }}
      >
        <div
          className="relative"
          style={{ width: cssW, height: cssH }}
        >
          <img
            ref={imgRef}
            src={sheetUrl}
            alt="sprite sheet"
            draggable={false}
            className="select-none block"
            style={{ width: cssW, height: cssH, imageRendering: 'pixelated' as any }}
          />
          {/* overlays */}
          {rects.map(r => {
            const x = Math.round(r.x * zoom)
            const y = Math.round(r.y * zoom)
            const w = Math.round(r.w * zoom)
            const h = Math.round(r.h * zoom)
            const isHover = hoverKey === r.key
            return (
              <div
                key={r.key}
                title={`${r.pose} #${r.index}`}
                className={`absolute border ${isHover ? 'border-white' : 'border-zinc-500/70'} bg-white/5`}
                style={{ left: x, top: y, width: w, height: h }}
                onMouseEnter={() => setHoverKey(r.key)}
                onMouseLeave={() => setHoverKey(null)}
              >
                <div className="absolute top-0 left-0 text-[10px] px-1 py-0.5 bg-zinc-900/70">
                  {r.pose} #{r.index}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
