import { useState } from 'react'
import { useTrades } from '@/hooks/useTrades'
import { useRealtimeTrades } from '@/hooks/useRealtimeTrades'
import { formatCurrency } from '@/lib/formatters'
import { cn } from '@/lib/cn'
import type { LivePosition } from '@/hooks/useLiveSnapshots'

interface ConsoleTradeFeedProps {
  podId?: string
  limit?: number
  positions?: LivePosition[]
}

function compactTime(value: string) {
  return new Date(value).toLocaleString('en-US', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

type FeedTab = 'trades' | 'notes' | 'positions' | 'readme'

export function ConsoleTradeFeed({ podId, limit = 26, positions = [] }: ConsoleTradeFeedProps) {
  const [tab, setTab] = useState<FeedTab>('trades')
  const { data: trades, isLoading, error } = useTrades({ podId, limit })
  useRealtimeTrades(podId)

  return (
    <aside className="flex min-h-0 flex-col border-l border-black bg-white">
      <div className="grid grid-cols-4 border-b border-black text-[10px] font-black uppercase tracking-[0.08em]">
        {[
          ['trades', 'Completed Trades'],
          ['notes', 'Trader Notes'],
          ['positions', 'Positions'],
          ['readme', 'Readme.txt'],
        ].map(([value, label], index) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value as FeedTab)}
            className={cn(
              'px-2 py-2 text-left',
              index < 3 && 'border-r border-black',
              tab === value ? 'bg-black text-white' : 'bg-white text-black',
            )}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="border-b border-black px-2 py-1 font-mono text-[11px]">
        <span className="font-black">FILTER:</span>{' '}
        <button type="button" onClick={() => setTab('trades')} className="inline-block border border-black bg-white px-1">
          {podId ? 'THIS POD' : 'ALL PODS'} ▾
        </button>
        <span className="float-right">
          {tab === 'trades' ? `Showing last ${trades?.length ?? 0} trades` : tab}
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {tab === 'notes' && (
          <div className="space-y-3 p-3 font-mono text-[11px] leading-5">
            <p className="font-black uppercase">Public notes</p>
            <p>Trades and holdings are read-only records sourced from the fund backend.</p>
            <p>Live notional marks current shares against latest available market prices.</p>
          </div>
        )}
        {tab === 'positions' && (
          <div>
            {!positions.length && <div className="p-3 font-mono text-xs">No open marked positions.</div>}
            {positions.map((position) => (
              <article key={position.symbol} className="border-b border-black/20 px-3 py-2 font-mono text-[11px] leading-5">
                <div className="flex justify-between gap-3">
                  <span className="font-black">{position.symbol}</span>
                  <span>{formatCurrency(position.market_value)}</span>
                </div>
                <p>Quantity: {Number(position.quantity).toLocaleString()}</p>
                <p>Avg entry: {formatCurrency(position.avg_entry_price)}</p>
                <p>Current: {formatCurrency(position.current_price)}</p>
                <p className={cn('font-black', (position.unrealized_pnl ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
                  Unrealized P&L: {formatCurrency(position.unrealized_pnl)}
                </p>
              </article>
            ))}
          </div>
        )}
        {tab === 'readme' && (
          <div className="space-y-3 p-3 font-mono text-[11px] leading-5">
            <p className="font-black uppercase">RQFC transparency</p>
            <p>This page shows student traders, pods, holdings, notional exposure, and completed trade records.</p>
            <p>It is not a leaderboard and does not accept orders.</p>
          </div>
        )}
        {tab === 'trades' && isLoading && <div className="p-3 font-mono text-xs">Loading ledger...</div>}
        {tab === 'trades' && error && <div className="p-3 font-mono text-xs text-red-700">Failed to load trades.</div>}
        {tab === 'trades' && !isLoading && !error && !trades?.length && (
          <div className="p-3 font-mono text-xs">No completed trades yet.</div>
        )}
        {tab === 'trades' && trades?.map((trade) => {
          const isBuy = trade.side === 'buy'
          const qty = Number(trade.filled_qty ?? trade.quantity ?? 0)
          const notional = trade.notional ?? (trade.price != null ? Math.abs(qty * trade.price) : null)
          return (
            <article key={trade.id} className="border-b border-black/20 px-3 py-2 font-mono text-[11px] leading-5">
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0">
                  <span className="font-black text-indigo-700">{trade.traders?.display_name ?? 'Trader'}</span>{' '}
                  completed a{' '}
                  <span className={cn('font-black', isBuy ? 'text-emerald-700' : 'text-red-700')}>
                    {trade.side}
                  </span>{' '}
                  trade on{' '}
                  <span className="font-black">{trade.symbol}</span>
                </p>
                <span className="shrink-0 text-[10px] text-zinc-500">{compactTime(trade.executed_at)}</span>
              </div>
              <p>Price: {formatCurrency(trade.price)} </p>
              <p>Quantity: {qty.toLocaleString()}</p>
              <p>Notional: {formatCurrency(notional)}</p>
              <p>Book: {trade.asset_class.replace('_', ' ')}</p>
              <p>
                NET P&L:{' '}
                <span className={cn('font-black', isBuy ? 'text-emerald-700' : 'text-red-700')}>
                  {trade.status || 'recorded'}
                </span>
              </p>
            </article>
          )
        })}
      </div>
    </aside>
  )
}
