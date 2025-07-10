#!/usr/bin/env python3
"""
Utilidad para configurar tipos de instrumentos en Mr. Cashondo
"""

from signal_generator import SignalGenerator
from mt5_connector import MT5Connector
import logging

def display_current_config(signal_generator):
    """Mostrar configuración actual"""
    print("\n" + "="*60)
    print("         CONFIGURACIÓN ACTUAL DE INSTRUMENTOS")
    print("="*60)
    
    config = signal_generator.get_instrument_types_status()
    preferred = signal_generator.preferred_symbols
    
    for instrument_type, enabled in config.items():
        status = "✅ HABILITADO" if enabled else "❌ DESHABILITADO"
        print(f"  {instrument_type.upper():12} : {status}")
    
    print(f"\nSímbolos preferidos activos ({len(preferred)}):")
    print(f"  {', '.join(preferred[:15])}{'...' if len(preferred) > 15 else ''}")
    print("="*60)

def configure_instruments():
    """
    Configura los tipos de instrumentos habilitados para análisis.
    """
    signal_generator = SignalGenerator()
    signal_generator.configure_instrument_types(
        forex=True, indices=True, metals=True, stocks=False, crypto=False
    )
    print("Configuración aplicada:")
    print("✅ FOREX: Habilitado")
    print("✅ Índices: Habilitado")
    print("✅ Metales: Habilitado")
    print("❌ Acciones: Deshabilitado")
    print("❌ Criptomonedas: Deshabilitado")

def test_configuration(signal_generator):
    """Test de la configuración actual"""
    try:
        mt5_connector = MT5Connector()
        
        if not mt5_connector.connect():
            print("❌ Error conectando a MT5")
            return
        
        print("✅ MT5 conectado")
        
        # Inicializar símbolos con configuración actual
        if signal_generator.initialize_symbols(mt5_connector):
            print(f"✅ Símbolos inicializados: {len(signal_generator.all_available_symbols)} totales")
            print(f"✅ Símbolos en rotación: {len(signal_generator.symbols)}")
            
            # Contar por tipos
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
            
            print("\n📊 Distribución de instrumentos en rotación:")
            for tipo, count in types.items():
                print(f"  {tipo}: {count} símbolos")
            
            # Mostrar algunos ejemplos
            print(f"\n🔍 Primeros 15 símbolos: {signal_generator.symbols[:15]}")
            
            # Símbolos preferidos activos
            preferred_active = [s for s in signal_generator.symbols if s in signal_generator.preferred_symbols]
            print(f"🎯 Símbolos preferidos activos: {len(preferred_active)}")
            print(f"   {preferred_active}")
            
        else:
            print("❌ Error inicializando símbolos")
        
        mt5_connector.disconnect()
        
    except Exception as e:
        print(f"❌ Error en test: {e}")

def quick_disable_stocks_crypto():
    """Función rápida para deshabilitar acciones y cripto"""
    signal_generator = SignalGenerator()
    signal_generator.configure_instrument_types(stocks=False, crypto=False)
    
    print("🚀 MR. CASHONDO - CONFIGURACIÓN APLICADA")
    print("✅ FOREX: Habilitado")
    print("✅ Índices: Habilitado") 
    print("✅ Metales/Commodities: Habilitado")
    print("❌ Acciones: DESHABILITADO")
    print("❌ Criptomonedas: DESHABILITADO")
    
    return signal_generator

if __name__ == "__main__":
    configure_instruments()
