import { usePositions } from '@/hooks/usePositions'
import { useRealtimePositions } from '@/hooks/useRealtimeTrades'
import { formatCurrency, formatPct } from '@/lib/formatters'
import { cn } from '@/lib/cn'

interface PositionsTableProps {
  podId: string
}

export function PositionsTable({ podId }: PositionsTableProps) {
  const { data: positions, isLoading, error } = usePositions(podId)
  useRealtimePositions(podId)

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-zinc-100 dark:bg-white/5" />
        ))}
      </div>
    )
  }

  if (error || !positions?.length) {
    return (
      <p className="text-sm text-zinc-500 py-4">
        {error ? 'Failed to load positions.' : 'No open positions.'}
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-white/10">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 dark:border-white/10 dark:bg-white/5">
            <th className="py-2 px-3 text-left text-xs text-zinc-500 font-medium">Symbol</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Qty</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Avg Entry</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Current</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Mkt Value</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Unreal P&L</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Return</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const pnl = pos.unrealized_pnl ?? 0
            const pnlPct =
              pos.avg_entry_price && pos.quantity
                ? pnl / (pos.avg_entry_price * Math.abs(pos.quantity))
                : null
            const isPos = pnl >= 0
            return (
              <tr
                key={pos.id}
                className="border-b border-zinc-100 hover:bg-zinc-50 dark:border-white/5 dark:hover:bg-white/5 transition-colors"
              >
                <td className="py-2.5 px-3 font-mono font-semibold text-zinc-900 dark:text-white">
                  {pos.symbol}
                </td>
                <td className="py-2.5 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
                  {Number(pos.quantity).toLocaleString()}
                </td>
                <td className="py-2.5 px-3 text-right text-zinc-500 dark:text-zinc-400 tabular-nums">
                  {formatCurrency(pos.avg_entry_price)}
                </td>
                <td className="py-2.5 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
                  {formatCurrency(pos.current_price)}
                </td>
                <td className="py-2.5 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
                  {formatCurrency(pos.market_value)}
                </td>
                <td
                  className={cn(
                    'py-2.5 px-3 text-right tabular-nums font-medium',
                    isPos
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400',
                  )}
                >
                  {formatCurrency(pnl)}
                </td>
                <td
                  className={cn(
                    'py-2.5 px-3 text-right tabular-nums text-sm',
                    isPos
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400',
                  )}
                >
                  {formatPct(pnlPct)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
