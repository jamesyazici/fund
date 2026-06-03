import { z } from 'zod'

// ─── Zod schemas ──────────────────────────────────────────────────────────────

export const PodSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  asset_class: z.string(),
  description: z.string().nullable(),
  benchmark_symbol: z.string(),
  inception_date: z.string(),
  starting_capital: z.number(),
  created_at: z.string(),
})

export const MemberSchema = z.object({
  id: z.string().uuid(),
  pod_id: z.string().uuid(),
  name: z.string(),
  role: z.enum(['pm', 'trader']),
  avatar_url: z.string().nullable(),
  joined_at: z.string(),
})

export const TradeSchema = z.object({
  id: z.string().uuid(),
  pod_id: z.string().uuid(),
  member_id: z.string().uuid().nullable(),
  symbol: z.string(),
  side: z.enum(['buy', 'sell']),
  quantity: z.number(),
  price: z.number(),
  notional: z.number(),
  asset_class: z.string(),
  alpaca_order_id: z.string().nullable(),
  executed_at: z.string(),
  created_at: z.string(),
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

export type Database = {
  public: {
    Tables: {
      pods: { Row: Pod; Insert: Omit<Pod, 'id' | 'created_at'>; Update: Partial<Pod> }
      members: { Row: Member; Insert: Omit<Member, 'id'>; Update: Partial<Member> }
      trades: { Row: Trade; Insert: Omit<Trade, 'id' | 'created_at'>; Update: Partial<Trade> }
      positions: { Row: Position; Insert: Omit<Position, 'id'>; Update: Partial<Position> }
      nav_history: { Row: NavHistory; Insert: NavHistory; Update: Partial<NavHistory> }
      metrics: { Row: Metrics; Insert: Metrics; Update: Partial<Metrics> }
    }
    Views: Record<string, never>
    Functions: Record<string, never>
    Enums: Record<string, never>
  }
}
