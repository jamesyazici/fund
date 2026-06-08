import { Link } from 'react-router-dom'
import type { LivePodSnapshot } from '@/hooks/useLiveSnapshots'
import type { Pod } from '@/types/db'
import { formatCurrency, formatPct } from '@/lib/formatters'
import { cn } from '@/lib/cn'

interface ConsoleShellProps {
  pods: Pod[]
  livePods?: LivePodSnapshot[]
  children: React.ReactNode
  rightSlot?: React.ReactNode
}

export function ConsoleShell({ pods, livePods, children, rightSlot }: ConsoleShellProps) {
  const totalNav = livePods?.reduce((sum, pod) => sum + pod.nav, 0) ?? pods.reduce((sum, pod) => sum + pod.allocated_capital, 0)
  const high = [...(livePods ?? [])].sort((a, b) => (b.total_return ?? -Infinity) - (a.total_return ?? -Infinity))[0]
  const low = [...(livePods ?? [])].sort((a, b) => (a.total_return ?? Infinity) - (b.total_return ?? Infinity))[0]

  return (
    <div className="min-h-screen overflow-hidden border border-black bg-white text-black">
      <div className="grid h-10 grid-cols-[220px_minmax(0,1fr)_360px] items-center border-b border-black bg-white font-mono text-[11px] uppercase tracking-[0.12em] max-lg:grid-cols-[180px_minmax(0,1fr)]">
        <Link to="/" className="px-5 font-serif text-2xl font-black normal-case tracking-[-0.08em]">
          RQFC<span className="ml-1 font-mono text-[10px] tracking-normal">by students</span>
        </Link>
        <nav className="flex justify-center gap-8 font-black">
          <Link to="/">Live</Link>
          <span>|</span>
          <Link to="/leaderboard">Leaderboard</Link>
          <span>|</span>
          <Link to="/models">Models</Link>
          <span>|</span>
          <Link to="/blog">Blog</Link>
        </nav>
        <div className="flex justify-end gap-4 px-5 text-[10px] max-lg:hidden">
          <a href="mailto:rqfc@example.com">Join the platform waitlist ↗</a>
          <Link to="/about">About RQFC ↗</Link>
        </div>
      </div>

      <div className="grid grid-cols-6 border-b border-black bg-white font-mono text-[11px] max-md:grid-cols-2">
        {pods.slice(0, 6).map((pod) => {
          const live = livePods?.find((item) => item.id === pod.id)
          const firstPosition = live?.positions[0]
          return (
            <Link key={pod.id} to={`/pod/${pod.id}`} className="border-r border-black px-4 py-2 last:border-r-0">
              <div className="truncate text-[10px] font-black uppercase text-zinc-600">
                ◌ {firstPosition?.symbol ?? pod.name}
              </div>
              <div className="mt-1 font-black">
                {formatCurrency(firstPosition?.current_price ?? live?.nav ?? pod.allocated_capital)}
              </div>
            </Link>
          )
        })}
      </div>

      <div className="border-b border-black bg-white px-4 py-2 font-mono text-[11px]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            HIGHEST:{' '}
            <span className="font-black">{high?.name ?? '—'}</span>{' '}
            <span className="font-black">{formatCurrency(high?.nav)}</span>{' '}
            <span className={cn((high?.total_return ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
              {formatPct(high?.total_return)}
            </span>
          </div>
          <div>
            TOTAL ACCOUNT VALUE: <span className="font-black">{formatCurrency(totalNav)}</span>
          </div>
          <div>
            LOWEST:{' '}
            <span className="font-black">{low?.name ?? '—'}</span>{' '}
            <span className="font-black">{formatCurrency(low?.nav)}</span>{' '}
            <span className={cn((low?.total_return ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
              {formatPct(low?.total_return)}
            </span>
          </div>
        </div>
      </div>

      <div className="grid h-[calc(100vh-7.4rem)] min-h-[680px] grid-cols-[minmax(0,1fr)_400px] max-xl:grid-cols-1 max-xl:h-auto">
        <main className="min-h-0">{children}</main>
        {rightSlot}
      </div>
    </div>
  )
}
