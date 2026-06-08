import { z } from 'zod'

// ─── Zod schemas ──────────────────────────────────────────────────────────────

export const PodSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  asset_class: z.string(),
  description: z.string().nullable(),
  benchmark_symbol: z.string(),
  inception_date: z.string(),
  allocated_capital: z.number(),
  created_at: z.string(),
})

// `members` is a view over pod_memberships + traders, presenting a pod roster.
export const MemberSchema = z.object({
  id: z.string().uuid(),
  pod_id: z.string().uuid(),
  name: z.string(),
  role: z.enum(['pm', 'trader']),
  avatar_url: z.string().nullable(),
  joined_at: z.string(),
  is_admin: z.boolean(),
})

export const TradeSchema = z.object({
  id: z.string().uuid(),
  pod_id: z.string().uuid(),
  trader_id: z.string().uuid().nullable(),
  symbol: z.string(),
  side: z.enum(['buy', 'sell']),
  order_type: z.string().nullable(),
  quantity: z.number().nullable(),
  price: z.number().nullable(),
  notional: z.number().nullable(),
  limit_price: z.number().nullable(),
  filled_qty: z.number().nullable(),
  status: z.string().nullable(),
  asset_class: z.string(),
  alpaca_order_id: z.string().nullable(),
  executed_at: z.string(),
  created_at: z.string(),
  traders: z.object({ display_name: z.string().nullable() }).nullable().optional(),
  pods: z.object({ name: z.string().nullable() }).nullable().optional(),
})

export const PositionSchema = z.object({
  id: z.string().uuid(),
  pod_id: z.string().uuid(),
  symbol: z.string(),
  quantity: z.number(),
  avg_entry_price: z.number(),
  current_price: z.number().nullable(),
  market_value: z.number().nullable(),
  unrealized_pnl: z.number().nullable(),
  updated_at: z.string(),
})

export const NavHistorySchema = z.object({
  pod_id: z.string().uuid(),
  date: z.string(),
  nav: z.number(),
  cash: z.number(),
  daily_return: z.number().nullable(),
})

export const MetricsSchema = z.object({
  pod_id: z.string().uuid(),
  as_of_date: z.string(),
  cumulative_return: z.number().nullable(),
  annualized_return: z.number().nullable(),
  volatility: z.number().nullable(),
  sharpe: z.number().nullable(),
  sortino: z.number().nullable(),
  beta: z.number().nullable(),
  alpha: z.number().nullable(),
  max_drawdown: z.number().nullable(),
  calmar: z.number().nullable(),
  var_95: z.number().nullable(),
  win_rate: z.number().nullable(),
  trade_count: z.number().nullable(),
})

// ─── Inferred TS types ────────────────────────────────────────────────────────

export type Pod = z.infer<typeof PodSchema>
export type Member = z.infer<typeof MemberSchema>
export type Trade = z.infer<typeof TradeSchema>
export type Position = z.infer<typeof PositionSchema>
export type NavHistory = z.infer<typeof NavHistorySchema>
export type Metrics = z.infer<typeof MetricsSchema>

// ─── Supabase Database generic type (used by createClient<Database>) ──────────

type Trader = {
  id: string
  auth_user_id: string | null
  display_name: string
  is_admin: boolean
  created_at: string
}

type PodMembership = {
  pod_id: string
  trader_id: string
  role: 'pm' | 'trader'
  assigned_at: string
}

type CapitalAllocation = {
  id: string
  pod_id: string
  new_capital: number
  previous_capital: number | null
  allocated_by: string | null
  note: string | null
  created_at: string
}

export type Database = {
  public: {
    Tables: {
      pods: { Row: Pod; Insert: Omit<Pod, 'id' | 'created_at'>; Update: Partial<Pod> }
      traders: { Row: Trader; Insert: Omit<Trader, 'id' | 'created_at'>; Update: Partial<Trader> }
      pod_memberships: { Row: PodMembership; Insert: PodMembership; Update: Partial<PodMembership> }
      trades: { Row: Trade; Insert: Omit<Trade, 'id' | 'created_at'>; Update: Partial<Trade> }
      positions: { Row: Position; Insert: Omit<Position, 'id'>; Update: Partial<Position> }
      nav_history: { Row: NavHistory; Insert: NavHistory; Update: Partial<NavHistory> }
      metrics: { Row: Metrics; Insert: Metrics; Update: Partial<Metrics> }
      capital_allocations: { Row: CapitalAllocation; Insert: Omit<CapitalAllocation, 'id' | 'created_at'>; Update: Partial<CapitalAllocation> }
    }
    Views: {
      // pod_memberships + traders presented as a pod roster.
      members: { Row: Member }
    }
    Functions: Record<string, never>
    Enums: Record<string, never>
  }
}
