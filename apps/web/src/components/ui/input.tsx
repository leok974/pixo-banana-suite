import { InputHTMLAttributes } from "react"
export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={"rounded-lg px-3 py-2 bg-zinc-800 border border-zinc-700 outline-none "+(props.className||"")} />
}
