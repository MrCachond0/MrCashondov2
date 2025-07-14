"""
Módulo de cálculo de MACD para Mr. Cashondo
"""
import numpy as np
from .ema import calculate_ema

def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """Calcula el MACD y la señal."""
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)
    macd = ema_fast - ema_slow
    signal = calculate_ema(macd, signal_period)
    return macd, signal
