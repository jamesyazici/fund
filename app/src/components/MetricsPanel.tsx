import { MetricTile } from './MetricTile'
import { useMetrics } from '@/hooks/useMetrics'
import { METRIC_META } from '@/lib/metrics'

interface MetricsPanelProps {
  podId: string
}

const METRIC_KEYS = Object.keys(METRIC_META).filter((k) => k !== 'trade_count')

export function MetricsPanel({ podId }: MetricsPanelProps) {
  const { data: metrics, isLoading, error } = useMetrics(podId)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 animate-pulse">
        {METRIC_KEYS.map((k) => (
          <div key={k} className="h-24 rounded-xl bg-zinc-100 dark:bg-white/5" />
        ))}
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <p className="text-sm text-zinc-500">
        No metrics yet — accumulating trading history.
      </p>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {METRIC_KEYS.map((key) => (
        <MetricTile
          key={key}
          metricKey={key}
          value={metrics[key as keyof typeof metrics] as number | null}
        />
      ))}
    </div>
  )
}
