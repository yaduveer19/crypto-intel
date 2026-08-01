from app.strategies.engine import StrategyResult, get_all_strategies, get_strategy
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from app.strategies.macd_momentum import MACDMomentumStrategy
from app.strategies.breakout import BreakoutStrategy
from app.strategies.grid_levels import GridLevelsStrategy
from app.strategies.scalping import (  # noqa: F401 — registers scalping strategies
    VWAPReversionStrategy,
    OpeningRangeBreakoutStrategy,
    CVDDivergenceStrategy,
    OrderFlowMomentumStrategy,
)
