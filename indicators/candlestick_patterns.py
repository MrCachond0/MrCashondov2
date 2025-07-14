import numpy as np
def pin_bar(open_, high, low, close):
    # Simplificado: pin bar alcista/bajista
    pin_bull = (close > open_) & ((high - close) < (close - low))
    pin_bear = (open_ > close) & ((high - open_) < (open_ - low))
    return pin_bull, pin_bear
def bullish_engulfing(open_, high, low, close):
    # Simplificado: engulfing alcista
    return (close[-2] < open_[-2]) & (close[-1] > open_[-1]) & (close[-1] > open_[-2])
def bearish_engulfing(open_, high, low, close):
    # Simplificado: engulfing bajista
    return (open_[-2] < close[-2]) & (open_[-1] > close[-1]) & (open_[-1] > close[-2])
