import { Link } from 'react-router-dom'
import { usePods } from '@/hooks/usePods'
import { useLiveSnapshots } from '@/hooks/useLiveSnapshots'
import { ConsoleTradeFeed } from '@/components/ConsoleTradeFeed'
import { PortfolioNotionalChart } from '@/components/PortfolioNotionalChart'
import { ConsoleShell } from '@/components/ConsoleShell'
import { formatCurrency } from '@/lib/formatters'
import { cn } from '@/lib/cn'

export function Overview() {
  const { data: pods, isLoading, error } = usePods()
  const { data: livePods } = useLiveSnapshots()
  const featured = pods?.[0]
  const featuredLive = featured ? livePods?.find((pod) => pod.id === featured.id) : undefined

  const totalNav = livePods?.reduce((sum, pod) => sum + pod.nav, 0) ?? pods?.reduce((sum, pod) => sum + pod.allocated_capital, 0) ?? 0
  const totalNotional = livePods?.reduce((sum, pod) => sum + pod.gross_notional, 0) ?? 0
  const totalPnl = livePods?.reduce((sum, pod) => sum + (pod.total_pnl ?? pod.live_gain ?? 0), 0) ?? 0

  if (isLoading) {
    return <div className="min-h-screen border border-black bg-white" />
  }

  if (error || !pods?.length) {
    return (
      <div className="grid min-h-screen place-items-center bg-white font-mono text-sm text-black">
        <div className="border border-black bg-white p-4">No public fund data available.</div>
      </div>
    )
  }

  return (
    <ConsoleShell
      pods={pods}
      livePods={livePods}
      rightSlot={<ConsoleTradeFeed limit={26} positions={livePods?.flatMap((pod) => pod.positions) ?? []} />}
    >
      <div className="grid grid-cols-[1fr_1fr_1fr] border-b border-black bg-white font-mono text-[11px] max-md:grid-cols-1">
        <div className="border-r border-black p-3 max-md:border-b max-md:border-r-0">
          <div className="font-black uppercase text-zinc-500">Total Account Value</div>
          <div className="mt-1 font-black">{formatCurrency(totalNav)}</div>
        </div>
        <div className="border-r border-black p-3 max-md:border-b max-md:border-r-0">
          <div className="font-black uppercase text-zinc-500">Gross Notional</div>
          <div className="mt-1 font-black">{formatCurrency(totalNotional)}</div>
        </div>
        <div className="p-3">
          <div className="font-black uppercase text-zinc-500">Total P&L</div>
          <div className={cn('mt-1 font-black', totalPnl >= 0 ? 'text-emerald-700' : 'text-red-700')}>
            {formatCurrency(totalPnl)}
          </div>
        </div>
      </div>

      {featured ? (
        <PortfolioNotionalChart podId={featured.id} live={featuredLive} />
      ) : (
        <div className="grid h-full place-items-center font-mono text-xs">No featured pod.</div>
      )}

      <div id="funds" className="grid grid-cols-5 border-t border-black bg-white font-mono text-[10px] max-lg:grid-cols-2">
        {pods.slice(0, 5).map((pod) => {
          const live = livePods?.find((item) => item.id === pod.id)
          return (
            <Link key={pod.id} to={`/pod/${pod.id}`} className="border-r border-black p-3 last:border-r-0">
              <div className="truncate font-black uppercase">{pod.name}</div>
              <div className="mt-1">{formatCurrency(live?.nav ?? pod.allocated_capital)}</div>
              <div className={cn('mt-1 font-black', (live?.total_pnl ?? live?.live_gain ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
                {formatCurrency(live?.total_pnl ?? live?.live_gain)}
              </div>
            </Link>
          )
        })}
      </div>
    </ConsoleShell>
  )
}
