import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { backendUrl } from '@/lib/backend'
import { buildDemo, demoTicker } from './demo'
import type { FundData, Pod, Position, TickerItem, Trade } from './types'

// ── live feeds (best-effort; portal falls back to demo data) ──────────
interface LiveSnapshot {
  id: string
  name: string
  accountValue?: number
  account?: { portfolio_value?: number; cash?: number } | null
  nav?: number
  cash?: number | null
  realized_pnl?: number
  unrealized_pnl?: number
  total_pnl?: number
  fees?: number
  allocated_capital?: number
  total_return?: number | null
  session_return?: number | null
  live?: boolean
  positions?: Array<{
    symbol: string
    quantity: number
    avg_entry_price: number
    current_price: number | null
    market_value: number | null
    unrealized_pnl: number | null
    realized_pnl?: number | null
    total_pnl?: number | null
    instrument_type?: string
  }>
}

async function fetchLive(): Promise<LiveSnapshot[] | null> {
  try {
    const res = await fetch(backendUrl('/public/live'))
    if (!res.ok) return null
    const data = await res.json()
    const pods = data?.pods
    if (!Array.isArray(pods) || pods.length === 0) return null
    if (!pods.some((p: LiveSnapshot) => p.live)) return null
    return pods
  } catch {
    return null
  }
}

interface LiveTrade {
  id: string
  pod_id: string
  pod_name: string | null
  trader: string | null
  trader_id: string | null
  symbol: string
  side: string
  instrument_type: string
  quantity: number | null
  price: number | null
  notional: number | null
  type: string
  status: string
  realized_pnl: number | null
  executed_at: string
}

async function fetchTrades(): Promise<LiveTrade[] | null> {
  try {
    const res = await fetch(backendUrl('/public/trades?limit=120'))
    if (!res.ok) return null
    const data = await res.json()
    const trades = data?.trades
    if (!Array.isArray(trades) || trades.length === 0) return null
    return trades
  } catch {
    return null
  }
}

async function fetchTicker(): Promise<TickerItem[] | null> {
  try {
    const res = await fetch(backendUrl('/public/ticker'))
    if (!res.ok) return null
    const data = await res.json()
    const items = data?.items
    if (!Array.isArray(items) || items.length === 0) return null
    return items.map((i: { symbol: string; price: number; change_pct: number }) => ({
      symbol: i.symbol,
      price: i.price,
      changePct: i.change_pct,
    }))
  } catch {
    return null
  }
}

function mergeLive(base: FundData, live: LiveSnapshot[]): FundData {
  const byName = new Map(live.map((l) => [l.name.toLowerCase(), l]))
  const pods: Pod[] = base.pods.map((pod, i) => {
    const snap = byName.get(pod.name.toLowerCase()) ?? live[i]
    if (!snap || !snap.live) return pod
    const accountValue = snap.account?.portfolio_value ?? snap.nav ?? pod.accountValue
    const allocated = snap.allocated_capital ?? pod.allocatedCapital
    const positions: Position[] = (snap.positions ?? []).map((p, idx) => {
      const mv = p.market_value ?? 0
      return {
        id: `${pod.id}-live-${idx}`,
        podId: pod.id,
        symbol: p.symbol,
        side: p.quantity >= 0 ? 'long' : 'short',
        instrumentType: (p.instrument_type as 'equity' | 'option') ?? 'equity',
        quantity: Math.abs(p.quantity),
        avgEntry: p.avg_entry_price,
        currentPrice: p.current_price ?? p.avg_entry_price,
        marketValue: mv,
        costBasis: p.avg_entry_price * p.quantity,
        unrealizedPnl: p.unrealized_pnl ?? 0,
        realizedPnl: p.realized_pnl ?? 0,
        totalPnl: p.total_pnl ?? p.unrealized_pnl ?? 0,
        trader: pod.traders[idx % pod.traders.length]?.name ?? pod.name,
        openedAt: pod.positions[idx]?.openedAt ?? new Date().toISOString(),
      }
    })
    const usePositions = positions.length ? positions : pod.positions
    const totalPnl = snap.total_pnl ?? accountValue - allocated
    const lastNav = pod.nav[pod.nav.length - 1]
    const nav = [...pod.nav.slice(0, -1), { t: lastNav.t, value: accountValue }]
    return {
      ...pod,
      accountValue,
      allocatedCapital: allocated,
      cash: snap.cash ?? snap.account?.cash ?? pod.cash,
      realizedPnl: snap.realized_pnl ?? pod.realizedPnl,
      unrealizedPnl: snap.unrealized_pnl ?? pod.unrealizedPnl,
      totalPnl,
      fees: snap.fees ?? pod.fees,
      totalReturn: snap.total_return ?? totalPnl / (allocated || 1),
      dayReturn: snap.session_return ?? pod.dayReturn,
      liveGain: accountValue - allocated,
      positions: usePositions,
      nav,
    }
  })
  const positions = pods.flatMap((p) => p.positions)
  return { ...base, pods, positions, isLive: true, asOf: new Date().toISOString() }
}

// Map live order-log trades onto the merged pods (matched by pod name).
function mergeTrades(fund: FundData, live: LiveTrade[]): Trade[] {
  const byName = new Map(fund.pods.map((p) => [p.name.toLowerCase(), p]))
  const mapped: Trade[] = live.map((t) => {
    const pod = (t.pod_name && byName.get(t.pod_name.toLowerCase())) || fund.pods[0]
    const qty = t.quantity ?? 0
    const price = t.price ?? 0
    return {
      id: t.id,
      podId: pod?.id ?? t.pod_id,
      podCode: pod?.code ?? 0,
      podName: pod?.name ?? t.pod_name ?? '',
      trader: t.trader ?? pod?.traders[0]?.name ?? 'Trader',
      traderId: t.trader_id ?? '',
      symbol: t.symbol,
      side: t.side === 'sell' ? 'sell' : 'buy',
      instrumentType: t.instrument_type === 'option' ? 'option' : 'equity',
      quantity: Math.abs(qty),
      price,
      notional: t.notional ?? Math.abs(qty * price),
      type: (t.type || 'MARKET').toUpperCase(),
      status: t.status ?? 'filled',
      realizedPnl: t.realized_pnl ?? null,
      executedAt: t.executed_at,
    }
  })
  return mapped.sort((a, b) => +new Date(b.executedAt) - +new Date(a.executedAt))
}

export function useFund(): FundData {
  const base = useMemo(() => buildDemo(), [])

  const { data: live } = useQuery({
    queryKey: ['fund-live'],
    queryFn: fetchLive,
    refetchInterval: 5_000,
    staleTime: 2_000,
  })

  const { data: liveTrades } = useQuery({
    queryKey: ['fund-trades'],
    queryFn: fetchTrades,
    refetchInterval: 8_000,
    staleTime: 4_000,
  })

  const { data: ticker } = useQuery({
    queryKey: ['fund-ticker'],
    queryFn: fetchTicker,
    refetchInterval: 15_000,
    staleTime: 10_000,
  })

  return useMemo(() => {
    const merged = live ? mergeLive(base, live) : base
    const withTrades = liveTrades ? { ...merged, trades: mergeTrades(merged, liveTrades) } : merged
    return { ...withTrades, ticker: ticker ?? withTrades.ticker ?? demoTicker() }
  }, [base, live, liveTrades, ticker])
}

export function usePod(podId: string | undefined): Pod | undefined {
  const fund = useFund()
  return useMemo(() => fund.pods.find((p) => p.id === podId || String(p.code) === podId), [fund.pods, podId])
}
