"""
Módulo de cálculo de EMA para Mr. Cashondo
"""
import numpy as np

def calculate_ema(prices, period):
    """Calcula la EMA de una serie de precios."""
    prices = np.array(prices, dtype=float)
    
    if len(prices) < period:
        raise ValueError("La longitud de precios debe ser al menos igual al período.")
    
    ema = np.zeros_like(prices)
    k = 2 / (period + 1)

    # Inicializa con el promedio simple de los primeros `period` valores
    ema[period - 1] = np.mean(prices[:period])

    # Rellenamos los anteriores con NaN
    ema[:period - 1] = np.nan

    for i in range(period, len(prices)):
        ema[i] = prices[i] * k + ema[i - 1] * (1 - k)

    return ema