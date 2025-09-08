import { PropsWithChildren } from "react"
export function ScrollArea({ children }: PropsWithChildren) {
  return <div className="max-h-80 overflow-auto">{children}</div>
}
