import { formatDistanceToNow } from 'date-fns'
import type { Pod, Trade } from '@/data/types'
import { PodGlyph, SideBadge } from './ui'
import { formatCurrency } from '@/lib/formatters'
import { cn } from '@/lib/cn'

function tintFor(pods: Pod[], trade: Trade) {
  return pods.find((p) => p.id === trade.podId)?.tint ?? 'p3'
}

// Alpha-Arena style trade card for the live sidebar.
export function TradeCard({ trade, pods }: { trade: Trade; pods: Pod[] }) {
  const tint = tintFor(pods, trade)
  const ago = (() => {
    try {
      return formatDistanceToNow(new Date(trade.executedAt), { addSuffix: true })
    } catch {
      return ''
    }
  })()
  return (
    <div className="card-soft px-3 py-2.5">
      <div className="flex items-start gap-2">
        <PodGlyph tint={tint} label={trade.podName} size={22} />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate text-xs">
              <span className="font-semibold">{trade.trader}</span>{' '}
              <span className="text-faint">· {trade.podCode}</span>
            </span>
            <span className="shrink-0 text-2xs text-faint">{ago}</span>
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs">
            <SideBadge side={trade.side} />
            <span className="text-faint">{trade.type}</span>
            <span className="font-semibold">${trade.symbol}</span>
            {trade.instrumentType === 'option' && <span className="chip py-0">OPT</span>}
          </div>
        </div>
      </div>

      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-2xs">
        <Row k="Price" v={formatCurrency(trade.price)} />
        <Row k="Quantity" v={trade.quantity.toLocaleString()} />
        <Row k="Notional" v={formatCurrency(trade.notional)} />
        <Row k="Status" v={trade.status} />
      </dl>

      {trade.realizedPnl != null && (
        <div className="mt-2 flex items-center justify-between border-t border-line pt-1.5">
          <span className="label">Net P&L</span>
          <span className={cn('num text-xs font-semibold', trade.realizedPnl >= 0 ? 'pos' : 'neg')}>
            {trade.realizedPnl >= 0 ? '+' : ''}
            {formatCurrency(trade.realizedPnl)}
          </span>
        </div>
      )}
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-faint uppercase tracking-[0.08em]">{k}</dt>
      <dd className="num">{v}</dd>
    </div>
  )
}

export function TradesFeed({ trades, pods }: { trades: Trade[]; pods: Pod[] }) {
  if (!trades.length) {
    return <p className="px-3 py-6 text-center text-2xs uppercase tracking-[0.12em] text-faint">No trades yet</p>
  }
  return (
    <div className="flex flex-col gap-2">
      {trades.map((t) => (
        <TradeCard key={t.id} trade={t} pods={pods} />
      ))}
    </div>
  )
}

// Compact tabular trade log (pod detail / leaderboard "recent trades").
export function TradesTable({ trades }: { trades: Trade[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="dtable">
        <thead>
          <tr>
            <th>Time</th>
            <th>Side</th>
            <th>Symbol</th>
            <th>Trader</th>
            <th className="text-right">Qty</th>
            <th className="text-right">Price</th>
            <th className="text-right">Notional</th>
            <th className="text-right">Net P&L</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id}>
              <td className="text-faint">
                {new Date(t.executedAt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })}
              </td>
              <td><SideBadge side={t.side} /></td>
              <td className="font-semibold">${t.symbol}</td>
              <td className="text-faint">{t.trader}</td>
              <td className="text-right">{t.quantity.toLocaleString()}</td>
              <td className="text-right">{formatCurrency(t.price)}</td>
              <td className="text-right">{formatCurrency(t.notional)}</td>
              <td className={cn('text-right num', t.realizedPnl == null ? 'text-faint' : t.realizedPnl >= 0 ? 'pos' : 'neg')}>
                {t.realizedPnl == null ? '—' : `${t.realizedPnl >= 0 ? '+' : ''}${formatCurrency(t.realizedPnl)}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
