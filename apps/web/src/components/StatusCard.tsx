type Props = {
  jobs: any[]
  roots: any
  loading: boolean
  onOpenDrawer?: () => void
}
export function StatusCard({ jobs, roots, loading, onOpenDrawer }: Props) {
  return (
    <div className="rounded-2xl border border-zinc-800 p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-base font-medium">Status</h2>
        <button onClick={onOpenDrawer} className="text-sm underline hover:no-underline">Details</button>
      </div>
      <div className="grid gap-2 text-sm text-zinc-300">
        <div>Loading: {String(loading)}</div>
        <div>Jobs: {Array.isArray(jobs) ? jobs.length : 0}</div>
        <div>Roots: {roots ? 'ok' : '—'}</div>
      </div>
    </div>
  )
}
