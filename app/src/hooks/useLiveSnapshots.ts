import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { backendUrl } from '@/lib/backend'

const LivePositionSchema = z.object({
  symbol: z.string(),
  instrument_type: z.string().optional(),
  underlying_symbol: z.string().nullable().optional(),
  quantity: z.number(),
  avg_entry_price: z.number(),
  current_price: z.number().nullable(),
  multiplier: z.number().optional(),
  market_value: z.number().nullable(),
  cost_basis: z.number().nullable().optional(),
  realized_pnl: z.number().nullable().optional(),
  unrealized_pnl: z.number().nullable(),
  total_pnl: z.number().nullable().optional(),
  source: z.string().optional(),
})

const LiveAccountSchema = z.object({
  equity: z.number(),
  cash: z.number(),
  buying_power: z.number(),
  portfolio_value: z.number(),
  last_equity: z.number().nullable().optional(),
  session_return: z.number().nullable().optional(),
  status: z.string(),
})

const IntradayNavRowSchema = z.object({
  timestamp: z.string(),
  nav: z.number(),
  minute_return: z.number().nullable(),
})

const NotionalHistoryRowSchema = z.object({
  timestamp: z.string(),
  gross_notional: z.number(),
  net_notional: z.number(),
})

export const LivePodSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  asset_class: z.string(),
  description: z.string().nullable().optional(),
  benchmark_symbol: z.string().nullable().optional(),
  inception_date: z.string().nullable().optional(),
  allocated_capital: z.number(),
  live: z.boolean(),
  source: z.string(),
  account: LiveAccountSchema.nullable(),
  positions: z.array(LivePositionSchema),
  nav: z.number(),
  cash: z.number().nullable(),
  gross_notional: z.number(),
  net_notional: z.number(),
  realized_pnl: z.number().optional(),
  unrealized_pnl: z.number(),
  total_pnl: z.number().optional(),
  fees: z.number().optional(),
  live_gain: z.number(),
  daily_return: z.number().nullable(),
  session_return: z.number().nullable(),
  total_return: z.number().nullable(),
  error: z.string().nullable(),
})

const LiveSnapshotsResponseSchema = z.object({
  pods: z.array(LivePodSnapshotSchema),
})

export type LivePodSnapshot = z.infer<typeof LivePodSnapshotSchema>
export type LivePosition = z.infer<typeof LivePositionSchema>
export type IntradayNavRow = z.infer<typeof IntradayNavRowSchema>
export type NotionalHistoryRow = z.infer<typeof NotionalHistoryRowSchema>

export function useLiveSnapshots() {
  return useQuery({
    queryKey: ['public-live-snapshots'],
    queryFn: async () => {
      const response = await fetch(backendUrl('/public/live'))
      if (!response.ok) throw new Error(`Live feed failed: ${response.status}`)
      return LiveSnapshotsResponseSchema.parse(await response.json()).pods
    },
    refetchInterval: 5_000,
    staleTime: 2_000,
  })
}

export function useLivePodSnapshot(podId: string) {
  return useQuery({
    queryKey: ['public-live-pod', podId],
    queryFn: async () => {
      const response = await fetch(backendUrl(`/public/pods/${podId}/live`))
      if (!response.ok) throw new Error(`Live pod feed failed: ${response.status}`)
      return LivePodSnapshotSchema.parse(await response.json())
    },
    enabled: !!podId,
    refetchInterval: 5_000,
    staleTime: 2_000,
  })
}

export function useIntradayNav(podId: string, minutes = 390) {
  return useQuery({
    queryKey: ['public-intraday-nav', podId, minutes],
    queryFn: async () => {
      const response = await fetch(backendUrl(`/public/pods/${podId}/intraday-nav?minutes=${minutes}`))
      if (!response.ok) throw new Error(`Intraday NAV failed: ${response.status}`)
      const data = z.object({
        pod_id: z.string(),
        timeframe: z.literal('1Min'),
        rows: z.array(IntradayNavRowSchema),
      }).parse(await response.json())
      return data.rows
    },
    enabled: !!podId,
    refetchInterval: 60_000,
    staleTime: 55_000,
  })
}

export function useNotionalHistory(podId: string, minutes = 390) {
  return useQuery({
    queryKey: ['public-notional-history', podId, minutes],
    queryFn: async () => {
      const response = await fetch(backendUrl(`/public/pods/${podId}/notional-history?minutes=${minutes}`))
      if (!response.ok) throw new Error(`Notional history failed: ${response.status}`)
      const data = z.object({
        pod_id: z.string(),
        timeframe: z.literal('1Min'),
        rows: z.array(NotionalHistoryRowSchema),
      }).parse(await response.json())
      return data.rows
    },
    enabled: !!podId,
    refetchInterval: 60_000,
    staleTime: 55_000,
  })
}
