import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import { useNavHistory } from '@/hooks/useNavHistory'
import { useIntradayNav } from '@/hooks/useLiveSnapshots'
import { formatCompact, formatPct } from '@/lib/formatters'
import { useTheme } from '@/lib/theme'
import { format } from 'date-fns'

interface NavChartProps {
  podId: string
  startingCapital: number
  liveNav?: number
}

export function NavChart({ podId, startingCapital, liveNav }: NavChartProps) {
  const { data: history, isLoading } = useNavHistory(podId)
  const { data: intraday, isLoading: isIntradayLoading } = useIntradayNav(podId)
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

  if (isLoading || isIntradayLoading) {
    return <div className="h-64 rounded-xl bg-zinc-100 dark:bg-white/5 animate-pulse" />
  }

  if (!history?.length && !intraday?.length) {
    return (
      <div className="h-64 rounded-xl bg-zinc-100 dark:bg-white/5 flex items-center justify-center text-zinc-500 text-sm">
        No NAV history yet.
      </div>
    )
  }

  const hasIntraday = !!intraday?.length
  const chartData = hasIntraday
    ? intraday.map((row) => ({
        date: row.timestamp,
        nav: Number(row.nav),
        return: Number(row.minute_return ?? 0),
        cumReturn: (Number(row.nav) - startingCapital) / startingCapital,
      }))
    : (history ?? []).map((row) => ({
        date: row.date,
        nav: Number(row.nav),
        return: Number(row.daily_return ?? 0),
        cumReturn: (Number(row.nav) - startingCapital) / startingCapital,
      }))

  const latest = chartData[chartData.length - 1]
  const displayNav = liveNav ?? latest?.nav
  const gain = displayNav ? (displayNav - startingCapital) / startingCapital : 0
  const stroke = gain >= 0 ? '#34d399' : '#f87171'

  const gridStroke = isDark ? '#1d251f' : '#00000010'
  const axisTick = isDark ? '#5f6b63' : '#a1a1aa'
  const tooltipBg = isDark ? '#0b0f0d' : '#ffffff'
  const tooltipBorder = isDark ? '#1f2a23' : '#e4e4e7'
  const tooltipText = isDark ? '#f4fff7' : '#18181b'

  return (
    <div>
      <div className="flex items-end gap-3 mb-4">
        <span className="text-2xl font-bold text-zinc-900 dark:text-white">
          {formatCompact(displayNav)}
        </span>
        <span
          className={`text-sm font-medium pb-0.5 ${
            gain >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
          }`}
        >
          {formatPct(gain)} since inception
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id={`navGrad-${podId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={stroke} stopOpacity={0.3} />
              <stop offset="95%" stopColor={stroke} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
          <XAxis
            dataKey="date"
            tickFormatter={(d) => format(new Date(d), hasIntraday ? 'HH:mm' : 'MMM d')}
            tick={{ fill: axisTick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            minTickGap={hasIntraday ? 28 : 18}
          />
          <YAxis
            tickFormatter={(v) => formatCompact(v)}
            tick={{ fill: axisTick, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={70}
          />
          <Tooltip
            contentStyle={{
              background: tooltipBg,
              border: `1px solid ${tooltipBorder}`,
              borderRadius: 8,
              color: tooltipText,
            }}
            labelStyle={{ color: tooltipText }}
            labelFormatter={(d) => format(new Date(d as string), hasIntraday ? 'MMM d, HH:mm' : 'MMM d, yyyy')}
            formatter={(v: number) => [formatCompact(v), 'NAV']}
          />
          <Area
            type="monotone"
            dataKey="nav"
            stroke={stroke}
            strokeWidth={2}
            fill={`url(#navGrad-${podId})`}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
