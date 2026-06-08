import { Link } from 'react-router-dom'
import { usePods } from '@/hooks/usePods'
import { useLiveSnapshots } from '@/hooks/useLiveSnapshots'
import { ConsoleShell } from '@/components/ConsoleShell'
import { ConsoleTradeFeed } from '@/components/ConsoleTradeFeed'
import { formatCurrency, formatPct } from '@/lib/formatters'
import { cn } from '@/lib/cn'

export function Leaderboard() {
  const { data: pods, isLoading, error } = usePods()
  const { data: livePods } = useLiveSnapshots()

  if (isLoading) return <div className="min-h-screen border border-black bg-white" />
  if (error || !pods?.length) return <div className="grid min-h-screen place-items-center font-mono">No fund data.</div>

  const rows = pods.map((pod) => {
    const live = livePods?.find((item) => item.id === pod.id)
    return { pod, live, pnl: live?.total_pnl ?? live?.live_gain ?? 0 }
  }).sort((a, b) => b.pnl - a.pnl)

  return (
    <ConsoleShell pods={pods} livePods={livePods} rightSlot={<ConsoleTradeFeed positions={livePods?.flatMap((pod) => pod.positions) ?? []} />}>
      <div className="h-full overflow-auto bg-white font-mono text-[11px]">
        <div className="border-b border-black px-3 py-2 text-center font-black uppercase tracking-[0.12em]">
          Fund Transparency Leaderboard
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-black text-left uppercase text-zinc-500">
              <th className="p-2">Rank</th>
              <th className="p-2">Pod</th>
              <th className="p-2 text-right">NAV</th>
              <th className="p-2 text-right">Notional</th>
              <th className="p-2 text-right">Realized</th>
              <th className="p-2 text-right">Unrealized</th>
              <th className="p-2 text-right">Total P&L</th>
              <th className="p-2 text-right">Return</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ pod, live, pnl }, index) => (
              <tr key={pod.id} className="border-b border-black/20">
                <td className="p-2">#{index + 1}</td>
                <td className="p-2 font-black"><Link to={`/pod/${pod.id}`}>{pod.name}</Link></td>
                <td className="p-2 text-right">{formatCurrency(live?.nav ?? pod.allocated_capital)}</td>
                <td className="p-2 text-right">{formatCurrency(live?.gross_notional)}</td>
                <td className="p-2 text-right">{formatCurrency(live?.realized_pnl)}</td>
                <td className="p-2 text-right">{formatCurrency(live?.unrealized_pnl)}</td>
                <td className={cn('p-2 text-right font-black', pnl >= 0 ? 'text-emerald-700' : 'text-red-700')}>{formatCurrency(pnl)}</td>
                <td className="p-2 text-right">{formatPct(live?.total_return)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ConsoleShell>
  )
}
