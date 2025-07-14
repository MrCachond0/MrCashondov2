import numpy as np
def calculate_atr(high, low, close, period=14):
    high = np.array(high)
    low = np.array(low)
    close = np.array(close)
    tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
    atr = np.zeros_like(close)
    atr[:period] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr
