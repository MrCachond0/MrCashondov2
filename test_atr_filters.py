#!/usr/bin/env python3
"""
Test de filtros ATR ajustados
"""

from signal_generator import SignalGenerator
from mt5_connector import MT5Connector
import logging

def test_atr_filters():
    """Test de los nuevos filtros ATR"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print('🔧 TEST DE FILTROS ATR AJUSTADOS')
    print('='*60)
    
    # Crear instancias
    mt5_connector = MT5Connector()
    signal_generator = SignalGenerator()
    
    if not mt5_connector.connect():
        print('❌ Error conectando a MT5')
        return
    
    print('✅ MT5 conectado')
    
    # Inicializar símbolos
    if not signal_generator.initialize_symbols(mt5_connector):
        print('❌ Error inicializando símbolos')
        mt5_connector.disconnect()
        return
    
    print(f'✅ Símbolos inicializados: {len(signal_generator.symbols)} en rotación')
    
    # Test de análisis con filtros ajustados
    print('\n🔍 PROBANDO ANÁLISIS CON FILTROS AJUSTADOS...')
    
    # Analizar solo algunos símbolos para test
    test_symbols = signal_generator.symbols[:10]
    signals_found = 0
    symbols_passed_atr = 0
    
    for symbol in test_symbols:
        try:
            print(f'\n--- Analizando {symbol} ---')
            
            # Obtener datos del mercado
            market_data = mt5_connector.get_market_data(symbol, 'M5', 500)
            if not market_data:
                print(f'❌ No hay datos para {symbol}')
                continue
            
            # Analizar
            signal = signal_generator.analyze_market_data(market_data)
            
            if signal:
                signals_found += 1
                print(f'✅ SEÑAL GENERADA: {signal.signal_type} - Confianza: {signal.confidence:.2f}')
                print(f'   Razones: {", ".join(signal.reasons)}')
            else:
                print(f'⚪ No hay señal para {symbol}')
                
        except Exception as e:
            print(f'❌ Error analizando {symbol}: {e}')
    
    print(f'\n📊 RESULTADOS DEL TEST:')
    print(f'   Símbolos analizados: {len(test_symbols)}')
    print(f'   Señales encontradas: {signals_found}')
    print(f'   Tasa de señales: {(signals_found/len(test_symbols)*100):.1f}%')
    
    if signals_found > 0:
        print('✅ FILTROS AJUSTADOS FUNCIONANDO - Se generan señales')
    else:
        print('⚠️  Los filtros aún pueden estar demasiado restrictivos')
    
    mt5_connector.disconnect()
    print('\n✅ TEST COMPLETADO')

if __name__ == "__main__":
    test_atr_filters()
