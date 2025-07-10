"""
Test específico para verificar por qué no se generan señales
"""
import logging
from mt5_connector import MT5Connector
from signal_generator import SignalGenerator

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Activar debug específicamente para signal_generator
signal_logger = logging.getLogger('signal_generator')
signal_logger.setLevel(logging.DEBUG)

def test_signal_generation():
    """Test directo de generación de señales"""
    
    # Conectar a MT5
    mt5_connector = MT5Connector()
    if not mt5_connector.connect():
        logger.error("No se pudo conectar a MT5")
        return
    
    # Crear generador de señales
    signal_gen = SignalGenerator()
    
    # Inicializar con símbolos dinámicos
    if not signal_gen.initialize_symbols(mt5_connector):
        logger.error("No se pudieron inicializar símbolos")
        return
    
    logger.info(f"Símbolos a analizar: {signal_gen.symbols[:5]}")  # Solo los primeros 5
    
    # Analizar un símbolo específico manualmente
    symbol = "EURUSD"
    timeframe = "M15"
    
    logger.info(f"\n=== ANÁLISIS MANUAL DE {symbol} {timeframe} ===")
    
    # Obtener datos de mercado
    market_data = mt5_connector.get_market_data(symbol, timeframe, 500)
    if not market_data:
        logger.error(f"No se pudieron obtener datos para {symbol}")
        return
    
    logger.info(f"Datos obtenidos: {len(market_data.close)} barras")
    logger.info(f"Precio actual: {market_data.close[-1]:.5f}")
    
    # Verificar si el símbolo es tradeable
    is_tradeable = signal_gen.is_symbol_tradeable(symbol)
    logger.info(f"¿Es tradeable? {is_tradeable}")
    
    # Obtener estrategia adaptativa
    strategy = signal_gen.get_adaptive_strategy(symbol)
    logger.info(f"Estrategia adaptativa: {strategy}")
    
    # Analizar directamente
    signal = signal_gen.analyze_market_data(market_data)
    
    if signal:
        logger.info(f"¡SEÑAL ENCONTRADA! {signal.signal_type} para {signal.symbol}")
        logger.info(f"Precio entrada: {signal.entry_price:.5f}")
        logger.info(f"Stop Loss: {signal.stop_loss:.5f}")
        logger.info(f"Take Profit: {signal.take_profit:.5f}")
        logger.info(f"Confianza: {signal.confidence:.2f}")
        logger.info(f"Razones: {', '.join(signal.reasons)}")
    else:
        logger.info("No se encontró señal para este análisis")
    
    # Desconectar
    mt5_connector.disconnect()

if __name__ == "__main__":
    test_signal_generation()
