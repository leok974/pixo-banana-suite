type Props = { open: boolean; onClose: () => void; onRefresh?: () => void }
export function StatusDrawer({ open, onClose, onRefresh }: Props) {
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/60">
      <div className="absolute right-0 top-0 h-full w-full sm:w-[480px] bg-zinc-950 border-l border-zinc-800 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-medium">Status details</h3>
          <div className="space-x-2">
            <button onClick={onRefresh} className="text-sm underline">Refresh</button>
            <button onClick={onClose} className="text-sm underline">Close</button>
          </div>
        </div>
        <p className="text-sm text-zinc-400">Add richer status later.</p>
      </div>
    </div>
  )
}
