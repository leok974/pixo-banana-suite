import { ButtonHTMLAttributes } from "react"
export function Button(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={"rounded-lg px-3 py-2 border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 "+(props.className||"")} />
}
