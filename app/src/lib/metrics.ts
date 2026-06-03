export const METRIC_META: Record<
  string,
  { label: string; description: string; format: 'pct' | 'number' | 'ratio' }
> = {
  cumulative_return: {
    label: 'Cumulative Return',
    description: 'Total return since inception: ∏(1 + rₜ) − 1.',
    format: 'pct',
  },
  annualized_return: {
    label: 'Annualized Return',
    description: 'Cumulative return scaled to a 252-trading-day year.',
    format: 'pct',
  },
  volatility: {
    label: 'Volatility (Ann.)',
    description: 'Standard deviation of daily returns × √252.',
    format: 'pct',
  },
  sharpe: {
    label: 'Sharpe Ratio',
    description: '(Mean daily excess return) / σ × √252.',
    format: 'ratio',
  },
  sortino: {
    label: 'Sortino Ratio',
    description: 'Like Sharpe but penalises only downside deviations.',
    format: 'ratio',
  },
  beta: {
    label: 'Beta',
    description: 'Covariance(pod, benchmark) / Variance(benchmark).',
    format: 'ratio',
  },
  alpha: {
    label: "Alpha (Jensen's)",
    description: 'Annualised excess return beyond what beta predicts.',
    format: 'pct',
  },
  max_drawdown: {
    label: 'Max Drawdown',
    description: 'Worst peak-to-trough NAV decline.',
    format: 'pct',
  },
  calmar: {
    label: 'Calmar Ratio',
    description: 'Annualised return / |Max Drawdown|.',
    format: 'ratio',
  },
  var_95: {
    label: 'VaR 95% (1-day)',
    description: 'Historical 1-day loss not exceeded 95% of the time.',
    format: 'pct',
  },
  win_rate: {
    label: 'Win Rate',
    description: 'Fraction of trading days with positive return.',
    format: 'pct',
  },
}

export const ASSET_CLASS_LABELS: Record<string, string> = {
  equities: 'Equities',
  options: 'Options',
  fixed_income: 'Fixed Income',
  crypto: 'Crypto',
  fx: 'FX',
  futures: 'Futures',
}

export const ASSET_CLASS_COLORS: Record<string, string> = {
  equities: '#6366f1',
  options: '#f59e0b',
  fixed_income: '#10b981',
  crypto: '#f97316',
  fx: '#3b82f6',
  futures: '#ec4899',
}
