type Action = { key: string; label: string; onClick: () => void }
export function ActionCards({ items }: { items: Action[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((a) => (
        <button
          key={a.key}
          onClick={a.onClick}
          className="rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-left hover:bg-zinc-800 transition"
        >
          {a.label}
        </button>
      ))}
    </div>
  )
}
