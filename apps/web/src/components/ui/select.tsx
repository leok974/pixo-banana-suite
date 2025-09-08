import { SelectHTMLAttributes } from "react"
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={"rounded-lg px-3 py-2 bg-zinc-800 border border-zinc-700 "+(props.className||"")} />
}
