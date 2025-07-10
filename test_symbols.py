#!/usr/bin/env python3
"""
Script para analizar todos los símbolos disponibles en MT5
"""

from mt5_connector import MT5Connector
import MetaTrader5 as mt5

def analyze_all_symbols():
    """Analizar todos los símbolos disponibles en MT5"""
    
    # Crear instancia
    mt5_connector = MT5Connector()
    
    # Intentar conectar
    if not mt5_connector.connect():
        print('Error conectando a MT5')
        return
    
    print('MT5 conectado exitosamente')
    
    # Obtener TODOS los símbolos disponibles directamente de MT5
    all_symbols = mt5.symbols_get()
    print(f'Total de símbolos en MT5: {len(all_symbols)}')
    
    # Analizar por categorías
    forex_symbols = []
    metal_symbols = []
    index_symbols = []
    
    for symbol in all_symbols:
        symbol_name = symbol.name
        path = symbol.path.lower()
        
        if any(indicator in path for indicator in ['forex', 'fx', 'currency', 'currencies']):
            forex_symbols.append(symbol_name)
        elif any(indicator in path for indicator in ['metals', 'precious', 'gold', 'silver']) or any(m in symbol_name for m in ['XAU', 'XAG', 'GOLD', 'SILVER']):
            metal_symbols.append(symbol_name)
        elif any(indicator in path for indicator in ['indices', 'index', 'stock', 'cfd']) or any(i in symbol_name for i in ['US30', 'US500', 'NAS100', 'GER30', 'UK100']):
            index_symbols.append(symbol_name)
    
    print(f'\nDistribución por categorías:')
    print(f'  FOREX: {len(forex_symbols)}')
    print(f'  Metales: {len(metal_symbols)}')
    print(f'  Índices: {len(index_symbols)}')
    
    print(f'\nPrimeros 10 símbolos de cada categoría:')
    print(f'  FOREX: {forex_symbols[:10]}')
    print(f'  Metales: {metal_symbols[:10]}')
    print(f'  Índices: {index_symbols[:10]}')
    
    # Verificar si hay símbolos visibles y seleccionables
    tradeable_symbols = [s.name for s in all_symbols if s.visible and s.select and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL]
    print(f'\nSímbolos operables: {len(tradeable_symbols)}')
    
    # Mostrar las categorías de "otros"
    print(f'\nCategorías de "otros símbolos":')
    other_paths = set()
    for symbol in all_symbols:
        if symbol.name in other_symbols:
            other_paths.add(symbol.path)
    
    for path in sorted(other_paths):
        count = sum(1 for s in all_symbols if s.path == path and s.name in other_symbols)
        print(f'  {path}: {count} símbolos')
    
    mt5_connector.disconnect()

if __name__ == "__main__":
    analyze_all_symbols()
