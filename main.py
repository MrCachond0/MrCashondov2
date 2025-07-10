"""
Main Trading Bot Module - Mr.Cashondo
Automated FOREX trading bot with scalping and day trading strategies
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule
import os
from dotenv import load_dotenv

# Import custom modules
from mt5_connector import MT5Connector, OrderRequest
from signal_generator import SignalGenerator, TradingSignal
from risk_manager import RiskManager, RiskParameters
from telegram_alerts import TelegramAlerts

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para ver más detalles
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mr_cashondo_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MrCashondoBot:
    def send_daily_summary(self):
        """
        Envía el resumen diario de operaciones a Telegram usando los datos del risk_manager.
        """
        if self.risk_manager and self.telegram_alerts:
            daily_stats = self.risk_manager.get_risk_summary()
            self.telegram_alerts.send_daily_summary(daily_stats)
        else:
            logger.warning("No se pudo enviar el resumen diario: risk_manager o telegram_alerts no inicializados.")

    def reset_daily_stats(self):
        """
        Resetea las estadísticas diarias de riesgo (P&L, trades, etc).
        """
        if self.risk_manager:
            self.risk_manager.reset_daily_stats()
            logger.info("Estadísticas diarias reseteadas correctamente.")
        else:
            logger.warning("No se pudo resetear estadísticas diarias: risk_manager no inicializado.")
    """
    Main trading bot class
    """
    def __init__(self):
        """Initialize the trading bot"""
        self.mt5_connector = None
        self.signal_generator = None
        self.risk_manager = None
        self.telegram_alerts = None
        self.running = False
        self.start_time = datetime.now()
        self.active_positions = {}  # Track active positions
        self.last_scan_time = datetime.now()
        # --- INTEGRACIÓN BASE DE DATOS ---
        from trade_database import TradeDatabase
        self.trade_db = TradeDatabase()
        # Trading parameters
        self.scan_interval = 30  # seconds
        self.timeframes = ["M5", "M15"]  # Trading timeframes
        self.max_slippage = 5  # pips
        logger.info("Mr.Cashondo Bot initialized")
        self._subscription_validated = False

    def validate_subscription(self):
        """
        Solicita email y token de suscripción solo una vez por ejecución y valida contra Supabase.
        """
        if self._subscription_validated:
            return True
        email = os.getenv("USER_EMAIL")
        token = os.getenv("USER_TOKEN")
        if not email:
            email = input("Introduce tu email de suscripción: ").strip()
            os.environ["USER_EMAIL"] = email
        if not token:
            token = input("Introduce tu Token de suscripción: ").strip()
            os.environ["USER_TOKEN"] = token
        # Validar suscripción vía API
        try:
            import requests
            SUPABASE_URL = os.getenv("SUPABASE_URL")
            SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
            if not SUPABASE_URL or not SUPABASE_API_KEY:
                print("❌ Faltan variables SUPABASE_URL o SUPABASE_API_KEY en .env")
                logger.error("Faltan variables SUPABASE_URL o SUPABASE_API_KEY en .env")
                return False
            url = f"{SUPABASE_URL}/rest/v1/subscriptions?email=eq.{email}&select=active,expires_at"
            headers = {
                "apikey": SUPABASE_API_KEY,
                "Authorization": f"Bearer {SUPABASE_API_KEY}"
            }
            resp = requests.get(url, headers=headers)
            data = resp.json()
            if data and data[0].get("active", False):
                print("✅ Suscripción activa. Iniciando bot...")
                logger.info(f"Suscripción validada correctamente para {email}")
                self._subscription_validated = True
                return True
            else:
                print("❌ Suscripción inactiva, expirada o Token incorrecto. Contacta soporte.")
                logger.error(f"Suscripción inactiva o Token incorrecto para {email}")
                return False
        except Exception as e:
            print(f"❌ Error crítico validando suscripción: {e}")
            logger.error(f"Error crítico validando suscripción: {e}")
            return False
    
    def initialize_components(self) -> bool:
        """
        Initialize all bot components
        
        Returns:
            True if all components initialized successfully
        """
        try:
            # Initialize MT5 connector
            logger.info("Initializing MT5 connector...")
            self.mt5_connector = MT5Connector()
            if not self.mt5_connector.connect():
                logger.error("Failed to connect to MT5")
                return False
            
            # Initialize signal generator
            logger.info("Initializing signal generator...")
            self.signal_generator = SignalGenerator()
            # Forzar configuración: SOLO FOREX, ÍNDICES Y METALES
            self.signal_generator.configure_instrument_types(
                forex=True, indices=True, metals=True, stocks=False, crypto=False, etfs=False
            )
            
            # Initialize symbols dynamically from MT5
            logger.info("Initializing symbols dynamically...")
            if not self.signal_generator.initialize_symbols(self.mt5_connector):
                logger.error("Failed to initialize symbols")
                return False
            
            # Initialize risk manager
            logger.info("Initializing risk manager...")
            risk_params = RiskParameters(
                max_risk_per_trade=0.01,  # 1% risk per trade
                max_daily_loss=0.05,      # 5% daily loss limit
                max_open_positions=3,     # Maximum 3 open positions
                min_risk_reward_ratio=1.5 # Minimum 1:1.5 risk-reward
            )
            self.risk_manager = RiskManager(risk_params)
            
            # Initialize Telegram alerts
            logger.info("Initializing Telegram alerts...")
            self.telegram_alerts = TelegramAlerts()
            
            # Test Telegram connection
            if not self.telegram_alerts.test_connection():
                logger.error("Failed to connect to Telegram")
                return False
            
            # Send startup message
            self.telegram_alerts.send_bot_status(
                status="🟢 INICIADO",
                uptime="0:00:00",
                balance=self.mt5_connector.get_account_balance()
            )
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            return False
    
    def start_trading(self) -> None:
        """Start the trading bot with a fixed 15-minute scan interval for all symbols, sin rotación, escaneando todos los símbolos cada ciclo."""
        try:
            if not self.initialize_components():
                logger.error("Failed to initialize components")
                return
            self.running = True
            logger.info("Mr.Cashondo Bot started successfully")

            # Schedule daily summary
            schedule.every().day.at("23:59").do(self.send_daily_summary)
            # Schedule daily reset
            schedule.every().day.at("00:00").do(self.reset_daily_stats)

            # Ejecutar el primer escaneo inmediatamente
            logger.info("Executing initial scan...")
            self.scan_and_execute()
            self.monitor_positions()
            self.last_scan_time = datetime.now()
            logger.info("Initial scan completed")

            # Main trading loop: escanea TODOS los símbolos cada 15 minutos
            scan_interval_minutes = 15
            while self.running:
                try:
                    schedule.run_pending()
                    current_time = datetime.now()
                    time_since_last_scan = (current_time - self.last_scan_time).total_seconds() / 60
                    # Log para confirmar que el bot está activo
                    if int(time_since_last_scan) % 1 == 0 and time_since_last_scan < scan_interval_minutes:
                        logger.debug(f"Bot active, waiting for scan ({time_since_last_scan:.1f}/{scan_interval_minutes} minutes passed)")
                    # Ejecutar scan si han pasado 15 minutos desde el último
                    if time_since_last_scan >= scan_interval_minutes:
                        logger.info(f"Scan interval reached ({time_since_last_scan:.1f} minutes). Starting scan...")
                        self.scan_and_execute()
                        self.monitor_positions()
                        self.last_scan_time = datetime.now()
                    time.sleep(5)
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt, stopping bot...")
                    self.stop_trading()
                    break
                except Exception as e:
                    logger.error(f"Error in main trading loop: {str(e)}")
                    self.telegram_alerts.send_error_alert(str(e), "Main trading loop")
                    time.sleep(60)
        except Exception as e:
            logger.error(f"Critical error in start_trading: {str(e)}")
            self.telegram_alerts.send_error_alert(str(e), "Critical error")
    
    def scan_and_execute(self) -> None:
        """Scan for signals and execute trades"""
        try:
            logger.info("Scanning for trading signals...")

            # Limpiar señales generadas del ciclo anterior para evitar duplicados
            if hasattr(self.signal_generator, 'generated_signals'):
                self.signal_generator.generated_signals.clear()

            # Get signals from signal generator
            signals = self.signal_generator.scan_all_symbols(self.mt5_connector, self.timeframes)

            if not signals:
                logger.info("No trading signals found in this scan")
                return

            logger.info(f"Found {len(signals)} trading signals")

            # Process each signal
            for signal in signals:
                self.process_signal(signal)

            self.last_scan_time = datetime.now()

        except Exception as e:
            logger.error(f"Error in scan_and_execute: {str(e)}")
    
    def process_signal(self, signal: TradingSignal) -> None:
        """
        Procesar señal de trading:
        - Registrar señal en base de datos
        - Enviar SIEMPRE a Telegram
        - Ejecutar solo si hay fondos y exposición suficiente
        - Registrar trade en base de datos (incluyendo parámetros usados)
        """
        try:
            # FILTRO DE TIPO DE SÍMBOLO: solo operar FOREX, índices y commodities/metales
            if not self.signal_generator._is_symbol_type_enabled(signal.symbol):
                logger.warning(f"[SYMBOL FILTER] Señal descartada por tipo de símbolo no permitido: {signal.symbol}")
                self.telegram_alerts.send_signal_alert(signal)
                self.trade_db.update_signal_status(getattr(signal, 'id', None), "symbol_type_not_allowed")
                return
            # FILTRO DE CONFIANZA: solo procesar señales con confianza >= 0.7 (ajustado 10/07/2025)
            if hasattr(signal, 'confidence') and signal.confidence < 0.7:
                logger.info(f"Señal descartada por confianza insuficiente: {getattr(signal, 'confidence', None):.2f} < 0.70 para {signal.symbol}")
                return

            # --- REGISTRO DE SEÑAL EN BASE DE DATOS ---
            signal_dict = {
                'symbol': signal.symbol,
                'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                'signal_type': signal.signal_type,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'confidence': getattr(signal, 'confidence', 0.0),
                'timestamp': getattr(signal, 'timestamp', datetime.utcnow().isoformat()),
            }
            signal_id = self.trade_db.log_signal(signal_dict)

            # 1. Validar stops antes de procesar la señal
            order_type = 0 if signal.signal_type == "BUY" else 1  # Convertir a tipo MT5
            sl, tp, stops_valid = self.mt5_connector.validate_and_adjust_stops(
                signal.symbol, order_type, signal.entry_price, signal.stop_loss, signal.take_profit
            )
            if not stops_valid:
                logger.warning(f"Señal descartada para {signal.symbol}: Stops inválidos")
                # AUN ASÍ enviar la señal a Telegram para monitoreo manual
                self.telegram_alerts.send_signal_alert(signal)
                # Actualizar estado en base de datos
                self.trade_db.update_signal_status(signal_id, "invalid_stops")
                return
            # Actualizar la señal con stops válidos
            signal.stop_loss = sl
            signal.take_profit = tp
            # Obtener symbol_info antes de calcular el tamaño de la posición
            symbol_info = self.mt5_connector.get_symbol_info(signal.symbol)
            if not symbol_info:
                logger.error(f"No se pudo obtener información del símbolo {signal.symbol}")
                self.telegram_alerts.send_signal_alert(signal)
                self.trade_db.update_signal_status(signal_id, "no_symbol_info")
                return
            # 2. Calcular volumen basado en gestión de riesgo configurable (fixed_usd o percent_margin)
            from risk_config import RISK_MODE, FIXED_RISK_USD
            account_info = self.mt5_connector.get_account_info()
            free_margin = account_info.get('margin_free', 0)
            balance = account_info.get('balance', 0)
            position_size = None
            if RISK_MODE == "fixed_usd":
                position_size = self.risk_manager.calculate_position_size_fixed_usd(
                    signal.symbol,
                    signal.entry_price,
                    signal.stop_loss,
                    symbol_info,
                    FIXED_RISK_USD
                )
                logger.info(f"[RISK] Modo FIXED_USD: arriesgando {FIXED_RISK_USD} USD por operación para {signal.symbol}")
            else:
                # Usar el mayor entre 1% de free_margin y 1% de balance como monto de riesgo
                risk_amount = max(
                    self.risk_manager.calculate_risk_amount(free_margin, 0.01),
                    self.risk_manager.calculate_risk_amount(balance, 0.01)
                )
                position_size = self.risk_manager.calculate_position_size(
                    signal.symbol,
                    signal.entry_price,
                    signal.stop_loss,
                    risk_amount,  # Usar risk_amount como balance para forzar el 1% real
                    symbol_info,
                    free_margin=free_margin,
                    take_profit=signal.take_profit,
                    signal_type=signal.signal_type
                )
                logger.info(f"[RISK] Modo percent_margin: arriesgando {risk_amount} USD para {signal.symbol}")
            # Si el cálculo falla, fallback a mínimo volumen permitido
            if position_size is None or getattr(position_size, 'volume', None) is None or position_size.volume <= 0:
                logger.warning(f"Fallo el cálculo de tamaño de posición para {signal.symbol}, usando mínimo permitido")
                min_vol = symbol_info.get('min_volume', 0.01)
                position_size = type('PositionSize', (), {'volume': min_vol})

            # 3. Enviar SIEMPRE la señal a Telegram (independiente de fondos/exposición)
            self.telegram_alerts.send_signal_alert(signal)

            # 4. Intentar ejecutar la orden SOLO si hay fondos y exposición suficiente, pero corrigiendo el cálculo de volumen y margen
            max_volume = symbol_info.get('max_volume', 100.0)
            min_volume = symbol_info.get('min_volume', 0.01)
            volume_step = symbol_info.get('volume_step', 0.01)
            exposure_limit = self.risk_manager.calculate_dynamic_exposure_limit(free_margin, signal.symbol, {})
            test_volume = min(position_size.volume, max_volume)
            margin_required = self.risk_manager.calculate_margin_buffer(
                test_volume,
                symbol_info.get('contract_size', 100000),
                signal.entry_price,
                symbol_info.get('leverage', 100),
                signal.symbol
            )
            while margin_required > exposure_limit and test_volume > min_volume:
                test_volume = max(test_volume - volume_step, min_volume)
                margin_required = self.risk_manager.calculate_margin_buffer(
                    test_volume,
                    symbol_info.get('contract_size', 100000),
                    signal.entry_price,
                    symbol_info.get('leverage', 100),
                    signal.symbol
                )
            can_execute = test_volume >= min_volume and margin_required <= exposure_limit
            # Ejecutar orden solo si es posible
            if can_execute:
                try:
                    order_request = OrderRequest(
                        symbol=signal.symbol,
                        action=order_type,
                        volume=test_volume,
                        price=signal.entry_price,
                        sl=signal.stop_loss,
                        tp=signal.take_profit,
                        comment="MrcashondoV2"
                    )
                    result = self.mt5_connector.send_order(order_request)
                    if result and result.get('retcode', 0) == 10009:
                        logger.info(f"Orden ejecutada correctamente para {signal.symbol}")
                        # --- REGISTRO DE TRADE EN BASE DE DATOS ---
                        trade_dict = {
                            'signal_id': signal_id,
                            'order_id': result.get('order', None),
                            'symbol': signal.symbol,
                            'action': signal.signal_type,
                            'volume': test_volume,
                            'price': signal.entry_price,
                            'sl': signal.stop_loss,
                            'tp': signal.take_profit,
                            'comment': "MrcashondoV2",
                            'open_time': datetime.utcnow().isoformat(),
                            'close_time': None,
                            'close_price': None,
                            'profit': None,
                            'status': 'open',
                            # --- PARÁMETROS USADOS ---
                            # Puedes agregar aquí más parámetros relevantes para ML
                        }
                        self.trade_db.log_trade(trade_dict)
                        self.trade_db.update_signal_status(signal_id, "executed")
                    else:
                        logger.warning(f"No se pudo ejecutar la orden para {signal.symbol}: {result}")
                        self.trade_db.update_signal_status(signal_id, "not_executed")
                except Exception as e:
                    logger.error(f"Error ejecutando orden para {signal.symbol}: {e}")
                    self.trade_db.update_signal_status(signal_id, "error")
            else:
                logger.info(f"Señal para {signal.symbol} NO ejecutada en MT5 por fondos/exposición, pero enviada a Telegram")
                self.trade_db.update_signal_status(signal_id, "not_executed")
        except Exception as e:
            logger.error(f"Error en process_signal: {str(e)}")
    
    def execute_trade(self, signal: TradingSignal, volume: float) -> None:
        """
        Execute a trade based on signal
        
        Args:
            signal: TradingSignal object
            volume: Position volume
        """
        try:
            # Get dynamic trading parameters for the symbol
            trading_params = self.mt5_connector.get_dynamic_trading_params(signal.symbol)
            if not trading_params:
                logger.error(f"Cannot get trading parameters for {signal.symbol}")
                return
            
            # Get current price for market order
            current_price = self.mt5_connector.get_current_price(signal.symbol)
            if not current_price:
                logger.error(f"Cannot get current price for {signal.symbol}")
                return
            
            # Determine order type and price
            if signal.signal_type == "BUY":
                order_type = 0  # mt5.ORDER_TYPE_BUY
                execution_price = current_price[1]  # Ask price
            else:  # SELL
                order_type = 1  # mt5.ORDER_TYPE_SELL
                execution_price = current_price[0]  # Bid price
            
            # Use dynamic filling mode from symbol specifications
            # filling_mode eliminado: la lógica de filling_mode se gestiona internamente en mt5_connector
            
            # Create order request with dynamic parameters
            order_request = OrderRequest(
                symbol=signal.symbol,
                action=order_type,
                volume=volume,
                price=execution_price,
                sl=signal.stop_loss,
                tp=signal.take_profit,
                comment="MrcashondoV2"
            )
            
            # Send order
            result = self.mt5_connector.send_order(order_request)
            
            if result:
                logger.info(f"Order executed successfully: Ticket {result['ticket']}")
                
                # Update risk manager
                self.risk_manager.increment_positions()
                
                # Store position info
                self.active_positions[result['ticket']] = {
                    'signal': signal,
                    'volume': volume,
                    'execution_price': result['price'],
                    'open_time': datetime.now()
                }
                
                # Send execution alert
                self.telegram_alerts.send_execution_alert(
                    signal, result['ticket'], result['price'], volume
                )
                
            else:
                logger.error("Order execution failed")
                self.telegram_alerts.send_error_alert(
                    f"Order execution failed for {signal.symbol}", "Order execution"
                )
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
    
    def monitor_positions(self) -> None:
        """Monitor existing positions for management"""
        try:
            # Get current positions from MT5
            current_positions = self.mt5_connector.get_positions()
            
            if not current_positions:
                # No positions, clear active positions
                self.active_positions.clear()
                self.risk_manager.positions_count = 0
                return
            
            # Check each position
            for position in current_positions:
                ticket = position['ticket']
                
                if ticket in self.active_positions:
                    self.monitor_position(position)
                else:
                    # Position not in our tracking, add it with placeholder data
                    # Limitamos el logging de posiciones no rastreadas solo a nuevas en esta ejecución
                    if not hasattr(self, 'known_untracked_positions'):
                        self.known_untracked_positions = set()
                        
                    if ticket not in self.known_untracked_positions:
                        logger.info(f"Found untracked position: {ticket}")
                        self.known_untracked_positions.add(ticket)
                        
                    symbol = position.get('symbol', 'unknown')
                    
                    # Crear señal con timestamp actual
                    self.active_positions[ticket] = {
                        'signal': TradingSignal(
                            symbol=symbol,
                            signal_type="BUY" if position.get('type') == 0 else "SELL",
                            entry_price=position.get('price_open', 0.0),
                            stop_loss=position.get('sl', 0.0),
                            take_profit=position.get('tp', 0.0),
                            timeframe="UNKNOWN",
                            confidence=0.0,
                            reasons=["Existing position"],
                            atr_value=0.0,
                            timestamp=datetime.now()  # Añadir timestamp requerido
                        ),
                        'volume': position.get('volume', 0.0),
                        'execution_price': position.get('price_open', 0.0),
                        'open_time': datetime.now() - timedelta(days=1)  # Asumir que es de ayer
                    }
            
            # Remove closed positions from tracking
            current_tickets = [pos['ticket'] for pos in current_positions]
            for ticket in list(self.active_positions.keys()):
                if ticket not in current_tickets:
                    logger.info(f"Position {ticket} closed")
                    del self.active_positions[ticket]
                    self.risk_manager.decrement_positions()
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {str(e)}")
    
    def monitor_position(self, position: Dict) -> None:
        """
        Monitor individual position
        
        Args:
            position: Position information from MT5
        """
        try:
            ticket = position['ticket']
            symbol = position['symbol']
            current_price = position['price_current']
            
            if ticket not in self.active_positions:
                return
            
            signal = self.active_positions[ticket]['signal']
            
            # Check for breakeven move
            if self.risk_manager.should_move_to_breakeven(
                signal.signal_type, signal.entry_price, current_price, signal.atr_value
            ):
                # Move to breakeven
                new_sl = signal.entry_price
                if self.mt5_connector.modify_position(ticket, new_sl, position['tp']):
                    logger.info(f"Position {ticket} moved to breakeven")
            
            # Check for trailing stop
            new_trailing_sl = self.risk_manager.calculate_trailing_stop(
                signal.signal_type, signal.entry_price, current_price, signal.atr_value
            )
            
            if new_trailing_sl:
                current_sl = position['sl']
                should_update = False
                
                if signal.signal_type == "BUY" and new_trailing_sl > current_sl:
                    should_update = True
                elif signal.signal_type == "SELL" and new_trailing_sl < current_sl:
                    should_update = True
                
                if should_update:
                    if self.mt5_connector.modify_position(ticket, new_trailing_sl, position['tp']):
                        logger.info(f"Position {ticket} trailing stop updated to {new_trailing_sl}")
            
        except Exception as e:
            logger.error(f"Error monitoring position {ticket}: {str(e)}")
    
    def start_trading(self) -> None:
        """Start the trading bot with a fixed 15-minute scan interval for all symbols, sin rotación, escaneando todos los símbolos cada ciclo."""
        try:
            # Validar suscripción SOLO UNA VEZ antes de iniciar el bot
            if not self.validate_subscription():
                logger.error("No se pudo validar la suscripción. El bot no se iniciará.")
                return
            if not self.initialize_components():
                logger.error("Failed to initialize components")
                return
            self.running = True
            logger.info("Mr.Cashondo Bot started successfully")

            # Schedule daily summary
            schedule.every().day.at("23:59").do(self.send_daily_summary)
            # Schedule daily reset
            schedule.every().day.at("00:00").do(self.reset_daily_stats)

            # Ejecutar el primer escaneo inmediatamente
            logger.info("Executing initial scan...")
            self.scan_and_execute()
            self.monitor_positions()
            self.last_scan_time = datetime.now()
            logger.info("Initial scan completed")

            # Main trading loop: escanea TODOS los símbolos cada 15 minutos
            scan_interval_minutes = 15
            while self.running:
                try:
                    schedule.run_pending()
                    current_time = datetime.now()
                    time_since_last_scan = (current_time - self.last_scan_time).total_seconds() / 60
                    # Log para confirmar que el bot está activo
                    if int(time_since_last_scan) % 1 == 0 and time_since_last_scan < scan_interval_minutes:
                        logger.debug(f"Bot active, waiting for scan ({time_since_last_scan:.1f}/{scan_interval_minutes} minutes passed)")
                    # Ejecutar scan si han pasado 15 minutos desde el último
                    if time_since_last_scan >= scan_interval_minutes:
                        self.scan_and_execute()
                        self.monitor_positions()
                        self.last_scan_time = datetime.now()
                    time.sleep(5)
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt, stopping bot...")
                    self.stop_trading()
                    break
                except Exception as e:
                    logger.error(f"Error in main trading loop: {str(e)}")
                    self.telegram_alerts.send_error_alert(str(e), "Main trading loop")
                    time.sleep(60)
        except Exception as e:
            logger.error(f"Critical error in start_trading: {str(e)}")
            self.telegram_alerts.send_error_alert(str(e), "Critical error")
            
            # Disconnect from MT5
            if self.mt5_connector:
                self.mt5_connector.disconnect()
            
            logger.info("Mr.Cashondo Bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
    
    def get_bot_status(self) -> Dict:
        """
        Get current bot status
        
        Returns:
            Dictionary with bot status information
        """
        uptime = datetime.now() - self.start_time
        
        return {
            'running': self.running,
            'uptime': str(uptime),
            'last_scan': self.last_scan_time,
            'active_positions': len(self.active_positions),
            'account_balance': self.mt5_connector.get_account_balance() if self.mt5_connector else 0,
            'risk_stats': self.risk_manager.get_risk_summary() if self.risk_manager else {}
        }

def main():
    """Main function to run the bot"""
    try:
        logger.info("Starting Mr.Cashondo Trading Bot...")
        
        # Create and start bot
        bot = MrCashondoBot()
        bot.start_trading()
        
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}")
    finally:
        logger.info("Bot execution completed")

if __name__ == "__main__":
    main()
