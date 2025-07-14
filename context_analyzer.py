"""
Módulo de análisis multitemporal para Mr. Cashondo
Incluye funciones para analizar tendencia H4, niveles clave y niveles de Fibonacci.

Funciones principales:
- analyze_h4_trend: Detecta tendencia macro usando EMA 200 y estructura HH/HL/LH/LL
- analyze_key_levels: Detecta soportes y resistencias recientes
- get_fibonacci_levels: Calcula niveles de Fibonacci relevantes
- analyze_context: Devuelve dict resumen de contexto multitemporal
- calculate_ema: Utilidad para EMA
"""
import numpy as np
from typing import List, Dict, Any

def analyze_h4_trend(close_prices: List[float], high_prices: List[float], low_prices: List[float], period_ema: int = 200) -> str:
    """
    Analiza la tendencia en H4 usando EMA 200 y estructura de máximos/mínimos.
    Retorna 'bullish', 'bearish' o 'neutral'.
    """
    if len(close_prices) < period_ema:
        return "neutral"
    # Calcular EMA 200
    ema = calculate_ema(close_prices, period_ema)
    price = close_prices[-1]
    # Estructura de máximos/mínimos
    hh = high_prices[-2] < high_prices[-1]
    hl = low_prices[-2] < low_prices[-1]
    lh = high_prices[-2] > high_prices[-1]
    ll = low_prices[-2] > low_prices[-1]
    if price > ema[-1] and hh and hl:
        return "bullish"
    elif price < ema[-1] and lh and ll:
        return "bearish"
    else:
        return "neutral"

def analyze_key_levels(close_prices: List[float], window: int = 50) -> List[float]:
    """
    Detecta niveles clave (soportes y resistencias) en una ventana de precios.
    """
    if len(close_prices) < window:
        return []
    window_prices = close_prices[-window:]
    support = min(window_prices)
    resistance = max(window_prices)
    return [support, resistance]

def get_fibonacci_levels(close_prices: List[float], window: int = 50) -> Dict[str, float]:
    """
    Calcula niveles de Fibonacci entre el máximo y mínimo de la ventana.
    """
    if len(close_prices) < window:
        return {}
    window_prices = close_prices[-window:]
    high = max(window_prices)
    low = min(window_prices)
    diff = high - low
    levels = {
        "38.2": high - diff * 0.382,
        "50.0": high - diff * 0.5,
        "61.8": high - diff * 0.618
    }
    return levels

def analyze_context(close_prices: List[float], high_prices: List[float], low_prices: List[float], period_ema: int = 200, window: int = 50) -> Dict[str, Any]:
    """
    Analiza el contexto multitemporal y retorna dict con tendencia, niveles clave y Fibonacci.
    """
    trend = analyze_h4_trend(close_prices, high_prices, low_prices, period_ema)
    key_levels = analyze_key_levels(close_prices, window)
    fibonacci = get_fibonacci_levels(close_prices, window)
    return {
        "trend": trend,
        "key_levels": key_levels,
        "fibonacci": fibonacci
    }

# Utilidad: EMA simple (puede importar de indicators.ema si existe)
def calculate_ema(prices, period):
    prices = np.array(prices, dtype=float)
    if len(prices) < period:
        return np.array([prices[-1]]*len(prices))
    ema = np.zeros_like(prices)
    k = 2 / (period + 1)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = prices[i] * k + ema[i-1] * (1 - k)
    return ema
