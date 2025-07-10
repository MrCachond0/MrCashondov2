#!/usr/bin/env python3
"""
Test del sistema de rotación con todos los símbolos MT5
"""

from signal_generator import SignalGenerator
from mt5_connector import MT5Connector
import logging

def test_rotation_system():
    """Test del sistema de rotación completo"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Crear instancias
    mt5_connector = MT5Connector()
    signal_generator = SignalGenerator()
    
    # Intentar conectar
    if not mt5_connector.connect():
        print('Error conectando a MT5')
        return
    
    print('MT5 conectado exitosamente')
    
    # Inicializar símbolos con rotación
    if not signal_generator.initialize_symbols(mt5_connector):
        print('Error inicializando símbolos')
        mt5_connector.disconnect()
        return
    
    print(f'Sistema de rotación inicializado con {len(signal_generator.all_available_symbols)} símbolos totales')
    print(f'Símbolos en rotación actual: {len(signal_generator.symbols)}')
    print(f'Primeros 15 símbolos de la rotación: {signal_generator.symbols[:15]}')
    print(f'Rotación actual: {signal_generator.current_cycle}')
    print(f'Índice de rotación: {signal_generator.rotation_index}')
    
    # Mostrar estadísticas por tipo de símbolo
    forex_count = sum(1 for s in signal_generator.all_available_symbols if any(c in s for c in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']) and len(s) <= 7)
    metal_count = sum(1 for s in signal_generator.all_available_symbols if any(m in s for m in ['XAU', 'XAG', 'GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM']))
    index_count = sum(1 for s in signal_generator.all_available_symbols if any(i in s for i in ['US30', 'US500', 'NAS100', 'GER30', 'UK100', 'AUS200']))
    stock_count = sum(1 for s in signal_generator.all_available_symbols if any(stock in s for stock in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META']))
    other_count = len(signal_generator.all_available_symbols) - forex_count - metal_count - index_count - stock_count
    
    print(f'\nDistribución de símbolos en rotación:')
    print(f'  FOREX: {forex_count}')
    print(f'  Metales: {metal_count}')
    print(f'  Índices: {index_count}')
    print(f'  Acciones: {stock_count}')
    print(f'  Otros: {other_count}')
    
    # Mostrar símbolos preferidos que están activos
    preferred_active = [s for s in signal_generator.symbols if s in signal_generator.preferred_symbols]
    print(f'\nSímbolos preferidos activos: {preferred_active}')
    
    # Probar una rotación manual
    print("\n--- Probando rotación manual ---")
    signal_generator._rotate_symbols(mt5_connector)
    
    print(f'Después de rotación - Símbolos activos: {len(signal_generator.symbols)}')
    print(f'Nuevos primeros 15 símbolos: {signal_generator.symbols[:15]}')
    print(f'Nueva rotación: {signal_generator.current_cycle}')
    print(f'Nuevo índice: {signal_generator.rotation_index}')
    
    # Mostrar algunos ejemplos de cada tipo
    print("\n--- Ejemplos de tipos de símbolos ---")
    
    # FOREX
    forex_examples = [s for s in signal_generator.all_available_symbols if any(c in s for c in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']) and len(s) <= 7][:10]
    print(f"FOREX ejemplos: {forex_examples}")
    
    # Metales
    metal_examples = [s for s in signal_generator.all_available_symbols if any(m in s for m in ['XAU', 'XAG', 'GOLD', 'SILVER'])][:10]
    print(f"Metales ejemplos: {metal_examples}")
    
    # Índices
    index_examples = [s for s in signal_generator.all_available_symbols if any(i in s for i in ['US30', 'US500', 'NAS100', 'GER30', 'UK100', 'AUS200']) or 'INDEX' in s.upper()][:10]
    print(f"Índices ejemplos: {index_examples}")
    
    # Acciones
    stock_examples = [s for s in signal_generator.all_available_symbols if any(stock in s for stock in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC'])][:10]
    print(f"Acciones ejemplos: {stock_examples}")
    
    # Otros
    other_examples = [s for s in signal_generator.all_available_symbols if len(s) > 7 or any(other in s for other in ['ETF', 'FUND', 'TRUST'])][:10]
    print(f"Otros ejemplos: {other_examples}")
    
    mt5_connector.disconnect()

if __name__ == "__main__":
    test_rotation_system()
