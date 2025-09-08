// apps/web/src/components/ChatDock.tsx
import { useEffect, useMemo, useRef, useState } from "react"
import { pingAPI, fetchRoots, postPoses, postEdit, postAnimate } from "../lib/api"
import AtlasViewer from './AtlasViewer'
import PosePlayer from './PosePlayer'
import type { AtlasMeta } from '@/lib/api'
import { agentChat } from "../lib/api"

type Msg = { role: "user" | "assistant" | "system"; content: string; ts: number }

function DotThinking() {
  // simple animated dots
  return (
    <div className="text-xs text-zinc-400 flex items-center gap-2">
      <span className="inline-block animate-pulse">●</span>
      <span className="inline-block animate-pulse [animation-delay:.15s]">●</span>
      <span className="inline-block animate-pulse [animation-delay:.3s]">●</span>
      <span>thinking…</span>
    </div>
  )
}

export function ChatDock() {
  const API_BASE = (document.querySelector('meta[name="api-base"]') as HTMLMetaElement)?.content || ''
  const [wideMode, setWideMode] = useState(true)
  const [open, setOpen] = useState(true)
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Msg[]>([])
  const [sending, setSending] = useState(false)
  const [fixedCell, setFixedCell] = useState(false)
  const [cellW, setCellW] = useState(128)
  const [cellH, setCellH] = useState(128)
  const [preset, setPreset] = useState<"auto"|"64"|"96"|"128"|"256"|"custom">("auto")
  const [preview, setPreview] = useState<{sheet?: string; gif?: string} | null>(null)
  const [lastByPose, setLastByPose] = useState<Record<string, string[]> | null>(null)
  const [lastAtlas, setLastAtlas] = useState<AtlasMeta | null>(null)
  const [lastSheetUrl, setLastSheetUrl] = useState<string | null>(null)
  const [gifPose, setGifPose] = useState<string | null>(null)
  const [poseFilter, setPoseFilter] = useState<string | null>(null)

  // Pose selection state
  const POSE_LIST = [
    "idle","walk","run","attack","spell","hurt","die","jump","cast","defend"
  ] as const
  type PoseName = typeof POSE_LIST[number]
  const BASIC_POSES: PoseName[] = ["idle","walk","attack","spell"]
  // Default only 'idle' selected per request
  const [poseSel, setPoseSel] = useState<Record<PoseName, boolean>>(
    Object.fromEntries(POSE_LIST.map(p => [p, p === 'idle'])) as Record<PoseName, boolean>
  )
  // Default frame counts per pose
  const DEFAULT_FRAMES: Record<PoseName, number> = {
    idle: 4,
    walk: 8,
    run: 8,
    attack: 6,
    spell: 6,
    hurt: 4,
    die: 6,
    jump: 6,
    cast: 6,
    defend: 4,
  }
  const [poseFrames, setPoseFrames] = useState<Record<PoseName, number>>(
    Object.fromEntries(POSE_LIST.map(p => [p, DEFAULT_FRAMES[p]])) as Record<PoseName, number>
  )
  const selectedCount = (POSE_LIST as readonly PoseName[]).reduce((acc, p) => acc + (poseSel[p] ? 1 : 0), 0)
  function setAllPoses(v: boolean) {
    setPoseSel(Object.fromEntries(POSE_LIST.map(p => [p, v])) as Record<PoseName, boolean>)
  }
  function setBasicPoses() {
    setPoseSel(Object.fromEntries(POSE_LIST.map(p => [p, BASIC_POSES.includes(p)])) as Record<PoseName, boolean>)
  }
  function selectedPoses(): {name: string; frames?: number}[] {
    return (POSE_LIST as readonly PoseName[])
      .filter(p => poseSel[p])
      .map(p => {
        const f = poseFrames[p]
        return f && f > 0 ? { name: p, frames: f } : { name: p }
      })
  }

  const listRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, sending])

  // helper: sync preset → fields
  function applyPreset(p: typeof preset) {
    setPreset(p)
    if (p === "auto") { setFixedCell(false); return }
    setFixedCell(true)
    const size = p === "custom" ? null : Number(p)
    if (size) { setCellW(size); setCellH(size) }
  }

  // Derived: fixed mode when preset not auto (or legacy fixedCell state)
  const isFixed = preset !== "auto" || fixedCell

  // Tool actions (now *in* the chat)
  const actions = useMemo(() => ([
    {
      key: "ping",
      label: "Ping Backend",
      run: async () => {
        const r = await pingAPI()
        return "Ping → " + JSON.stringify(r)
      }
    },
    {
      key: "roots",
      label: "Check Roots",
      run: async () => {
        const r = await fetchRoots()
        return "Roots → " + JSON.stringify(r)
      }
    },
  {
      key: "poses",
      label: "Make Poses",
      run: async () => {
        const r = await postPoses({
          image_path: "assets/inputs/1.png", // <-- your generated image here
          poses: selectedPoses(),
          fps: 8,
          sheet_cols: 3,
          fixed_cell: isFixed,
          cell_w: isFixed ? cellW : undefined,
          cell_h: isFixed ? cellH : undefined,
        })
        setPreview({ sheet: (r as any)?.urls?.sprite_sheet, gif: (r as any)?.urls?.gif })
        if ((r as any)?.by_pose) {
          const bp = (r as any).by_pose as Record<string, string[]>
          setLastByPose(bp)
          const first = Object.keys(bp)[0]
          setGifPose(first || null)
          setPoseFilter(first || null)
        }
        if ((r as any)?.atlas) setLastAtlas((r as any).atlas as AtlasMeta)
        // Build reliable sheet URL (absolute when API_BASE exists)
        if ((r as any)?.urls?.sprite_sheet) {
          const raw = (r as any).urls.sprite_sheet as string
          const url = raw.startsWith('/view')
            ? (API_BASE ? new URL(raw, API_BASE).toString() : raw)
            : raw
          setLastSheetUrl(url)
        } else if ((r as any)?.sprite_sheet) {
          const rel = ((r as any).sprite_sheet as string).replace(/^assets\/outputs\//, '')
          const url = API_BASE ? new URL(`/view/${rel}`, API_BASE).toString() : `/view/${rel}`
          setLastSheetUrl(url)
        }
        const u = (r as any)?.edit_info?.used_model
        const reason = (r as any)?.edit_info?.reason
        const edited = (r as any)?.edit_info?.edited_path
        const so = (r as any)?.sheet_options
        const chosenPoses = ((r as any)?.frames ?? [])
          .map((s: string) => (s as string).match(/_(\w+)_\d+\.png$/i)?.[1])
          .filter(Boolean)
          .slice(0, 5)
        const lines = [
          `Edit → Poses → Animate complete. (edit=${u || "?"}${reason ? `, reason=${reason}` : ""})`,
          so?.fixed_cell ? `cell: ${so.cell_w}×${so.cell_h}` : `cell: auto`,
          chosenPoses.length ? `poses: ${Array.from(new Set(chosenPoses as string[])).join(", ")}` : "",
          edited ? `edited: ${edited}` : "",
          (r as any)?.urls?.sprite_sheet ? `sheet: ${(r as any).urls.sprite_sheet}` : "",
          (r as any)?.urls?.gif ? `gif: ${(r as any).urls.gif}` : "",
        ].filter(Boolean)
        return lines.join("\n")
      }
    },
    {
      key: "edit",
      label: "Nano Edit",
      run: async () => {
        const r = await postEdit({
          items: [{
            image_path: "assets/inputs/char.png",
            instruction: "make the cloak blue and add sparkles"
          }]
        })
        return "Edit → " + JSON.stringify(r)
      }
    },
    {
      key: "animate",
      label: "Animate",
      run: async () => {
        const payload = lastByPose
          ? {
              items: [{
                by_pose: lastByPose!,
                pose_for_gif: gifPose ?? undefined,
                fps: 8,
                sheet_cols: 4,
                basename: "pb_anim",
                ...(isFixed ? { fixed_cell: true, cell_w: cellW, cell_h: cellH } : {}),
              }]
            }
          : {
              items: [{
                frames: [
                  "assets/inputs/1.png",
                  "assets/inputs/2.png",
                  "assets/inputs/3.png",
                ],
                fps: 8,
                sheet_cols: 4,
                basename: "pb_anim",
              }]
            }
        const r = await postAnimate(payload as any)
        const item = (r as any)?.items?.[0]
        if (item?.atlas) setLastAtlas(item.atlas as AtlasMeta)
        // Build reliable sheet URL after /animate
        if (item?.urls?.sprite_sheet) {
          const raw: string = item.urls.sprite_sheet
          const url = raw.startsWith('/view')
            ? (API_BASE ? new URL(raw, API_BASE).toString() : raw)
            : raw
          setLastSheetUrl(url)
        } else if (item?.sprite_sheet) {
          const rel = (item.sprite_sheet as string).replace(/^assets\/outputs\//, '')
          const url = API_BASE ? new URL(`/view/${rel}`, API_BASE).toString() : `/view/${rel}`
          setLastSheetUrl(url)
        }
        if (item?.gif || item?.sprite_sheet) {
          return [
            "Animate → done",
            item?.sprite_sheet ? `sheet: ${item.sprite_sheet}` : "",
            item?.gif ? `gif: ${item.gif}` : ""
          ].filter(Boolean).join("\n")
        }
        return "Animate → " + JSON.stringify(r)
      }
    },
  ]), [preset, cellW, cellH, poseSel, sending])

  // crude NL router: if the text mentions "pose"/"poses" it will call /pipeline/poses.
  // It tries to extract an image path like "from assets/inputs/1.png" or "from 1.png".
  async function sendUser(text: string) {
    if (!text.trim()) return
    setMessages(m => [...m, { role: "user", content: text, ts: Date.now() }])
    setInput("")
    setSending(true)
    try {
      const lower = text.toLowerCase()
  const mentionsPoses = /\bpose(s)?\b/.test(lower) || /\bmake\s+poses\b/.test(lower)

  if (mentionsPoses) {
        // very light Parse: image path after "from"
        const imgMatch = text.match(/from\s+([^\s'\"]+)/i)
        const image_path = imgMatch ? imgMatch[1] : "assets/inputs/1.png"

        // pull pose words if user names them, else default three
  // Use the UI selection; if empty, ensure at least idle
  const poses = selectedPoses()
  if (poses.length === 0) poses.push({ name: "idle" })

        const payload = {
          image_path,
          poses,
          fps: 8,
          sheet_cols: 3,
          fixed_cell: isFixed,
          cell_w: isFixed ? cellW : undefined,
          cell_h: isFixed ? cellH : undefined,
        }

        const r = await postPoses(payload)
        setPreview({ sheet: (r as any)?.urls?.sprite_sheet, gif: (r as any)?.urls?.gif })
        if ((r as any)?.by_pose) {
          const bp = (r as any).by_pose as Record<string, string[]>
          setLastByPose(bp)
          const first = Object.keys(bp)[0]
          setGifPose(first || null)
        }
        if ((r as any)?.atlas) setLastAtlas((r as any).atlas as AtlasMeta)
        // Build reliable sheet URL in NL flow too
        if ((r as any)?.urls?.sprite_sheet) {
          const raw = (r as any).urls.sprite_sheet as string
          const url = raw.startsWith('/view')
            ? (API_BASE ? new URL(raw, API_BASE).toString() : raw)
            : raw
          setLastSheetUrl(url)
        } else if ((r as any)?.sprite_sheet) {
          const rel = ((r as any).sprite_sheet as string).replace(/^assets\/outputs\//, '')
          const url = API_BASE ? new URL(`/view/${rel}`, API_BASE).toString() : `/view/${rel}`
          setLastSheetUrl(url)
        }
        const u = (r as any)?.edit_info?.used_model
        const reason = (r as any)?.edit_info?.reason
        const edited = (r as any)?.edit_info?.edited_path
        const so = (r as any)?.sheet_options
        const chosenPoses = ((r as any)?.frames ?? [])
          .map((s: string) => (s as string).match(/_(\w+)_\d+\.png$/i)?.[1])
          .filter(Boolean)
          .slice(0, 5)
        const lines = [
          `Edit → Poses → Animate complete. (edit=${u || "?"}${reason ? `, reason=${reason}` : ""})`,
          so?.fixed_cell ? `cell: ${so.cell_w}×${so.cell_h}` : `cell: auto`,
          chosenPoses.length ? `poses: ${Array.from(new Set(chosenPoses as string[])).join(", ")}` : "",
          edited ? `edited: ${edited}` : "",
          (r as any)?.urls?.sprite_sheet ? `sheet: ${(r as any).urls.sprite_sheet}` : "",
          (r as any)?.urls?.gif ? `gif: ${(r as any).urls.gif}` : ""
        ].filter(Boolean)
        const reply = lines.join("\n") || "(done)"
        setMessages(m => [...m, { role: "assistant", content: reply, ts: Date.now() }])
      } else {
        // fall back to normal agent chat
        const resp = await agentChat({
          messages: [{ role: "user", content: text }],
          intent: "auto"
        })
        const reply = resp?.reply ?? "(no reply)"
        setMessages(m => [...m, { role: "assistant", content: reply, ts: Date.now() }])
      }
    } catch (e: any) {
      setMessages(m => [...m, { role: "assistant", content: String(e?.message ?? e), ts: Date.now() }])
    } finally {
      setSending(false)
    }
  }

  async function runAction(run: () => Promise<string>, label: string) {
    setMessages(m => [...m, { role: "user", content: `[tool] ${label}`, ts: Date.now() }])
    setSending(true)
    try {
      const out = await run()
      setMessages(m => [...m, { role: "assistant", content: out, ts: Date.now() }])
    } catch (e: any) {
      setMessages(m => [...m, { role: "assistant", content: `Error → ${String(e?.message ?? e)}`, ts: Date.now() }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className={wideMode
      ? "fixed inset-0 z-40 bg-zinc-950/95 backdrop-blur supports-[backdrop-filter]:bg-zinc-950/70"
      : "fixed bottom-4 right-4 z-[70] w-[480px] md:w-[560px] max-h-[80vh] overflow-hidden"
    }>
      <div className={wideMode ? "h-full w-full max-w-screen-2xl mx-auto p-4 overflow-auto" : "h-full"}>
        {/* header */}
        <div className="flex items-center gap-2 mb-2 sticky top-4">
          <button
            className="px-3 py-1.5 rounded-lg border border-zinc-700 hover:bg-zinc-800"
            onClick={()=> setWideMode(!wideMode)}
            title={wideMode ? "Switch to docked" : "Switch to wide"}
          >
            {wideMode ? "Dock" : "Wide"}
          </button>
          <div className="text-sm font-medium">Agent</div>
          <button
            className="sticky top-4 right-4 ml-auto block px-3 py-1.5 rounded-lg border border-zinc-700 hover:bg-zinc-800"
            onClick={() => setOpen(o => !o)}
          >
            {open ? "Collapse" : "Expand"}
          </button>
        </div>
        <div className={wideMode
          ? "rounded-2xl border border-zinc-800 bg-zinc-900/90 shadow-lg min-h-[60vh]"
          : "rounded-2xl border border-zinc-800 bg-zinc-900 shadow-lg max-h-[70vh] overflow-y-auto"
        }>
        {open && (
          <div className="p-3 space-y-3">
            {/* Quick tools row (moved into chat) */}
            <div className="grid grid-cols-2 gap-2">
              {actions.map(a => (
                <button
                  key={a.key}
                  onClick={() => runAction(a.run, a.label)}
                  className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-left text-xs hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={(a.key === 'poses' && (selectedCount === 0 || sending))}
                  title={a.key === 'poses' && selectedCount === 0 ? 'Pick at least one pose.' : undefined}
                >
                  {a.label}
                </button>
              ))}
            </div>
            {selectedCount === 0 && (
              <div className="text-amber-400 text-sm">Pick at least one pose.</div>
            )}

            {/* Sprite sheet options */}
            <div className="rounded-lg border border-zinc-800 p-3 bg-zinc-950/50 space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <label className="text-sm">Sprite cell size</label>
                <select
                  className="rounded bg-zinc-800 border border-zinc-700 px-2 py-1 text-sm"
                  value={preset}
                  onChange={(e) => applyPreset(e.target.value as any)}
                >
                  <option value="auto">Auto (infer)</option>
                  <option value="64">64 × 64</option>
                  <option value="96">96 × 96</option>
                  <option value="128">128 × 128</option>
                  <option value="256">256 × 256</option>
                  <option value="custom">Custom…</option>
                </select>

                <div className="flex items-center gap-2 text-sm">
                  <label>W</label>
                  <input
                    type="number" min={8}
                    className="w-20 rounded bg-zinc-800 border border-zinc-700 px-2 py-1"
                    value={cellW}
                    onChange={(e) => setCellW(parseInt(e.target.value || "0", 10))}
                    disabled={preset !== "custom"}
                  />
                  <label>H</label>
                  <input
                    type="number" min={8}
                    className="w-20 rounded bg-zinc-800 border border-zinc-700 px-2 py-1"
                    value={cellH}
                    onChange={(e) => setCellH(parseInt(e.target.value || "0", 10))}
                    disabled={preset !== "custom"}
                  />
                </div>
              </div>

              <div className="text-xs text-zinc-500">
                Auto: infer compact cells from the first frame. Fixed: lock exact pixel size (nearest-neighbor).
              </div>
            </div>

            {/* Pose picker */}
            <div className="rounded-lg border border-zinc-800 p-3 bg-zinc-950/50 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium">Poses</div>
                <div className="flex gap-2">
                  <button
                    className="text-xs underline text-zinc-300 hover:text-zinc-100"
                    onClick={() => setAllPoses(true)}
                  >All</button>
                  <button
                    className="text-xs underline text-zinc-300 hover:text-zinc-100"
                    onClick={() => setAllPoses(false)}
                  >None</button>
                  <button
                    className="text-xs underline text-zinc-300 hover:text-zinc-100"
                    onClick={setBasicPoses}
                  >Basic</button>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {POSE_LIST.map(p => (
                  <label key={p} className="flex items-center justify-between gap-2 text-sm rounded-lg border border-zinc-800 bg-zinc-900 px-2 py-1">
                    <span className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={poseSel[p]}
                        onChange={(e) => setPoseSel(prev => ({ ...prev, [p]: e.target.checked }))}
                      />
                      <span className="capitalize">{p}</span>
                    </span>
                    {poseSel[p] && (
                      <span className="flex items-center gap-2 text-[11px] opacity-90">
                        frames
                        <input
                          type="number"
                          min={1}
                          value={poseFrames[p]}
                          onChange={(e) => {
                            const v = parseInt(e.target.value || '1', 10)
                            setPoseFrames(prev => ({ ...prev, [p]: Number.isFinite(v) && v > 0 ? v : 1 }))
                          }}
                          className="w-16 rounded bg-zinc-900 border border-zinc-700 px-2 py-1"
                        />
                      </span>
                    )}
                  </label>
                ))}
              </div>

              <div className="text-[11px] text-zinc-500">
                These poses will be used by “Make Poses” and by natural text commands that trigger posing.
              </div>
            </div>

            {/* GIF pose selector (after /poses) */}
            {lastByPose && (
              <div className="rounded-lg border border-zinc-800 p-3 bg-zinc-950/50 space-y-2">
                <label className="flex items-center gap-2 text-sm">
                  <span className="font-medium">GIF pose</span>
                  <select
                    className="rounded bg-zinc-900 border border-zinc-700 px-2 py-1"
                    value={gifPose ?? ''}
                    onChange={(e) => setGifPose(e.target.value || null)}
                  >
                    {Object.keys(lastByPose).map(k => (
                      <option key={k} value={k}>{k}</option>
                    ))}
                  </select>
                </label>
              </div>
            )}

            {/* Message list */}
            <div ref={listRef} className="h-52 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950/50 p-2">
              {messages.map((m, i) => (
                <div key={i} className={`mb-2 ${m.role === "user" ? "text-zinc-100" : "text-zinc-300"}`}>
                  <span className="text-xs uppercase text-zinc-500 mr-2">{m.role}</span>
                  <span className="text-sm whitespace-pre-wrap break-words">{m.content}</span>
                </div>
              ))}
              {sending && <DotThinking />}
              {!sending && messages.length === 0 && (
                <div className="text-xs text-zinc-500">Type a message or try a tool above.</div>
              )}
            </div>

            {/* Preview panel */}
            {preview && (preview.sheet || preview.gif) && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-2 space-y-2">
                <div className="text-xs text-zinc-400">Preview</div>
                {preview.sheet && (
                  <a href={preview.sheet} target="_blank" rel="noreferrer" className="block">
                    <img src={preview.sheet} alt="sprite-sheet" className="max-h-48 w-auto rounded border border-zinc-800" />
                  </a>
                )}
                {preview.gif && (
                  <a href={preview.gif} target="_blank" rel="noreferrer" className="inline-block">
                    <img src={preview.gif} alt="gif" className="h-20 w-auto rounded border border-zinc-800" />
                  </a>
                )}
                <div className="text-[10px] text-zinc-500">
                  Click to open full size. (Served from <code>/view</code>)
                </div>
              </div>
            )}

            {/* Atlas toolbar */}
            {lastAtlas && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-2 mt-2">
                <div className="flex items-center gap-3">
                  <span className="text-sm opacity-80">Pose filter</span>
                  <select
                    className="rounded bg-zinc-900 border border-zinc-700 px-2 py-1"
                    value={poseFilter ?? ''}
                    onChange={(e)=> setPoseFilter(e.target.value || null)}
                  >
                    {Array.from(new Set(lastAtlas.frames.map(f => f.pose))).map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                  <button
                    className="ml-auto px-3 py-1.5 rounded-lg border border-zinc-700 hover:bg-zinc-800"
                    onClick={() => {
                      if (!lastAtlas) return
                      const blob = new Blob([JSON.stringify(lastAtlas, null, 2)], { type: 'application/json' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `${lastAtlas.meta?.image?.replace(/\.(png|webp)$/i, '') || 'sheet'}.json`
                      a.click()
                      URL.revokeObjectURL(url)
                    }}
                  >
                    Download atlas JSON
                  </button>
                </div>
              </div>
            )}

            {/* Tiny play/stop scrubber for the selected pose */}
            {lastAtlas && lastSheetUrl && (poseFilter || gifPose) && (
              <div className="mt-3">
                <PosePlayer atlas={lastAtlas} sheetUrl={lastSheetUrl} pose={(poseFilter || gifPose)!} fps={8} scalePx={2} />
              </div>
            )}

            {/* Atlas viewer */}
            {lastAtlas && lastSheetUrl && (
              <div className="mt-3">
                <AtlasViewer sheetUrl={lastSheetUrl} atlas={lastAtlas} poseFilter={poseFilter} />
              </div>
            )}

            {/* Always show a bottom Preview panel */}
            <div className="mt-3">
              <div className="text-sm opacity-80 mb-1">Preview</div>
              <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-2">
                {lastSheetUrl && (
                  <a href={lastSheetUrl} target="_blank" rel="noreferrer" className="block text-xs opacity-70 mb-2">
                    Click to open full size
                  </a>
                )}
                {lastSheetUrl ? (
                  <img
                    src={lastSheetUrl}
                    alt="sprite sheet"
                    className="w-full max-w-full rounded-lg border border-zinc-800 mt-2 object-contain max-h-[360px]"
                    draggable={false}
                  />
                ) : (
                  <div className="text-sm opacity-60">No preview yet.</div>
                )}
              </div>
            </div>

            {/* Composer */}
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-lg bg-zinc-800 px-3 py-2 text-sm outline-none border border-zinc-700"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask the agent…"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    sendUser(input)
                  }
                }}
              />
              <button
                className="rounded-lg bg-zinc-100 text-zinc-900 px-3 text-sm font-medium"
                onClick={() => sendUser(input)}
                disabled={sending}
              >
                Send
              </button>
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  )
}
