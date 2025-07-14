"""
Filtros técnicos para Mr. Cashondo
"""
def atr_sufficient(atr, threshold=0.001, timeframe='M5', symbol_type='forex'):
    # Fase 3: Ignorar símbolos con ATR muy bajo en M5 (<0.0005 para Forex)
    if timeframe == 'M5' and symbol_type == 'forex':
        return atr >= 0.0005
    return atr >= threshold

def adx_sufficient(adx, threshold=8):
    return adx >= threshold

def rsi_favorable(rsi):
    return 35 <= rsi <= 70
