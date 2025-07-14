"""
Filtros pre-técnicos para Mr. Cashondo
"""
def has_sufficient_data(market_data, min_bars=200):
    return len(market_data['close']) >= min_bars

def spread_within_reasonable_bounds(symbol_info, max_spread=20):
    return symbol_info['spread'] <= max_spread

def symbol_is_tradeable(symbol_info):
    return symbol_info.get('trade_mode', 0) == 0 or symbol_info.get('trade_mode', 0) == 1
