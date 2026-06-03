import numpy as np
import pandas as pd


def get_sharpe(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    """Annualized Sharpe ratio. Higher is better; >1 is good, >2 is great."""
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess = returns - daily_rf
    return round(float((excess.mean() / excess.std()) * np.sqrt(252)), 4)


def get_sortino(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    """Annualized Sortino ratio. Like Sharpe but only penalizes downside volatility."""
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess = returns - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return float("inf")
    return round(float((excess.mean() / downside.std()) * np.sqrt(252)), 4)


def get_max_drawdown(returns: pd.Series) -> float:
    """Max peak-to-trough drawdown. Returns a negative decimal: -0.23 = -23%."""
    if len(returns) < 2:
        return 0.0
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    return round(float(drawdown.min()), 4)


def get_beta(stock_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Beta vs a benchmark. 1.0 = market, >1 = more volatile, <0 = inverse."""
    combined = pd.concat([stock_returns, benchmark_returns], axis=1).dropna()
    combined.columns = ["stock", "benchmark"]
    var = combined["benchmark"].var()
    if var == 0:
        return 0.0
    cov = combined.cov().iloc[0, 1]
    return round(cov / var, 4)


def get_volatility(returns: pd.Series) -> float:
    """Annualized realized volatility. Returns a decimal: 0.25 = 25%."""
    if len(returns) < 2:
        return 0.0
    return round(float(returns.std() * np.sqrt(252)), 4)
