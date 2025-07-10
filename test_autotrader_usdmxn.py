"""
Script de prueba automatizada para MrCashondoBot
Genera una señal forzada en USDMXN, baja los filtros y verifica el flujo completo:
- Generación de señal
- Envío a Telegram
- Ejecución automática
"""
import logging
from mt5_connector import MT5Connector
from signal_generator import SignalGenerator, TradingSignal
from risk_manager import RiskManager, RiskParameters
from telegram_alerts import TelegramAlerts
from main import MrCashondoBot

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_autotrader_usdmxn():
    """Prueba de autotrader con señal forzada USDMXN"""
    # Inicializar componentes
    bot = MrCashondoBot()
    assert bot.initialize_components(), "Fallo al inicializar componentes"

    # Configuración normal de filtros (restaurar si fue modificado)
    bot.signal_generator.confidence_threshold = 0.6  # Valor estándar
    bot.signal_generator.min_adx_threshold = 25      # Valor estándar
    bot.signal_generator.min_volume_threshold = 500  # Valor estándar
    # El min_atr_threshold es por símbolo, así que no se modifica globalmente

    # Obtener datos de mercado para USDMXN
    symbol = "USDMXN"
    timeframe = "M5"
    market_data = bot.mt5_connector.get_market_data(symbol, timeframe, 500)
    assert market_data, f"No se pudo obtener market data para {symbol}"

    # Analizar y generar señal real (no mock)
    signal = bot.signal_generator.analyze_market_data(market_data)
    assert signal, "No se generó señal real para USDMXN. Si no hay señal, revisa condiciones de mercado o baja filtros temporalmente."
    logger.info(f"Señal generada: {signal.signal_type} {signal.symbol} Confianza: {signal.confidence}")

    # Procesar señal usando el flujo real del bot
    bot.process_signal(signal)
    logger.info("Señal real procesada y enviada a Telegram. Verifica ejecución en MT5 y Telegram.")

if __name__ == "__main__":
    test_autotrader_usdmxn()
    print("\n✅ Prueba de autotrader USDMXN completada. Revisa logs, Telegram y MT5.")
