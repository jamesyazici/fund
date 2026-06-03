import { useTrades } from '@/hooks/useTrades'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { cn } from '@/lib/cn'
import type { Trade } from '@/types/db'

interface TradeBlotterProps {
  podId?: string
  limit?: number
}

function TradeRow({ trade }: { trade: Trade }) {
  const isBuy = trade.side === 'buy'
  return (
    <tr className="border-b border-zinc-100 hover:bg-zinc-50 dark:border-white/5 dark:hover:bg-white/5 transition-colors">
      <td className="py-2.5 px-3 text-xs text-zinc-500 dark:text-zinc-400 whitespace-nowrap">
        {formatDateTime(trade.executed_at)}
      </td>
      <td className="py-2.5 px-3 font-mono font-semibold text-zinc-900 dark:text-white">
        {trade.symbol}
      </td>
      <td className="py-2.5 px-3">
        <span
          className={cn(
            'inline-block px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide',
            isBuy
              ? 'bg-emerald-500/15 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400'
              : 'bg-red-500/15 text-red-700 dark:bg-red-500/20 dark:text-red-400',
          )}
        >
          {trade.side}
        </span>
      </td>
      <td className="py-2.5 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
        {Number(trade.quantity).toLocaleString()}
      </td>
      <td className="py-2.5 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
        {formatCurrency(trade.price)}
      </td>
      <td className="py-2.5 px-3 text-right text-zinc-700 dark:text-zinc-200 tabular-nums">
        {formatCurrency(trade.notional)}
      </td>
      <td className="py-2.5 px-3 text-xs text-zinc-500 capitalize">
        {trade.asset_class.replace('_', ' ')}
      </td>
    </tr>
  )
}

export function TradeBlotter({ podId, limit = 50 }: TradeBlotterProps) {
  const { data: trades, isLoading, error } = useTrades({ podId, limit })
  useRealtimeTrades(podId)

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-10 rounded bg-zinc-100 dark:bg-white/5" />
        ))}
      </div>
    )
  }

  if (error || !trades?.length) {
    return (
      <p className="text-sm text-zinc-500 py-4">
        {error ? 'Failed to load trades.' : 'No trades yet.'}
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-white/10">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 dark:border-white/10 dark:bg-white/5">
            <th className="py-2 px-3 text-left text-xs text-zinc-500 font-medium">Time</th>
            <th className="py-2 px-3 text-left text-xs text-zinc-500 font-medium">Symbol</th>
            <th className="py-2 px-3 text-left text-xs text-zinc-500 font-medium">Side</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Qty</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Price</th>
            <th className="py-2 px-3 text-right text-xs text-zinc-500 font-medium">Notional</th>
            <th className="py-2 px-3 text-left text-xs text-zinc-500 font-medium">Class</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <TradeRow key={trade.id} trade={trade} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
