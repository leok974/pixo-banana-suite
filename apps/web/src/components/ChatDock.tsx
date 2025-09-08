// apps/web/src/components/ChatDock.tsx
import { useEffect, useMemo, useRef, useState } from "react"
import { pingAPI, fetchRoots, postPoses, postEdit, postAnimate } from "../lib/api"
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
  const [open, setOpen] = useState(true)
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Msg[]>([])
  const [sending, setSending] = useState(false)

  const listRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, sending])

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
          instruction: "keep the armor silhouette; tint cloak blue; add faint glow",
          poses: [{ name: "idle" }, { name: "attack" }, { name: "spell" }],
          fps: 8,
          sheet_cols: 3,
          out_dir: "assets/outputs",
          basename: "knightA"
        })
        const u = (r as any)?.edit_info?.used_model
        const reason = (r as any)?.edit_info?.reason
        const edited = (r as any)?.edit_info?.edited_path
        const lines = [
          `Edit → Poses → Animate complete. (edit=${u || "?"}${reason ? `, reason=${reason}` : ""})`,
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
        const r = await postAnimate({
          items: [{
            frames: [
              "assets/inputs/1.png",
              "assets/inputs/2.png",
              "assets/inputs/3.png"
            ],
            fps: 8,
            sheet_cols: 4,
            basename: "test_anim"
          }]
        })
        const item = (r as any)?.items?.[0]
        if (item?.urls?.gif || item?.urls?.sprite_sheet) {
          return [
            "Animate → done",
            item?.urls?.sprite_sheet ? `sheet: ${item.urls.sprite_sheet}` : "",
            item?.urls?.gif ? `gif: ${item.urls.gif}` : ""
          ].filter(Boolean).join("\n")
        }
        return "Animate → " + JSON.stringify(r)
      }
    },
  ]), [])

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
        const names: string[] = []
        const pushIf = (name: string) => { if (lower.includes(name)) names.push(name) }
        pushIf("idle"); pushIf("attack"); pushIf("spell"); pushIf("walk"); pushIf("run");
        const poses = (names.length ? names : ["idle","attack","spell"]).map(n => ({ name: n }))

        // use the whole text as the edit instruction (natural prompt)
        const instruction = text
        const payload = { image_path, instruction, poses, fps: 8, sheet_cols: 3, basename: undefined as any }

        const r = await postPoses(payload)
        const u = (r as any)?.edit_info?.used_model
        const reason = (r as any)?.edit_info?.reason
        const edited = (r as any)?.edit_info?.edited_path
        const lines = [
          `Edit → Poses → Animate complete. (edit=${u || "?"}${reason ? `, reason=${reason}` : ""})`,
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
    <div className="fixed bottom-4 right-4 w-[380px] max-w-[95vw]">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 shadow-lg">
        <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
          <div className="text-sm font-medium">Agent</div>
          <button className="text-xs text-zinc-400 underline" onClick={() => setOpen(!open)}>
            {open ? "Collapse" : "Expand"}
          </button>
        </div>

        {open && (
          <div className="p-3 space-y-3">
            {/* Quick tools row (moved into chat) */}
            <div className="grid grid-cols-2 gap-2">
              {actions.map(a => (
                <button
                  key={a.key}
                  onClick={() => runAction(a.run, a.label)}
                  className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-left text-xs hover:bg-zinc-700"
                >
                  {a.label}
                </button>
              ))}
            </div>

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
  )
}
