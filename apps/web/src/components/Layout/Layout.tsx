import { PropsWithChildren } from 'react'

export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 sticky top-0 bg-zinc-950/80 backdrop-blur">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold">Pixel Banana Suite</h1>
          <div className="text-xs text-zinc-400">dev</div>
        </div>
      </header>
      <main>{children}</main>
    </div>
  )
}
