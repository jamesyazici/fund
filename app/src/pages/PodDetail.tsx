import { Link, useParams } from 'react-router-dom'
import { usePod } from '@/hooks/usePods'
import { useMembers } from '@/hooks/useMembers'
import { useLivePodSnapshot } from '@/hooks/useLiveSnapshots'
import { PortfolioNotionalChart } from '@/components/PortfolioNotionalChart'
import { ConsoleTradeFeed } from '@/components/ConsoleTradeFeed'
import { formatCurrency, formatPct } from '@/lib/formatters'
import { cn } from '@/lib/cn'

const assetIcons: Record<string, string> = {
  equities: '▦',
  options: '◇',
  fixed_income: '◌',
  crypto: '◈',
  fx: '✕',
  futures: '◆',
}

function initials(value: string) {
  return value
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function PodDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: pod, isLoading, error } = usePod(id ?? '')
  const { data: live } = useLivePodSnapshot(id ?? '')
  const { data: members } = useMembers(id ?? '')

  if (isLoading) {
    return <div className="min-h-screen border border-black bg-[#f6f6f3]" />
  }

  if (error || !pod) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#f6f6f3] font-mono text-sm text-black">
        <div className="border border-black bg-white p-4">
          Pod not found. <Link to="/" className="underline">Back to live view</Link>
        </div>
      </div>
    )
  }

  const leadTrader = members?.find((member) => member.role === 'pm') ?? members?.[0]
  const traderName = leadTrader?.name ?? 'Student Trader'
  const positions = live?.positions ?? []
  const gross = live?.gross_notional ?? 0
  const nav = live?.nav ?? pod.allocated_capital
  const totalReturn = live?.total_return ?? null
  const liveGain = live?.live_gain ?? nav - pod.allocated_capital
  const isPositive = liveGain >= 0

  return (
    <div className="min-h-screen overflow-hidden border border-black bg-[#f6f6f3] text-black">
      <div className="grid h-10 grid-cols-[220px_minmax(0,1fr)_360px] items-center border-b border-black bg-[#f7f7f4] font-mono text-[11px] uppercase tracking-[0.12em] max-lg:grid-cols-[180px_minmax(0,1fr)]">
        <Link to="/" className="px-5 font-serif text-2xl font-black normal-case tracking-[-0.08em]">
          RQFC<span className="ml-1 font-mono text-[10px] tracking-normal">by students</span>
        </Link>
        <div className="flex justify-center gap-8 font-black">
          <span>Live</span>
          <span>|</span>
          <span>Portfolio</span>
          <span>|</span>
          <span>Trades</span>
        </div>
        <div className="flex justify-end gap-4 px-5 text-[10px] max-lg:hidden">
          <span>{live?.live ? 'live alpaca marks' : 'snapshot fallback'}</span>
          <span>read only ↗</span>
        </div>
      </div>

      <div className="grid grid-cols-6 border-b border-black bg-[#f7f7f4] font-mono text-[11px] max-md:grid-cols-2">
        {(positions.length ? positions.slice(0, 6) : [{ symbol: pod.benchmark_symbol, current_price: nav, quantity: 1 }]).map((position) => (
          <div key={position.symbol} className="border-r border-black px-4 py-2 last:border-r-0">
            <div className="text-[10px] font-black uppercase text-zinc-600">
              {assetIcons[pod.asset_class] ?? '◌'} {position.symbol}
            </div>
            <div className="mt-1 font-black">{formatCurrency(position.current_price)}</div>
          </div>
        ))}
      </div>

      <div className="grid h-[calc(100vh-7.25rem)] min-h-[680px] grid-cols-[minmax(0,1fr)_400px] max-xl:grid-cols-1 max-xl:h-auto">
        <main className="min-h-0">
          <div className="grid grid-cols-[280px_minmax(0,1fr)_280px] border-b border-black bg-[#f7f7f4] font-mono text-[11px] max-lg:grid-cols-1">
            <div className="border-r border-black p-4 max-lg:border-b max-lg:border-r-0">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-full border border-black bg-white font-black">
                  {initials(traderName)}
                </div>
                <div>
                  <div className="font-black uppercase">{traderName}</div>
                  <div className="text-zinc-600">Trader</div>
                </div>
              </div>
            </div>
            <div className="p-4 text-center max-lg:border-b max-lg:border-black">
              <div className="font-black uppercase tracking-[0.2em]">{pod.name}</div>
              <div className="mt-1 text-zinc-600">{pod.asset_class.replace('_', ' ')} / {pod.benchmark_symbol}</div>
            </div>
            <div className="grid grid-cols-2 font-mono">
              <div className="border-l border-black p-4 max-lg:border-l-0">
                <div className="text-[10px] font-black uppercase text-zinc-500">Notional</div>
                <div className="mt-1 font-black">{formatCurrency(gross)}</div>
              </div>
              <div className="border-l border-black p-4">
                <div className="text-[10px] font-black uppercase text-zinc-500">Gain</div>
                <div className={cn('mt-1 font-black', isPositive ? 'text-emerald-700' : 'text-red-700')}>
                  {formatCurrency(liveGain)}
                </div>
              </div>
            </div>
          </div>

          <PortfolioNotionalChart podId={pod.id} live={live} />

          <div className="grid grid-cols-5 border-t border-black bg-[#f7f7f4] font-mono text-[10px] max-lg:grid-cols-2">
            <div className="border-r border-black p-3">
              <div className="font-black uppercase text-zinc-500">NAV</div>
              <div className="mt-1 font-black">{formatCurrency(nav)}</div>
            </div>
            <div className="border-r border-black p-3">
              <div className="font-black uppercase text-zinc-500">Return</div>
              <div className={cn('mt-1 font-black', (totalReturn ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
                {formatPct(totalReturn)}
              </div>
            </div>
            <div className="border-r border-black p-3">
              <div className="font-black uppercase text-zinc-500">Cash</div>
              <div className="mt-1 font-black">{formatCurrency(live?.cash)}</div>
            </div>
            <div className="border-r border-black p-3">
              <div className="font-black uppercase text-zinc-500">Allocated</div>
              <div className="mt-1 font-black">{formatCurrency(pod.allocated_capital)}</div>
            </div>
            <div className="p-3">
              <div className="font-black uppercase text-zinc-500">Positions</div>
              <div className="mt-1 font-black">{positions.length}</div>
            </div>
          </div>

          <div className="grid grid-cols-5 border-t border-black bg-[#f7f7f4] font-mono text-[10px] max-lg:grid-cols-2">
            {(positions.length ? positions.slice(0, 5) : [{ symbol: 'NO POSITIONS', market_value: 0, unrealized_pnl: 0 }]).map((position) => (
              <div key={position.symbol} className="border-r border-black p-3 last:border-r-0">
                <div className="font-black uppercase">{position.symbol}</div>
                <div className="mt-1">{formatCurrency(position.market_value)}</div>
                <div className={cn('mt-1 font-black', (position.unrealized_pnl ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
                  {formatCurrency(position.unrealized_pnl)}
                </div>
              </div>
            ))}
          </div>
        </main>

        <ConsoleTradeFeed podId={pod.id} limit={26} />
      </div>
    </div>
  )
}
