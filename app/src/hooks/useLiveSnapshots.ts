import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { backendUrl } from '@/lib/backend'

const LivePositionSchema = z.object({
  symbol: z.string(),
  quantity: z.number(),
  avg_entry_price: z.number(),
  current_price: z.number().nullable(),
  market_value: z.number().nullable(),
  unrealized_pnl: z.number().nullable(),
})

const LiveAccountSchema = z.object({
  equity: z.number(),
  cash: z.number(),
  buying_power: z.number(),
  portfolio_value: z.number(),
  status: z.string(),
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
  unrealized_pnl: z.number(),
  daily_return: z.number().nullable(),
  total_return: z.number().nullable(),
  error: z.string().nullable(),
})

const LiveSnapshotsResponseSchema = z.object({
  pods: z.array(LivePodSnapshotSchema),
})

export type LivePodSnapshot = z.infer<typeof LivePodSnapshotSchema>
export type LivePosition = z.infer<typeof LivePositionSchema>

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
