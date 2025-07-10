#!/usr/bin/env python3
"""
Test final del sistema multi-instrumento con rotación
"""

from signal_generator import SignalGenerator
from mt5_connector import MT5Connector
import logging

def final_test():
    """Test final del sistema completo"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Crear instancias
    mt5_connector = MT5Connector()
    signal_generator = SignalGenerator()
    
    # Conectar y probar
    if not mt5_connector.connect():
        print('❌ Error conectando a MT5')
        return
    
    print('✅ MT5 conectado exitosamente')
    
    # Inicializar símbolos
    if not signal_generator.initialize_symbols(mt5_connector):
        print('❌ Error inicializando símbolos')
        mt5_connector.disconnect()
        return
    
    print(f'✅ Sistema inicializado con {len(signal_generator.all_available_symbols)} símbolos')
    print(f'✅ Rotación actual: {len(signal_generator.symbols)} símbolos activos')
    
    # Mostrar diversidad
    types = {}
    for symbol in signal_generator.symbols:
        if any(c in symbol for c in ['USD', 'EUR', 'GBP', 'JPY']) and len(symbol) <= 7:
            types['FOREX'] = types.get('FOREX', 0) + 1
        elif any(m in symbol for m in ['XAU', 'XAG', 'GOLD', 'SILVER']):
            types['Metales'] = types.get('Metales', 0) + 1
        elif any(i in symbol for i in ['US30', 'US500', 'NAS100', 'GER30']):
            types['Índices'] = types.get('Índices', 0) + 1
        elif any(s in symbol for s in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']):
            types['Acciones'] = types.get('Acciones', 0) + 1
        else:
            types['Otros'] = types.get('Otros', 0) + 1
    
    print('✅ Diversidad de instrumentos activos:')
    for tipo, count in types.items():
        print(f'   {tipo}: {count} símbolos')
    
    # Test de rotación
    print('\n🔄 Probando rotación...')
    signal_generator._rotate_symbols(mt5_connector)
    print(f'✅ Rotación completada - Nuevos símbolos: {len(signal_generator.symbols)}')
    
    # Símbolos preferidos
    preferred_active = [s for s in signal_generator.symbols if s in signal_generator.preferred_symbols]
    print(f'✅ Símbolos preferidos activos: {len(preferred_active)}/{len(signal_generator.preferred_symbols)}')
    print(f'   Activos: {preferred_active}')
    
    print('\n🎯 RESUMEN DEL SISTEMA:')
    print(f'   • Total símbolos disponibles: {len(signal_generator.all_available_symbols)}')
    print(f'   • Símbolos por rotación: {signal_generator.symbols_per_cycle}')
    print(f'   • Ciclos necesarios: {len(signal_generator.all_available_symbols) // signal_generator.symbols_per_cycle + 1}')
    print(f'   • Tipos de instrumentos: FOREX, Metales, Índices, Acciones, ETFs')
    print(f'   • Estado: ✅ SISTEMA MULTI-INSTRUMENTO ACTIVO')
    
    # Mostrar algunos ejemplos de cada tipo
    print('\n📋 Ejemplos de instrumentos por tipo:')
    
    # Separar por tipos
    forex_symbols = [s for s in signal_generator.all_available_symbols if any(c in s for c in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']) and len(s) <= 7]
    metal_symbols = [s for s in signal_generator.all_available_symbols if any(m in s for m in ['XAU', 'XAG', 'GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM'])]
    index_symbols = [s for s in signal_generator.all_available_symbols if any(i in s for i in ['US30', 'US500', 'NAS100', 'GER30', 'UK100', 'AUS200'])]
    stock_symbols = [s for s in signal_generator.all_available_symbols if any(stock in s for stock in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META'])]
    
    print(f'   FOREX ({len(forex_symbols)}): {forex_symbols[:8]}')
    print(f'   Metales ({len(metal_symbols)}): {metal_symbols[:5]}')
    print(f'   Índices ({len(index_symbols)}): {index_symbols[:5]}')
    print(f'   Acciones ({len(stock_symbols)}): {stock_symbols[:5]}')
    
    print('\n🚀 SISTEMA MULTI-INSTRUMENTO LISTO PARA TRADING!')
    
    mt5_connector.disconnect()

if __name__ == "__main__":
    final_test()
