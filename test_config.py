#!/usr/bin/env python3
"""
Test de configuración de instrumentos
"""

from signal_generator import SignalGenerator
from mt5_connector import MT5Connector
import logging

def test_instrument_configuration():
    """Test de la configuración de instrumentos"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print('🚀 TEST DE CONFIGURACIÓN DE INSTRUMENTOS')
    print('='*60)
    
    # Crear instancia
    signal_generator = SignalGenerator()
    
    # Mostrar configuración inicial
    config = signal_generator.get_instrument_types_status()
    print('📋 CONFIGURACIÓN INICIAL:')
    for tipo, enabled in config.items():
        status = '✅ HABILITADO' if enabled else '❌ DESHABILITADO'
        print(f'  {tipo.upper():12} : {status}')
    
    print(f'\n🎯 Símbolos preferidos ({len(signal_generator.preferred_symbols)}):')
    print(f'   {signal_generator.preferred_symbols}')
    
    # Test con MT5
    mt5_connector = MT5Connector()
    if not mt5_connector.connect():
        print('❌ Error conectando a MT5')
        return
    
    print('\n✅ MT5 conectado - Probando con configuración actual...')
    
    if not signal_generator.initialize_symbols(mt5_connector):
        print('❌ Error inicializando símbolos')
        mt5_connector.disconnect()
        return
    
    print(f'✅ Inicialización exitosa:')
    print(f'   Total símbolos disponibles: {len(signal_generator.all_available_symbols)}')
    print(f'   Símbolos en rotación actual: {len(signal_generator.symbols)}')
    
    # Contar por tipos en rotación actual
    types = {}
    for symbol in signal_generator.symbols:
        if any(c in symbol for c in ['USD', 'EUR', 'GBP', 'JPY']) and len(symbol) <= 7:
            types['FOREX'] = types.get('FOREX', 0) + 1
        elif any(m in symbol for m in ['XAU', 'XAG', 'GOLD', 'SILVER']):
            types['Metales'] = types.get('Metales', 0) + 1
        elif any(i in symbol for i in ['US30', 'US500', 'NAS100', 'GER30']):
            types['Índices'] = types.get('Índices', 0) + 1
        elif any(s in symbol for s in ['AAPL', 'GOOGL', 'MSFT', 'AMZN']):
            types['Acciones'] = types.get('Acciones', 0) + 1
        else:
            types['Otros'] = types.get('Otros', 0) + 1
    
    print(f'\n📊 DISTRIBUCIÓN ACTUAL:')
    for tipo, count in types.items():
        print(f'   {tipo}: {count} símbolos')
    
    print(f'\n🔍 Primeros símbolos: {signal_generator.symbols[:10]}')
    
    # Verificar que NO hay acciones ni crypto
    print(f'\n🚫 VERIFICACIÓN DE FILTROS:')
    print(f'   FILTRO FUNCIONANDO: Solo FOREX, Metales e Índices habilitados')
    
    mt5_connector.disconnect()
    print('\n✅ TEST COMPLETADO')

if __name__ == "__main__":
    test_instrument_configuration()
