import { METRIC_META } from '@/lib/metrics'

export function About() {
  return (
    <div className="max-w-3xl space-y-12 text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white mb-3">
          Methodology &amp; Transparency
        </h1>
        <p>
          This portal provides a real-time, read-only view of a multi-pod quantitative fund.
          All data is sourced directly from our trading infrastructure via Supabase. No data
          is fabricated or smoothed for display.
        </p>
      </div>

      <section>
        <h2 className="text-base font-semibold text-zinc-900 dark:text-white mb-4">Data Freshness</h2>
        <ul className="space-y-2 list-disc list-inside text-zinc-600 dark:text-zinc-400">
          <li>Trades appear in real time as fills are confirmed by Alpaca Markets.</li>
          <li>Position marks (current price, market value, unrealized P&L) refresh every 5–15 minutes during market hours via scheduled sync.</li>
          <li>NAV and daily return are computed at market close each trading day.</li>
          <li>Risk/performance metrics are recomputed daily after NAV is confirmed.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-base font-semibold text-zinc-900 dark:text-white mb-4">Risk-Free Rate</h2>
        <p className="text-zinc-600 dark:text-zinc-400">
          We use an annualized risk-free rate of{' '}
          <strong className="text-zinc-900 dark:text-white">5.00%</strong> (stored in
          the <code className="bg-zinc-100 dark:bg-white/10 px-1 rounded">config</code> table, last updated June 2025).
          Daily risk-free = annual rate ÷ 252 trading days. Update this on the{' '}
          <code className="bg-zinc-100 dark:bg-white/10 px-1 rounded">config</code> table to reflect current Fed funds
          rate changes.
        </p>
      </section>

      <section>
        <h2 className="text-base font-semibold text-zinc-900 dark:text-white mb-4">Benchmark Assignments</h2>
        <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-white/10">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 bg-zinc-50 dark:border-white/10 dark:bg-white/5">
                <th className="py-2 px-4 text-left text-zinc-500 font-medium">Asset Class</th>
                <th className="py-2 px-4 text-left text-zinc-500 font-medium">Benchmark</th>
                <th className="py-2 px-4 text-left text-zinc-500 font-medium">Rationale</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Equities', 'SPY', 'SPDR S&P 500 ETF — broad US equity market.'],
                ['Options', 'SPY', 'Underlying equity market. Consider VIXM for vol-focused pods.'],
                ['Fixed Income', 'AGG', 'Bloomberg US Aggregate Bond ETF.'],
                ['Crypto', 'BTC', 'Bitcoin as crypto market proxy.'],
                ['FX', 'DXY', 'US Dollar Index.'],
              ].map(([cls, sym, note]) => (
                <tr key={cls} className="border-b border-zinc-100 dark:border-white/5">
                  <td className="py-2.5 px-4 text-zinc-700 dark:text-zinc-300">{cls}</td>
                  <td className="py-2.5 px-4 font-mono text-zinc-900 dark:text-white">{sym}</td>
                  <td className="py-2.5 px-4 text-zinc-500 text-xs">{note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-base font-semibold text-zinc-900 dark:text-white mb-4">Metric Definitions</h2>
        <p className="text-zinc-600 dark:text-zinc-400 mb-4">
          Let <em>r</em><sub>t</sub> = daily pod return, <em>b</em><sub>t</sub> = benchmark daily
          return, <em>r</em><sub>f</sub> = daily risk-free rate (annual ÷ 252), N = 252.
          Metrics require a minimum of 20 trading days of history before they are displayed.
        </p>
        <div className="space-y-4">
          {Object.entries(METRIC_META).map(([key, meta]) => (
            <div key={key} className="border-l-2 border-zinc-200 dark:border-white/10 pl-4">
              <p className="font-medium text-zinc-900 dark:text-white">{meta.label}</p>
              <p className="text-zinc-600 dark:text-zinc-400 text-xs mt-0.5">{meta.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-base font-semibold text-zinc-900 dark:text-white mb-3">Architecture</h2>
        <p className="text-zinc-600 dark:text-zinc-400">
          The frontend is a static SPA (Vite + React + TypeScript) deployed to GitHub Pages.
          It connects to Supabase using a public, read-only anonymous key. Row Level Security
          (RLS) enforces that the browser can only read — it cannot write to any table.
          All writes originate from a separate Python trading engine that holds the privileged
          service-role key and never exposes it to this portal.
        </p>
      </section>
    </div>
  )
}
