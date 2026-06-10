// Domain model consumed by the UI. The data layer maps either live backend +
// Supabase data or the demo fallback onto these shapes so pages never branch.

export type Tint = 'p1' | 'p2' | 'p3' | 'p4' | 'p5' | 'p6'

export interface Trader {
  id: string
  name: string
  handle: string
  podId: string
  podCode: number
  role: 'pm' | 'trader'
  tint: Tint
  // attributed metrics (live)
  livePnl: number
  realizedPnl: number
  unrealizedPnl: number
  biggestWin: number
  biggestLoss: number
  maxDrawdown: number
  winRate: number
  trades: number
}

export interface Position {
  id: string
  podId: string
  symbol: string
  side: 'long' | 'short'
  instrumentType: 'equity' | 'option'
  quantity: number
  avgEntry: number
  currentPrice: number
  marketValue: number
  costBasis: number
  unrealizedPnl: number
  realizedPnl: number
  totalPnl: number
  trader: string
  openedAt: string
}

export interface Trade {
  id: string
  podId: string
  podCode: number
  podName: string
  trader: string
  traderId: string
  symbol: string
  side: 'buy' | 'sell'
  instrumentType: 'equity' | 'option'
  quantity: number | null
  price: number | null
  notional: number | null // market value of the trade when it took place
  type: string // order label (MARKET / LIMIT / ...)
  status: string
  realizedPnl: number | null
  executedAt: string
}

export interface NavPoint {
  t: string // ISO timestamp
  value: number
}

export interface Pod {
  id: string
  code: number
  name: string
  strategy: string
  assetClass: string
  description: string
  tint: Tint
  inceptionDate: string
  allocatedCapital: number

  // live portfolio accounting
  accountValue: number
  cash: number
  realizedPnl: number
  unrealizedPnl: number
  totalPnl: number
  fees: number
  totalReturn: number // fraction
  dayReturn: number // fraction
  liveGain: number

  // risk / performance metrics
  sharpe: number
  maxDrawdown: number // fraction (negative)
  winRate: number // fraction
  biggestWin: number
  biggestLoss: number
  avgLeverage: number
  longExposure: number
  shortExposure: number

  traders: Trader[]
  positions: Position[]
  nav: NavPoint[]
}

export interface TickerItem {
  symbol: string
  price: number
  changePct: number
}

export interface FundData {
  pods: Pod[]
  traders: Trader[]
  trades: Trade[]
  positions: Position[]
  ticker: TickerItem[]
  isLive: boolean
  asOf: string
}
