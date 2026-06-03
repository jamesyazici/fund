import { cn } from '@/lib/cn'
import { formatNumber, formatPct } from '@/lib/formatters'
import { METRIC_META } from '@/lib/metrics'

interface MetricTileProps {
  metricKey: string
  value: number | null | undefined
  className?: string
}

export function MetricTile({ metricKey, value, className }: MetricTileProps) {
  const meta = METRIC_META[metricKey]
  if (!meta) return null

  const display =
    value == null
      ? 'accumulating history…'
      : meta.format === 'pct'
        ? formatPct(value)
        : formatNumber(value)

  const isNegative = value != null && value < 0
  const isPositive = value != null && value > 0

  return (
    <div
      className={cn(
        'rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-white/5',
        className,
      )}
    >
      <p className="text-xs text-zinc-600 dark:text-zinc-400 truncate">{meta.label}</p>
      <p
        className={cn('mt-1 text-xl font-semibold tabular-nums', {
          'text-emerald-600 dark:text-emerald-400': isPositive && meta.format === 'pct',
          'text-red-600 dark:text-red-400': isNegative && meta.format === 'pct',
          'text-zinc-900 dark:text-white':
            meta.format === 'ratio' || meta.format === 'number',
        })}
      >
        {display}
      </p>
      <p className="mt-1 text-[11px] text-zinc-500 leading-tight line-clamp-2">
        {meta.description}
      </p>
    </div>
  )
}
