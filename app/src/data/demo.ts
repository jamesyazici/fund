// Self-consistent demo dataset: 3 pods, 3-4 traders each, live-style positions,
// trades, NAV series and derived risk metrics. Used as the fallback whenever the
// live backend / Supabase have no data, so the portal always renders.
import type { FundData, NavPoint, Pod, Position, Tint, Trade, Trader, TickerItem } from './types'

// ── deterministic RNG ─────────────────────────────────────────────
function mulberry32(seed: number) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const round = (n: number, d = 2) => {
  const f = 10 ** d
  return Math.round(n * f) / f
}

// ── series math ───────────────────────────────────────────────────
function sharpeOf(nav: NavPoint[]): number {
  const rets: number[] = []
  for (let i = 1; i < nav.length; i++) rets.push(nav[i].value / nav[i - 1].value - 1)
  if (rets.length < 2) return 0
  const mean = rets.reduce((a, b) => a + b, 0) / rets.length
  const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length - 1)
  const sd = Math.sqrt(variance)
  if (sd === 0) return 0
  return round(((mean / sd) * Math.sqrt(252)), 3)
}

function maxDrawdownOf(nav: NavPoint[]): number {
  let peak = -Infinity
  let mdd = 0
  for (const p of nav) {
    if (p.value > peak) peak = p.value
    const dd = p.value / peak - 1
    if (dd < mdd) mdd = dd
  }
  return round(mdd, 4)
}

// random-walk NAV that lands exactly on `end`
function makeNav(seed: number, start: number, end: number, days: number): NavPoint[] {
  const rng = mulberry32(seed)
  const raw: number[] = [start]
  for (let i = 1; i < days; i++) {
    const drift = (end / start - 1) / days
    const shock = (rng() - 0.5) * 0.018
    raw.push(raw[i - 1] * (1 + drift + shock))
  }
  // rescale so the final point equals `end`
  const factor = end / raw[raw.length - 1]
  const now = Date.now()
  return raw.map((v, i) => ({
    t: new Date(now - (days - 1 - i) * 24 * 3600 * 1000).toISOString(),
    value: round(v * (1 + (factor - 1) * (i / (days - 1)))),
  }))
}

// ── static specs ──────────────────────────────────────────────────
interface PodSpec {
  code: number
  name: string
  strategy: string
  assetClass: string
  description: string
  tint: Tint
  allocated: number
  end: number
  realized: number
  fees: number
  traders: { name: string; handle: string; role: 'pm' | 'trader'; tint: Tint }[]
  positions: { symbol: string; side: 'long' | 'short'; instr: 'equity' | 'option'; qty: number; entry: number; drift: number }[]
}

const SPECS: PodSpec[] = [
  {
    code: 1,
    name: 'Momentum Alpha',
    strategy: 'Cross-sectional equity momentum',
    assetClass: 'US Equities',
    tint: 'p3',
    allocated: 100_000,
    end: 112_480,
    realized: 4_120,
    fees: 142,
    description:
      'Systematic long/short on 1–12 month price momentum across US large caps, rebalanced into strength and risk-managed on trend breaks.',
    traders: [
      { name: 'Ava Lindqvist', handle: 'ava', role: 'pm', tint: 'p3' },
      { name: 'Marcus Holt', handle: 'mholt', role: 'trader', tint: 'p1' },
      { name: 'Priya Nair', handle: 'pnair', role: 'trader', tint: 'p2' },
    ],
    positions: [
      { symbol: 'NVDA', side: 'long', instr: 'equity', qty: 120, entry: 168.4, drift: 0.142 },
      { symbol: 'MSFT', side: 'long', instr: 'equity', qty: 80, entry: 402.1, drift: 0.061 },
      { symbol: 'META', side: 'long', instr: 'equity', qty: 45, entry: 512.7, drift: 0.088 },
      { symbol: 'INTC', side: 'short', instr: 'equity', qty: 300, entry: 31.2, drift: -0.072 },
    ],
  },
  {
    code: 2,
    name: 'Mean Reversion',
    strategy: 'Short-horizon statistical reversion',
    assetClass: 'Equities · Options',
    tint: 'p1',
    allocated: 100_000,
    end: 96_240,
    realized: -2_870,
    fees: 196,
    description:
      'Fades intraday and multi-day dislocations in liquid names, hedged with index options. Profits from overreaction; bleeds in strong trends.',
    traders: [
      { name: 'Diego Alvarez', handle: 'diego', role: 'pm', tint: 'p1' },
      { name: 'Hana Suzuki', handle: 'hana', role: 'trader', tint: 'p6' },
      { name: 'Tom Becker', handle: 'tbecker', role: 'trader', tint: 'p5' },
      { name: 'Lena Ortiz', handle: 'lena', role: 'trader', tint: 'p4' },
    ],
    positions: [
      { symbol: 'TSLA', side: 'short', instr: 'equity', qty: 60, entry: 244.5, drift: 0.041 },
      { symbol: 'AMD', side: 'long', instr: 'equity', qty: 140, entry: 148.2, drift: -0.028 },
      { symbol: 'SPY', side: 'long', instr: 'equity', qty: 50, entry: 548.9, drift: 0.012 },
      { symbol: 'COIN', side: 'short', instr: 'equity', qty: 40, entry: 312.0, drift: 0.064 },
    ],
  },
  {
    code: 3,
    name: 'Volatility Arb',
    strategy: 'Convexity & dispersion',
    assetClass: 'Options · Equities',
    tint: 'p5',
    allocated: 100_000,
    end: 104_910,
    realized: 1_980,
    fees: 311,
    description:
      'Owns cheap convexity and trades single-name vs index dispersion. Long gamma into events, monetizing realized-vs-implied gaps.',
    traders: [
      { name: 'Sofia Reyes', handle: 'sofia', role: 'pm', tint: 'p5' },
      { name: 'Noah Kim', handle: 'nkim', role: 'trader', tint: 'p2' },
      { name: 'Yusuf Demir', handle: 'yusuf', role: 'trader', tint: 'p3' },
    ],
    positions: [
      { symbol: 'AAPL', side: 'long', instr: 'equity', qty: 90, entry: 224.1, drift: 0.034 },
      { symbol: 'GOOGL', side: 'long', instr: 'equity', qty: 70, entry: 168.7, drift: 0.052 },
      { symbol: 'AMZN', side: 'long', instr: 'equity', qty: 65, entry: 197.3, drift: 0.027 },
      { symbol: 'QQQ', side: 'short', instr: 'equity', qty: 35, entry: 471.2, drift: 0.019 },
    ],
  },
]

const ORDER_TYPES = ['MARKET', 'LIMIT', 'MARKET', 'MARKET', 'LIMIT']

export function buildDemo(): FundData {
  const pods: Pod[] = []
  const allTraders: Trader[] = []
  const allTrades: Trade[] = []
  const allPositions: Position[] = []
  const now = Date.now()

  SPECS.forEach((spec, pi) => {
    const podId = `pod-${spec.code}`
    const rng = mulberry32(spec.code * 7919)

    // traders
    const traders: Trader[] = spec.traders.map((t, ti) => ({
      id: `${podId}-t${ti}`,
      name: t.name,
      handle: t.handle,
      podId,
      podCode: spec.code,
      role: t.role,
      tint: t.tint,
      livePnl: 0,
      realizedPnl: 0,
      unrealizedPnl: 0,
      biggestWin: 0,
      biggestLoss: 0,
      maxDrawdown: 0,
      winRate: 0,
      trades: 0,
    }))

    // positions (marked to live price = entry * (1 + drift))
    const positions: Position[] = spec.positions.map((p, idx) => {
      const trader = traders[idx % traders.length]
      const current = round(p.entry * (1 + p.drift), 2)
      const signed = p.side === 'long' ? p.qty : -p.qty
      const mult = p.instr === 'option' ? 100 : 1
      const marketValue = round(signed * current * mult)
      const costBasis = round(signed * p.entry * mult)
      const unreal = round((current - p.entry) * signed * mult)
      const pos: Position = {
        id: `${podId}-p${idx}`,
        podId,
        symbol: p.symbol,
        side: p.side,
        instrumentType: p.instr,
        quantity: p.qty,
        avgEntry: p.entry,
        currentPrice: current,
        marketValue,
        costBasis,
        unrealizedPnl: unreal,
        realizedPnl: 0,
        totalPnl: unreal,
        trader: trader.name,
        openedAt: new Date(now - (3 + idx) * 24 * 3600 * 1000 - idx * 1.7e6).toISOString(),
      }
      return pos
    })

    const unrealizedPnl = round(positions.reduce((a, p) => a + p.unrealizedPnl, 0))
    const grossLong = positions.filter((p) => p.side === 'long').reduce((a, p) => a + Math.abs(p.marketValue), 0)
    const grossShort = positions.filter((p) => p.side === 'short').reduce((a, p) => a + Math.abs(p.marketValue), 0)
    const netMv = positions.reduce((a, p) => a + p.marketValue, 0)
    const totalPnl = round(spec.realized + unrealizedPnl - spec.fees)
    const accountValue = round(spec.allocated + totalPnl)
    const cash = round(accountValue - netMv)

    // NAV series
    const nav = makeNav(spec.code * 104729, spec.allocated, accountValue, 90)
    const sharpe = sharpeOf(nav)
    const mdd = maxDrawdownOf(nav)
    const dayReturn = round(nav[nav.length - 1].value / nav[nav.length - 2].value - 1, 4)

    // trades: open trades for each position + a few closed (realized) trades
    const podTrades: Trade[] = []
    positions.forEach((pos, idx) => {
      const trader = traders[idx % traders.length]
      const openSide = pos.side === 'long' ? 'buy' : 'sell'
      podTrades.push({
        id: `${podId}-tr-open-${idx}`,
        podId,
        podCode: spec.code,
        podName: spec.name,
        trader: trader.name,
        traderId: trader.id,
        symbol: pos.symbol,
        side: openSide,
        instrumentType: pos.instrumentType,
        quantity: pos.quantity,
        price: pos.avgEntry,
        notional: round(pos.quantity * pos.avgEntry * (pos.instrumentType === 'option' ? 100 : 1)),
        type: ORDER_TYPES[(spec.code + idx) % ORDER_TYPES.length],
        status: 'filled',
        realizedPnl: null,
        executedAt: pos.openedAt,
      })
    })
    // closed/realized trades
    const closedCount = 4 + Math.floor(rng() * 3)
    const closedSymbols = ['NFLX', 'JPM', 'BA', 'CRM', 'UBER', 'PLTR', 'SHOP', 'XOM', 'DIS']
    for (let i = 0; i < closedCount; i++) {
      const trader = traders[Math.floor(rng() * traders.length)]
      const sym = closedSymbols[Math.floor(rng() * closedSymbols.length)]
      const qty = 20 + Math.floor(rng() * 120)
      const price = round(40 + rng() * 380, 2)
      const realized = round((rng() - 0.42) * 1600)
      const hoursAgo = round(rng() * 96, 1)
      podTrades.push({
        id: `${podId}-tr-cl-${i}`,
        podId,
        podCode: spec.code,
        podName: spec.name,
        trader: trader.name,
        traderId: trader.id,
        symbol: sym,
        side: rng() > 0.5 ? 'sell' : 'buy',
        instrumentType: 'equity',
        quantity: qty,
        price,
        notional: round(qty * price),
        type: ORDER_TYPES[i % ORDER_TYPES.length],
        status: 'filled',
        realizedPnl: realized,
        executedAt: new Date(now - hoursAgo * 3.6e6).toISOString(),
      })
    }
    podTrades.sort((a, b) => +new Date(b.executedAt) - +new Date(a.executedAt))

    // attribute metrics to traders
    traders.forEach((tr) => {
      const trTrades = podTrades.filter((t) => t.traderId === tr.id)
      const trPositions = positions.filter((p) => p.trader === tr.name)
      const realizedList = trTrades.map((t) => t.realizedPnl).filter((v): v is number => v != null)
      const unreal = round(trPositions.reduce((a, p) => a + p.unrealizedPnl, 0))
      const realizedSum = round(realizedList.reduce((a, b) => a + b, 0))
      const wins = realizedList.filter((v) => v > 0).length
      tr.realizedPnl = realizedSum
      tr.unrealizedPnl = unreal
      tr.livePnl = round(realizedSum + unreal)
      tr.biggestWin = realizedList.length ? round(Math.max(0, ...realizedList)) : 0
      tr.biggestLoss = realizedList.length ? round(Math.min(0, ...realizedList)) : 0
      tr.winRate = realizedList.length ? round(wins / realizedList.length, 3) : 0
      tr.trades = trTrades.length
      // per-trader drawdown proxy scaled off pod
      tr.maxDrawdown = round(mdd * (0.6 + rng() * 0.5), 4)
    })

    const realizedAll = podTrades.map((t) => t.realizedPnl).filter((v): v is number => v != null)
    const wins = realizedAll.filter((v) => v > 0).length
    const winRate = realizedAll.length ? round(wins / realizedAll.length, 3) : 0

    const pod: Pod = {
      id: podId,
      code: spec.code,
      name: spec.name,
      strategy: spec.strategy,
      assetClass: spec.assetClass,
      description: spec.description,
      tint: spec.tint,
      inceptionDate: nav[0].t.slice(0, 10),
      allocatedCapital: spec.allocated,
      accountValue,
      cash,
      realizedPnl: round(spec.realized - spec.fees),
      unrealizedPnl,
      totalPnl,
      fees: spec.fees,
      totalReturn: round(totalPnl / spec.allocated, 4),
      dayReturn,
      liveGain: round(accountValue - spec.allocated),
      sharpe,
      maxDrawdown: mdd,
      winRate,
      biggestWin: realizedAll.length ? round(Math.max(0, ...realizedAll)) : 0,
      biggestLoss: realizedAll.length ? round(Math.min(0, ...realizedAll)) : 0,
      avgLeverage: round((grossLong + grossShort) / accountValue, 2),
      longExposure: round(grossLong / accountValue, 3),
      shortExposure: round(grossShort / accountValue, 3),
      traders,
      positions,
      nav,
    }

    pods.push(pod)
    allTraders.push(...traders)
    allTrades.push(...podTrades)
    allPositions.push(...positions)
    void pi
  })

  allTrades.sort((a, b) => +new Date(b.executedAt) - +new Date(a.executedAt))

  return {
    pods,
    traders: allTraders,
    trades: allTrades,
    positions: allPositions,
    ticker: demoTicker(),
    isLive: false,
    asOf: new Date().toISOString(),
  }
}

const TICKER_SEED: [string, number][] = [
  ['NVDA', 192.4], ['AAPL', 231.6], ['MSFT', 426.7], ['TSLA', 254.6], ['AMZN', 202.6],
  ['GOOGL', 177.5], ['META', 557.8], ['SPY', 555.4], ['QQQ', 480.1], ['AMD', 144.1],
  ['NFLX', 712.3], ['JPM', 232.1], ['COIN', 332.0], ['INTC', 28.9], ['PLTR', 41.7],
]

export function demoTicker(): TickerItem[] {
  const rng = mulberry32(Math.floor(Date.now() / 60000))
  return TICKER_SEED.map(([symbol, base]) => {
    const changePct = round((rng() - 0.45) * 4.2, 2)
    return { symbol, price: round(base * (1 + changePct / 100), 2), changePct }
  })
}
