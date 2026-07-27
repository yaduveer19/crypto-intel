from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class StrategyResult:
    bias: str = "NEUTRAL"
    tier: str = "LOW"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    reasoning: str = ""
    signals: list = field(default_factory=list)


class BaseStrategy(ABC):
    @property
    @abstractmethod
    def key(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    def default_params(self) -> dict:
        return {}

    @abstractmethod
    def analyze(self, symbol: str, ohlcv: list, params: dict = None) -> StrategyResult:
        pass


_strategies = {}


def register_strategy(cls):
    instance = cls()
    _strategies[instance.key] = instance
    return cls


def get_strategy(key: str) -> Optional[BaseStrategy]:
    return _strategies.get(key)


def get_all_strategies() -> list:
    return [
        {
            "key": s.key,
            "name": s.name,
            "description": s.description,
            "default_params": s.default_params,
        }
        for s in _strategies.values()
    ]


def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return (max(highs) - min(lows)) * 0.3
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    return sum(trs[-period:]) / period


def ema(values, period):
    if len(values) < period:
        return sum(values) / len(values)
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for v in values[period:]:
        result = (v - result) * multiplier + result
    return result


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
