type Props = { jobs: any[], loading: boolean }
export function RecentJobs({ jobs, loading }: Props) {
  return (
    <div className="rounded-2xl border border-zinc-800 p-4">
      <h2 className="text-base font-medium mb-2">Recent Jobs</h2>
      {loading ? (
        <div className="text-sm text-zinc-400">Loading…</div>
      ) : (
        <ul className="text-sm text-zinc-300 space-y-1">
          {(jobs ?? []).map((j: any) => (
            <li key={j.job_id} className="flex items-center justify-between">
              <span className="truncate">{j.job_id}</span>
              <span className="text-zinc-500">{j.files?.length ?? 0} file(s)</span>
            </li>
          ))}
          {(!jobs || jobs.length === 0) && <li className="text-zinc-500">No jobs yet.</li>}
        </ul>
      )}
    </div>
  )
}
