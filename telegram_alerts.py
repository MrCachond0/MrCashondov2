"""
Telegram Alerts Module
Handles sending trading signals and notifications to Telegram
"""
import telebot
from typing import List, Dict, Optional
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
from signal_generator import TradingSignal

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_alerts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramAlerts:
    """
    Telegram bot for sending trading alerts and notifications
    """
    
    def __init__(self):
        """Initialize Telegram bot"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_ids = self._get_chat_ids()
        
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            raise ValueError("TELEGRAM_BOT_TOKEN not found")
        
        if not self.chat_ids:
            logger.error("No TELEGRAM_CHAT_ID found in environment variables")
            raise ValueError("No TELEGRAM_CHAT_ID found")
        
        try:
            test_env = os.getenv('TEST_ENV', 'false').lower() == 'true'
            if test_env:
                self.bot = None
                logger.info("Telegram bot initialization skipped in test environment.")
            else:
                if ':' not in self.bot_token:
                    logger.error("Invalid TELEGRAM_BOT_TOKEN format. Token must contain a colon.")
                    raise ValueError("Invalid TELEGRAM_BOT_TOKEN format")
                self.bot = telebot.TeleBot(self.bot_token)
                logger.info("Telegram bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            raise
    
    def _get_chat_ids(self) -> List[str]:
        """
        Get chat IDs from environment variables
        
        Returns:
            List of chat IDs
        """
        chat_ids = []
        
        # Get main chat ID
        main_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if main_chat_id:
            chat_ids.append(main_chat_id)
        
        # Get additional chat IDs
        i = 1
        while True:
            chat_id = os.getenv(f'TELEGRAM_CHAT_ID_{i}')
            if chat_id:
                chat_ids.append(chat_id)
                i += 1
            else:
                break
        
        return chat_ids
    
    def send_signal_alert(self, signal: TradingSignal) -> bool:
        """
        Envía SIEMPRE la señal a Telegram, sin importar si será ejecutada en MT5 o no.
        Args:
            signal: TradingSignal object
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = self._format_signal_message(signal)
            success = True
            for chat_id in self.chat_ids:
                try:
                    if self.bot:
                        self.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='HTML'
                        )
                        logger.info(f"Signal sent to chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send signal to chat {chat_id}: {str(e)}")
                    success = False
            return success
        except Exception as e:
            logger.error(f"Error sending signal alert: {str(e)}")
            return False
    
    def send_execution_alert(self, signal: TradingSignal, ticket: int, 
                           execution_price: float, volume: float) -> bool:
        """
        (Deshabilitado) No enviar notificaciones de ejecución de órdenes a Telegram.
        """
        logger.info("[Telegram] Notificación de ejecución de orden suprimida (no se envía a Telegram)")
        return True
    
    def send_close_alert(self, symbol: str, ticket: int, close_price: float, 
                        profit: float, reason: str) -> bool:
        """
        (Deshabilitado) No enviar notificaciones de cierre de posiciones a Telegram.
        """
        logger.info("[Telegram] Notificación de cierre de posición suprimida (no se envía a Telegram)")
        return True
    
    def send_error_alert(self, error_message: str, context: str = "") -> bool:
        """
        (Deshabilitado) No enviar notificaciones de error a Telegram.
        """
        logger.info("[Telegram] Notificación de error suprimida (no se envía a Telegram)")
        return True
    
    def send_daily_summary(self, daily_stats: Dict) -> bool:
        """
        (Deshabilitado) No enviar resumen diario a Telegram.
        """
        logger.info("[Telegram] Resumen diario suprimido (no se envía a Telegram)")
        return True
    
    def send_bot_status(self, status: str, uptime: str, balance: float) -> bool:
        """
        (Deshabilitado) No enviar actualizaciones de estado del bot a Telegram.
        """
        logger.info("[Telegram] Actualización de estado del bot suprimida (no se envía a Telegram)")
        return True
    
    def _format_signal_message(self, signal: TradingSignal) -> str:
        """
        Format trading signal message
        
        Args:
            signal: TradingSignal object
            
        Returns:
            Formatted message string
        """
        # Signal emoji
        signal_emoji = "📈" if signal.signal_type == "BUY" else "📉"
        
        # Risk-reward ratio
        if signal.signal_type == "BUY":
            risk = signal.entry_price - signal.stop_loss
            reward = signal.take_profit - signal.entry_price
        else:
            risk = signal.stop_loss - signal.entry_price
            reward = signal.entry_price - signal.take_profit
        
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Determinar tipo de instrumento para el encabezado
        category = self._categorize_by_symbol_name(signal.symbol)
        if category == "forex":
            header = "💹 <b>NUEVA OPERACIÓN FOREX</b>"
        elif category == "metal":
            header = "🪙 <b>NUEVA OPERACIÓN METAL</b>"
        elif category == "index":
            header = "📊 <b>NUEVA OPERACIÓN ÍNDICE</b>"
        elif category == "crypto":
            header = "🪙 <b>NUEVA OPERACIÓN CRYPTO</b>"
        else:
            header = "💼 <b>NUEVA OPERACIÓN</b>"
        message = f"{header}\n\n"
        message += f"<b>Par:</b> {signal.symbol}\n"
        message += f"<b>Timeframe:</b> {signal.timeframe}\n"
        message += f"{signal_emoji} <b>Tipo:</b> {signal.signal_type}\n"
        message += f"🎯 <b>Entrada:</b> {signal.entry_price:.5f}\n"
        message += f"🚫 <b>SL:</b> {signal.stop_loss:.5f}\n"
        message += f"✅ <b>TP:</b> {signal.take_profit:.5f}\n"
        message += f"⚖️ <b>R:R:</b> 1:{rr_ratio:.2f}\n"
        message += f"🔥 <b>Confianza:</b> {signal.confidence*100:.1f}%\n"
        message += f"📊 <b>Estrategia:</b> {', '.join(signal.reasons)}\n"
        message += f"⏰ <b>Hora:</b> {signal.timestamp.strftime('%H:%M UTC')}\n"
        
        return message

    def _categorize_by_symbol_name(self, symbol: str) -> str:
        """
        Categoriza un instrumento basado solo en el nombre del símbolo.
        Versión simplificada para Telegram Alerts.
        """
        if not symbol:
            return "unknown"
        symbol_upper = symbol.upper()
        # FOREX
        forex_currencies = [
            'USD', 'EUR', 'JPY', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF',
            'CNY', 'MXN', 'SEK', 'NOK', 'DKK', 'HKD', 'SGD', 'TRY',
            'ZAR', 'BRL', 'PLN', 'RUB', 'INR', 'THB'
        ]
        if len(symbol_upper) <= 8:
            currencies_present = sum(1 for curr in forex_currencies if curr in symbol_upper)
            if currencies_present >= 2:
                return "forex"
            if any(sep in symbol_upper for sep in ['/', '.', '_']) and currencies_present >= 1:
                return "forex"
        # Metales
        metal_patterns = [
            'XAU', 'GOLD', 'XAG', 'SILVER', 'PLAT', 'PLATINUM',
            'COPPER', 'PALLADIUM', 'XPD', 'XPT', 'XAUUSD', 'XAGUSD'
        ]
        if any(pattern in symbol_upper for pattern in metal_patterns):
            return "metal"
        # Índices
        index_patterns = [
            'US30', 'DOW', 'SPX', 'SP500', 'S&P', 'NAS100', 'NASDAQ', 'NDX',
            'DAX', 'UK100', 'FTSE', 'CAC', 'IBEX', 'N225', 'HSI', 'ASX',
            'STOXX', 'EURO50', 'RUSSELL', 'VIX'
        ]
        if any(pattern in symbol_upper for pattern in index_patterns):
            return "index"
        # Cripto
        crypto_patterns = [
            'BTC', 'ETH', 'LTC', 'XRP', 'DOGE', 'BCH', 'BNB', 'USDT',
            'ADA', 'DOT', 'LINK', 'SOL', 'MATIC', 'AVAX', 'XLM', 'UNI',
            'BITCOIN', 'ETHEREUM'
        ]
        if any(pattern in symbol_upper for pattern in crypto_patterns):
            return "crypto"
        return "other"
    
    def _format_execution_message(self, signal: TradingSignal, ticket: int, 
                                 execution_price: float, volume: float) -> str:
        """
        Format execution message
        
        Args:
            signal: TradingSignal object
            ticket: Order ticket
            execution_price: Execution price
            volume: Order volume
            
        Returns:
            Formatted message string
        """
        signal_emoji = "✅" if signal.signal_type == "BUY" else "✅"
        
        message = f"{signal_emoji} <b>ORDEN EJECUTADA</b>\n\n"
        message += f"<b>Ticket:</b> #{ticket}\n"
        message += f"<b>Par:</b> {signal.symbol}\n"
        message += f"<b>Tipo:</b> {signal.signal_type}\n"
        message += f"<b>Volumen:</b> {volume:.2f} lotes\n"
        message += f"<b>Precio Ejecutado:</b> {execution_price:.5f}\n"
        message += f"<b>Slippage:</b> {abs(execution_price - signal.entry_price):.5f}\n"
        message += f"<b>Hora:</b> {datetime.now().strftime('%H:%M UTC')}\n"
        
        return message
    
    def _format_close_message(self, symbol: str, ticket: int, close_price: float, 
                             profit: float, reason: str) -> str:
        """
        Format close message
        
        Args:
            symbol: Trading symbol
            ticket: Order ticket
            close_price: Close price
            profit: Profit/Loss
            reason: Close reason
            
        Returns:
            Formatted message string
        """
        profit_emoji = "💰" if profit > 0 else "💔"
        
        message = f"{profit_emoji} <b>POSICIÓN CERRADA</b>\n\n"
        message += f"<b>Ticket:</b> #{ticket}\n"
        message += f"<b>Par:</b> {symbol}\n"
        message += f"<b>Precio Cierre:</b> {close_price:.5f}\n"
        message += f"<b>Resultado:</b> ${profit:.2f}\n"
        message += f"<b>Motivo:</b> {reason}\n"
        message += f"<b>Hora:</b> {datetime.now().strftime('%H:%M UTC')}\n"
        
        return message
    
    def _format_daily_summary(self, daily_stats: Dict) -> str:
        """
        Format daily summary message
        
        Args:
            daily_stats: Daily statistics dictionary
            
        Returns:
            Formatted message string
        """
        total_pnl = daily_stats.get('total_pnl', 0)
        total_trades = daily_stats.get('total_trades', 0)
        winning_trades = daily_stats.get('winning_trades', 0)
        losing_trades = daily_stats.get('losing_trades', 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        summary_emoji = "📊"
        
        message = f"{summary_emoji} <b>RESUMEN DIARIO</b>\n\n"
        message += f"<b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d')}\n"
        message += f"<b>Total Operaciones:</b> {total_trades}\n"
        message += f"<b>Operaciones Ganadoras:</b> {winning_trades}\n"
        message += f"<b>Operaciones Perdedoras:</b> {losing_trades}\n"
        message += f"<b>Tasa de Éxito:</b> {win_rate:.1f}%\n"
        message += f"<b>P&L Total:</b> ${total_pnl:.2f}\n"
        message += f"<b>Balance de Cuenta:</b> ${daily_stats.get('account_balance', 0):.2f}\n"
        
        return message
    
    def test_connection(self) -> bool:
        """
        Test Telegram bot connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test bot connection
            bot_info = self.bot.get_me()
            logger.info(f"Bot connected: {bot_info.username}")
            
            # Test sending message to all chat IDs
            test_message = "🧪 <b>Test Message</b>\n\nMr.Cashondo Bot connection test successful!"
            
            for chat_id in self.chat_ids:
                try:
                    self.bot.send_message(
                        chat_id=chat_id,
                        text=test_message,
                        parse_mode='HTML'
                    )
                    logger.info(f"Test message sent to chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send test message to chat {chat_id}: {str(e)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Telegram connection test failed: {str(e)}")
            return False
    
    def send_warning(self, message: str) -> bool:
        """
        (Deshabilitado) No enviar advertencias a Telegram.
        """
        logger.info("[Telegram] Advertencia suprimida (no se envía a Telegram)")
        return True
