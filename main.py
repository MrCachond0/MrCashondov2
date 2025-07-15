
"""
Main Trading Bot Module - Mr.Cashondo
Automated FOREX trading bot with scalping and day trading strategies
"""

# === IMPORTS NECESARIOS ===
import os

# === AUTO UPDATE SYSTEM ===
import subprocess
import sys
import requests
import shutil

GITHUB_REPO = "MrCachond0/MrCashondov2"
BRANCH = "main"
LOCAL_VERSION_FILE = "version.txt"
REMOTE_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/version.txt"

def get_local_version():
    if not os.path.exists(LOCAL_VERSION_FILE):
        return "0.0.0"
    with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def get_remote_version():
    try:
        r = requests.get(REMOTE_VERSION_URL, timeout=10)
        if r.status_code == 200:
            return r.text.strip()
    except Exception:
        pass
    return None

def auto_update():
    local_version = get_local_version()
    remote_version = get_remote_version()
    if remote_version and remote_version != local_version:
        print(f"\n[AutoUpdate] Nueva versión disponible: {remote_version} (actual: {local_version})")
        print("Descargando y aplicando actualización desde GitHub...")
        # Descargar ZIP del repo
        zip_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/{BRANCH}.zip"
        zip_path = "update.zip"
        try:
            with requests.get(zip_url, stream=True, timeout=30) as r:
                with open(zip_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)
            # Extraer y sobreescribir archivos
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("update_tmp")
            update_dir = os.path.join("update_tmp", f"MrCashondov2-{BRANCH}")
            # Copiar archivos nuevos (excepto .env, .env.user, .env.enc, .env.key, logs, trades.db)
            exclude = {".env", ".env.user", ".env.enc", ".env.key", "mr_cashondo_bot.log", "trades.db", "logs"}
            for root, dirs, files in os.walk(update_dir):
                rel_dir = os.path.relpath(root, update_dir)
                for file in files:
                    if file in exclude:
                        continue
                    src = os.path.join(root, file)
                    dst = os.path.join(os.getcwd(), rel_dir, file) if rel_dir != "." else os.path.join(os.getcwd(), file)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
            # Actualizar version.txt
            with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(remote_version)
            print("Actualización aplicada. Reiniciando bot...")
            # Limpiar archivos temporales
            shutil.rmtree("update_tmp", ignore_errors=True)
            os.remove(zip_path)
            # Reiniciar el script
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"[AutoUpdate] Error durante la actualización: {e}")
            print("Continúa con la versión actual.")

# Ejecutar auto-update antes de cualquier otra cosa
auto_update()
import time
import logging
from datetime import datetime, timedelta, timezone
import os
import schedule
from dotenv import load_dotenv
from env_loader import load_env
load_env()
from subscription_api import validate_subscription
from typing import Dict, List, Optional

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

import threading
import getpass

class MrCashondoBot:
    def process_signal(self, signal: TradingSignal) -> None:
        """
        Procesa una señal de trading: registra, filtra duplicados, ajusta trailing y ejecuta si corresponde.
        Args:
            signal: Objeto TradingSignal generado por el SignalGenerator
        """
        # --- FILTRO DE DUPLICIDAD ---
        duplicate = None
        if self.trade_db:
            duplicate = self.trade_db.find_duplicate_signal(
                symbol=signal.symbol,
                timeframe=getattr(signal, 'timeframe', 'UNKNOWN'),
                signal_type=signal.signal_type,
                window_minutes=60
            )
        if duplicate:
            # Comprobar si hay cambios relevantes en SL, TP, entry
            diff_entry = abs(signal.entry_price - duplicate.get('entry_price', 0)) > 0.0005 * signal.entry_price
            diff_sl = abs(signal.stop_loss - duplicate.get('stop_loss', 0)) > 0.0005 * signal.entry_price
            diff_tp = abs(signal.take_profit - duplicate.get('take_profit', 0)) > 0.0005 * signal.entry_price
            if diff_sl or diff_tp:
                # Sugerir actualización de trailing o parámetros
                logger.info(f"[DUPLICATE][TRAILING] Señal duplicada detectada, pero SL/TP cambiaron. Sugerir actualización de trailing o parámetros para la señal original (ID {duplicate['id']}).")
                # Aquí podrías actualizar la señal original en la base de datos si lo deseas:
                # self.trade_db.update_signal_params(duplicate['id'], {'stop_loss': signal.stop_loss, 'take_profit': signal.take_profit})
                # Por ahora, solo logueamos y descartamos la nueva señal
                return
            else:
                logger.info(f"[DUPLICATE][DISCARDED] Señal duplicada detectada para {signal.symbol} {signal.signal_type} en {getattr(signal, 'timeframe', 'UNKNOWN')}. Se descarta la nueva señal y se mantiene la original (ID {duplicate['id']}).")
                return
        try:
            # FILTRO DE TIPO DE SÍMBOLO: solo operar FOREX, índices y commodities/metales
            if not self.signal_generator._is_symbol_type_enabled(signal.symbol):
                logger.warning(f"[SYMBOL FILTER][REJECTED] Señal descartada por tipo de símbolo no permitido: {signal.symbol}")
                if self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'rejected',
                        'generation_params': None
                    }, generation_params={'reason': 'symbol_type_not_allowed'})
                return

            # FILTRO DE CONFIANZA: solo procesar señales con confianza >= 0.8
            if hasattr(signal, 'confidence') and signal.confidence < 0.8:
                logger.info(f"[CONFIDENCE][REJECTED] Señal descartada por confianza insuficiente: {getattr(signal, 'confidence', None):.2f} < 0.80 para {signal.symbol}")
                if self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'rejected',
                        'generation_params': None
                    }, generation_params={'reason': 'confidence_below_threshold'})
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
                'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
            }
            signal_id = None
            if self.trade_db:
                try:
                    signal_id = self.trade_db.log_signal(signal_dict)
                    logger.info(f"[DB] Señal registrada en base de datos con ID {signal_id}")
                except Exception as e:
                    logger.error(f"[DB] Error al registrar señal: {e}")
                    signal_id = None

            # 1. Validar stops antes de procesar la señal
            order_type = 0 if signal.signal_type == "BUY" else 1  # Convertir a tipo MT5
            sl, tp, stops_valid = self.mt5_connector.validate_and_adjust_stops(
                signal.symbol, order_type, signal.entry_price, signal.stop_loss, signal.take_profit
            )
            if not stops_valid:
                logger.warning(f"[STOPS][REJECTED] Señal descartada para {signal.symbol}: Stops inválidos")
                if self.trade_db and signal_id:
                    self.trade_db.update_signal_status(signal_id, "invalid_stops")
                elif self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'invalid_stops',
                        'generation_params': None
                    }, generation_params={'reason': 'invalid_stops'})
                return
            logger.info(f"[RISK] Stops validados para {signal.symbol}: SL={sl}, TP={tp}")
            # Actualizar la señal con stops válidos
            signal.stop_loss = sl
            signal.take_profit = tp
            # Obtener symbol_info antes de calcular el tamaño de la posición
            symbol_info = self.mt5_connector.get_symbol_info(signal.symbol)
            if not symbol_info:
                logger.error(f"[MT5][ERROR] No se pudo obtener información del símbolo {signal.symbol}")
                if self.trade_db and signal_id:
                    self.trade_db.update_signal_status(signal_id, "no_symbol_info")
                elif self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'no_symbol_info',
                        'generation_params': None
                    }, generation_params={'reason': 'no_symbol_info'})
                return
            logger.info(f"[INFO] symbol_info obtenido para {signal.symbol}: {symbol_info}")
            # 2. Calcular volumen basado en gestión de riesgo configurable (fixed_usd o percent_margin)
            from risk_config import RISK_MODE, FIXED_RISK_USD
            account_info = self.mt5_connector.get_account_info()
            free_margin = account_info.get('margin_free', 0)
            balance = account_info.get('balance', 0)
            position_size = None
            if RISK_MODE == "fixed_usd":
                try:
                    position_size = self.risk_manager.calculate_position_size_fixed_usd(
                        signal.symbol,
                        signal.entry_price,
                        signal.stop_loss,
                        symbol_info,
                        FIXED_RISK_USD
                    )
                    logger.info(f"[RISK] Modo FIXED_USD: arriesgando {FIXED_RISK_USD} USD por operación para {signal.symbol}")
                except Exception as e:
                    logger.error(f"[RISK] Error en cálculo de lotaje FIXED_USD: {e}")
                    position_size = None
            else:
                # Usar el mayor entre 1% de free_margin y 1% de balance como monto de riesgo
                try:
                    risk_amount = max(
                        self.risk_manager.calculate_risk_amount(free_margin, 0.01),
                        self.risk_manager.calculate_risk_amount(balance, 0.01)
                    )
                    position_size = self.risk_manager.calculate_position_size(
                        signal.symbol,
                        signal.entry_price,
                        signal.stop_loss,
                        risk_amount,
                        symbol_info,
                        free_margin=free_margin,
                        take_profit=signal.take_profit,
                        signal_type=signal.signal_type
                    )
                    logger.info(f"[RISK] Modo percent_margin: arriesgando {risk_amount} USD para {signal.symbol}")
                except Exception as e:
                    logger.error(f"[RISK] Error en cálculo de lotaje percent_margin: {e}")
                    position_size = None
            # Si el cálculo falla, fallback a mínimo volumen permitido
            if position_size is None or getattr(position_size, 'volume', None) is None or position_size.volume <= 0:
                logger.warning(f"[POSITION SIZE][ADJUSTED] Fallo el cálculo de tamaño de posición para {signal.symbol}, usando mínimo permitido")
                if self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'adjusted_min_volume',
                        'generation_params': None
                    }, generation_params={'reason': 'position_size_min_volume'})
                min_vol = symbol_info.get('min_volume', 0.01)
                position_size = type('PositionSize', (), {'volume': min_vol})
            logger.info(f"[RISK] Volumen final calculado para {signal.symbol}: {position_size.volume}")

            # 3. Enviar la señal a Telegram (solo si confianza >= 0.8, ya filtrado arriba)
            if self.telegram_alerts:
                self.telegram_alerts.send_signal_alert(signal)

            # 4. Intentar ejecutar la orden SOLO si hay fondos y exposición suficiente, pero corrigiendo el cálculo de volumen y margen
            min_volume = symbol_info.get('min_volume', 0.01)
            test_volume = max(position_size.volume, min_volume)
            margin_required = self.risk_manager.calculate_margin_required(
                signal.symbol, test_volume, signal.entry_price, symbol_info
            )
            exposure_limit = self.risk_manager.get_exposure_limit(symbol_info, account_info)
            logger.info(f"[RISK] margin_required={margin_required}, exposure_limit={exposure_limit}, min_volume={min_volume}")
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
                        if self.trade_db and signal_id:
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
                                'open_time': datetime.now(timezone.utc).isoformat(),
                                'close_time': None,
                                'close_price': None,
                                'profit': None,
                                'status': 'open',
                            }
                            self.trade_db.log_trade(trade_dict)
                            self.trade_db.update_signal_status(signal_id, "executed")
                        logger.info(f"[DB] Trade registrado para {signal.symbol} (order_id={result.get('order', None)})")
                    else:
                        logger.warning(f"No se pudo ejecutar la orden para {signal.symbol}: {result}")
                        if self.trade_db and signal_id:
                            self.trade_db.update_signal_status(signal_id, "not_executed")
                except Exception as e:
                    logger.error(f"Error ejecutando orden para {signal.symbol}: {e}")
                    if self.trade_db and signal_id:
                        self.trade_db.update_signal_status(signal_id, "error")
            else:
                logger.info(f"Señal para {signal.symbol} NO ejecutada en MT5 por fondos/exposición, pero enviada a Telegram")
                if self.trade_db and signal_id:
                    self.trade_db.update_signal_status(signal_id, "not_executed")
            logger.info(f"[RISK] Proceso de ejecución finalizado para {signal.symbol}")
        except Exception as e:
            logger.error(f"Error en process_signal: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    def scan_and_execute(self) -> None:
        """
        Escanea todos los símbolos configurados y ejecuta señales de trading.
        """
        try:
            logger.info("Escaneando señales de trading...")
            if not self.signal_generator or not self.mt5_connector:
                logger.error("Componentes no inicializados para escaneo de señales.")
                return
            signals = self.signal_generator.scan_all_symbols(self.mt5_connector, self.timeframes)
            if not signals:
                logger.info("No se encontraron señales de trading en este escaneo.")
                return
            logger.info(f"Se encontraron {len(signals)} señales de trading.")
            for signal in signals:
                self.process_signal(signal)
            self.last_scan_time = datetime.now()
        except Exception as e:
            logger.error(f"Error en scan_and_execute: {str(e)}")

    def monitor_positions(self) -> None:
        """
        Monitorea y gestiona las posiciones abiertas en MT5.
        """
        try:
            if not self.mt5_connector:
                logger.warning("MT5Connector no inicializado para monitoreo de posiciones.")
                return
            # Gestión activa de posiciones: trailing stop y cierre parcial
            for pos in self.open_positions:
                # Se asume que cada 'pos' es un dict u objeto con los siguientes atributos:
                # position_id, entry_price, stop_loss, take_profit, current_price, signal_type, volume, close_prices, atr
                try:
                    self.risk_manager.manage_partial_and_trailing(
                        pos['position_id'],
                        pos['entry_price'],
                        pos['stop_loss'],
                        pos['take_profit'],
                        pos['current_price'],
                        pos['signal_type'],
                        pos['volume'],
                        pos['close_prices'],
                        pos['atr'],
                        self.mt5_connector
                    )
                except Exception as e:
                    logger.error(f"Error gestionando posición {pos}: {str(e)}")
            logger.debug("Monitoreo de posiciones activas: gestión activa ejecutada")
        except Exception as e:
            logger.error(f"Error en monitor_positions: {str(e)}")

    def stop_trading(self) -> None:
        """
        Detiene el bot de trading y desconecta de MT5.
        """
        try:
            self.running = False
            if hasattr(self, 'mt5_connector') and self.mt5_connector:
                self.mt5_connector.disconnect()
            logger.info("Mr.Cashondo Bot detenido correctamente.")
        except Exception as e:
            logger.error(f"Error al detener el bot: {str(e)}")
    def reset_daily_stats(self) -> None:
        """
        Resetea las estadísticas diarias del bot y del risk_manager. Envía notificación a Telegram si está configurado.
        """
        try:
            if hasattr(self, 'risk_manager') and self.risk_manager:
                self.risk_manager.reset_daily_stats()
                logger.info("Estadísticas diarias reseteadas correctamente.")
            if hasattr(self, 'telegram_alerts') and self.telegram_alerts:
                self.telegram_alerts.send_info_alert("Estadísticas diarias reseteadas.")
        except Exception as e:
            logger.error(f"Error al resetear estadísticas diarias: {str(e)}")
            if hasattr(self, 'telegram_alerts') and self.telegram_alerts:
                self.telegram_alerts.send_error_alert(str(e), "reset_daily_stats")
    def __init__(self):
        self.running = False
        self.subscription_email = None
        self.subscription_token = None
        self.last_scan_time = None
        self.mt5_connector = None
        self.signal_generator = None
        self.risk_manager = None
        self.telegram_alerts = None
        self.trade_db = None
        self.timeframes = ['M5', 'M15', 'H1']  # Ejemplo, puedes ajustar
        self.open_positions = []  # Inicializa la lista de posiciones abiertas para evitar errores

    def send_daily_summary(self):
        """
        Envía el resumen diario de operaciones a Telegram usando los datos del risk_manager.
        """
        if self.risk_manager and self.telegram_alerts:
            daily_stats = self.risk_manager.get_risk_summary()
            self.telegram_alerts.send_daily_summary(daily_stats)

    def initialize_components(self) -> bool:
        """
        Inicializa los módulos principales del bot. Devuelve True si todo fue exitoso, False si hubo algún error.
        """
        try:
            self.mt5_connector = MT5Connector()
            # Conectar a MT5 antes de cualquier operación que requiera conexión
            if hasattr(self.mt5_connector, 'connect') and not getattr(self.mt5_connector, 'connected', False):
                if not self.mt5_connector.connect():
                    logger.error("No se pudo conectar a MT5. Verifica credenciales y conexión.")
                    return False
            self.signal_generator = SignalGenerator()
            self.risk_manager = RiskManager()
            self.telegram_alerts = TelegramAlerts()
            # Si tienes un módulo de base de datos de trades:
            try:
                from trade_database import TradeDatabase
                self.trade_db = TradeDatabase()
            except ImportError:
                self.trade_db = None
                logger.warning("No se pudo importar TradeDatabase. El registro de señales/trades estará deshabilitado.")
            # --- Inicializar todos los símbolos disponibles en MT5 (sin rotación) ---
            if hasattr(self.signal_generator, 'initialize_symbols'):
                # Si existe el método, inicializa todos los símbolos (sin argumento rotation)
                self.signal_generator.initialize_symbols(self.mt5_connector)
            elif hasattr(self.signal_generator, 'symbols'):
                import MetaTrader5 as mt5
                all_symbols = mt5.symbols_get()
                self.signal_generator.symbols = [s.name for s in all_symbols]
            return True
        except Exception as e:
            logger.error(f"Error inicializando componentes: {e}")
            return False

    def start_trading(self) -> None:
        """Inicia el bot de trading con validación robusta de suscripción y monitoreo periódico."""
        try:
            print("\n=== VALIDACIÓN DE SUSCRIPCIÓN ===")
            email = input("Correo de suscripción: ").strip()
            token = getpass.getpass("Token de suscripción: ").strip()
            # Validar suscripción en Supabase (requiere active==True)
            if not validate_subscription(email, token):
                logger.error("No se pudo validar la suscripción o no está activa. El bot no se iniciará.")
                print("\nSUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE\n")
                return  # Detener el flujo si la suscripción es inválida
            self.subscription_email = email
            self.subscription_token = token

            # Iniciar monitor de suscripción en hilo aparte
            def monitor():
                while True:
                    if not validate_subscription(self.subscription_email, self.subscription_token):
                        logger.error("Suscripción inválida o expirada. Deteniendo bot.")
                        self.running = False
                        break
                    time.sleep(600)  # 10 minutos
            t = threading.Thread(target=monitor, daemon=True)
            t.start()

            # Inicializar componentes
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
                    if int(time_since_last_scan) % 1 == 0 and time_since_last_scan < scan_interval_minutes:
                        logger.debug(f"Bot active, waiting for scan ({time_since_last_scan:.1f}/{scan_interval_minutes} minutes passed)")
                    if time_since_last_scan >= scan_interval_minutes:
                        logger.info(f"Scan interval reached ({time_since_last_scan:.1f} minutes). Starting scan...")
                        self.scan_and_execute()
                        self.monitor_positions()
                        self.last_scan_time = datetime.now()

                        # --- FASE 7: Registro automático de métricas de performance globales y por símbolo ---
                        try:
                            # Global metrics
                            metrics = self.signal_generator.calculate_performance_metrics()
                            if hasattr(self, 'trade_db') and self.trade_db:
                                self.trade_db.log_metrics(metrics)
                            self.signal_generator.save_performance_metrics(filename='performance_metrics.csv')
                            logger.info("[METRICS] Métricas globales registradas en DB y CSV.")

                            # Por símbolo
                            symbol_metrics = self.signal_generator.analyze_symbol_performance()
                            if hasattr(self, 'trade_db') and self.trade_db:
                                for symbol, m in symbol_metrics.items():
                                    m['timestamp'] = None  # Se asigna en log_metrics
                                    self.trade_db.log_metrics(m, symbol=symbol)
                            logger.info("[METRICS] Métricas por símbolo registradas en DB.")
                        except Exception as e:
                            logger.error(f"[METRICS] Error al registrar métricas: {e}")
                    time.sleep(5)
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt, stopping bot...")
                    self.stop_trading()
                    break
                except Exception as e:
                    logger.error(f"Error in main trading loop: {str(e)}")
                    if self.telegram_alerts:
                        self.telegram_alerts.send_error_alert(str(e), "Main trading loop")
                    time.sleep(60)
        except Exception as e:
            logger.error(f"Critical error in start_trading: {str(e)}")
            if hasattr(self, 'telegram_alerts') and self.telegram_alerts:
                self.telegram_alerts.send_error_alert(str(e), "Critical error")
            if hasattr(self, 'mt5_connector') and self.mt5_connector:
                self.mt5_connector.disconnect()
            logger.info("Mr.Cashondo Bot stopped")

    # ...otros métodos de MrCashondoBot (scan_and_execute, process_signal, etc)...

# Entrypoint para ejecución directa
if __name__ == "__main__":
    try:
        logger.info("Starting Mr.Cashondo Trading Bot...")
        bot = MrCashondoBot()
        bot.start_trading()
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}")
    finally:
        logger.info("Bot execution completed")
"""
Main Trading Bot Module - Mr.Cashondo
Automated FOREX trading bot with scalping and day trading strategies
"""
import time
import logging
from datetime import datetime, timedelta, timezone
import os
import schedule
from dotenv import load_dotenv
from env_loader import load_env
load_env()
from subscription_api import validate_subscription
from typing import Dict, List, Optional
import schedule
import os
from dotenv import load_dotenv
from env_loader import load_env
load_env()

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
    def prompt_subscription_credentials(self):
        """
        Solicita email y token de suscripción al usuario por consola.
        """
        email = input("Correo de suscripción: ").strip()
        token = input("Token de suscripción: ").strip()
        self.subscription_email = email
        self.subscription_token = token

    def process_signal(self, signal: TradingSignal) -> None:
        """
        Procesar señal de trading:
        - Registrar señal en base de datos
        - Enviar a Telegram solo si confianza >= 0.8
        - Ejecutar solo si hay fondos y exposición suficiente
        - Registrar trade en base de datos (incluyendo parámetros usados)
        """
        try:
            # FILTRO DE TIPO DE SÍMBOLO: solo operar FOREX, índices y commodities/metales
            if not self.signal_generator._is_symbol_type_enabled(signal.symbol):
                logger.warning(f"[SYMBOL FILTER] Señal descartada por tipo de símbolo no permitido: {signal.symbol}")
                return

            # FILTRO DE CONFIANZA: solo procesar señales con confianza >= 0.8
            if hasattr(signal, 'confidence') and signal.confidence < 0.8:
                logger.info(f"Señal descartada por confianza insuficiente: {getattr(signal, 'confidence', None):.2f} < 0.80 para {signal.symbol}")
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
                'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
            }
            signal_id = self.trade_db.log_signal(signal_dict)

            # 1. Validar stops antes de procesar la señal
            order_type = 0 if signal.signal_type == "BUY" else 1  # Convertir a tipo MT5
            sl, tp, stops_valid = self.mt5_connector.validate_and_adjust_stops(
                signal.symbol, order_type, signal.entry_price, signal.stop_loss, signal.take_profit
            )
            if not stops_valid:
                logger.warning(f"Señal descartada para {signal.symbol}: Stops inválidos")
                # No enviar la señal a Telegram si no cumple confianza
                self.trade_db.update_signal_status(signal_id, "invalid_stops")
                return
            # Actualizar la señal con stops válidos
            signal.stop_loss = sl
            signal.take_profit = tp
            # Obtener symbol_info antes de calcular el tamaño de la posición
            symbol_info = self.mt5_connector.get_symbol_info(signal.symbol)
            if not symbol_info:
                logger.error(f"No se pudo obtener información del símbolo {signal.symbol}")
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

            # 3. Enviar la señal a Telegram (solo si confianza >= 0.8, ya filtrado arriba)
            self.telegram_alerts.send_signal_alert(signal)

            # 4. Control de ejecución inteligente: validar cantidad de trades abiertos, margen libre y riesgo antes de ejecutar
            min_volume = symbol_info.get('min_volume', 0.01)
            test_volume = max(position_size.volume, min_volume)
            margin_required = self.risk_manager.calculate_margin_required(
                signal.symbol, test_volume, signal.entry_price, symbol_info
            )
            exposure_limit = self.risk_manager.get_exposure_limit(symbol_info, account_info)
            can_open, motivo_open = self.risk_manager.can_open_position(signal.symbol)
            if not can_open:
                logger.warning(f"[EXECUTION][REJECTED] No se puede abrir nueva posición para {signal.symbol}: {motivo_open}")
                if self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'rejected',
                        'generation_params': None
                    }, generation_params={'reason': motivo_open})
                return
            if margin_required > exposure_limit:
                logger.warning(f"[RISK][REJECTED] margin_required={margin_required} excede exposure_limit={exposure_limit} para {signal.symbol}")
                if self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'rejected',
                        'generation_params': None
                    }, generation_params={'reason': 'margin_required > exposure_limit'})
                return
            # Validar margen libre mínimo absoluto (por ejemplo, 10 USD)
            min_free_margin = 10.0
            if account_info.get('margin_free', 0) < min_free_margin:
                logger.warning(f"[EXECUTION][REJECTED] Margen libre insuficiente ({account_info.get('margin_free', 0)} < {min_free_margin}) para {signal.symbol}")
                if self.trade_db:
                    self.trade_db.log_signal({
                        'symbol': signal.symbol,
                        'timeframe': getattr(signal, 'timeframe', 'UNKNOWN'),
                        'signal_type': signal.signal_type,
                        'entry_price': signal.entry_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'confidence': getattr(signal, 'confidence', 0.0),
                        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        'status': 'rejected',
                        'generation_params': None
                    }, generation_params={'reason': 'free_margin_below_minimum'})
                return
            can_execute = test_volume >= min_volume and margin_required <= exposure_limit and can_open and account_info.get('margin_free', 0) >= min_free_margin
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
                            'open_time': datetime.now(timezone.utc).isoformat(),
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
        'timestamp': getattr(signal, 'timestamp', datetime.now(timezone.utc).isoformat()),
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
        'open_time': datetime.now(timezone.utc).isoformat(),
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
            # Aquí puedes agregar la lógica de ejecución real del trade
        except Exception as e:
            logger.error(f"Error in execute_trade: {e}")
    def start_trading(self) -> None:
        """Inicia el bot de trading con validación robusta de suscripción y monitoreo periódico. Pausa si el mercado está cerrado."""
        import getpass
        import threading
        import sys
        try:
            print("\n=== VALIDACIÓN DE SUSCRIPCIÓN ===")
            email = input("Correo de suscripción: ").strip()
            token = getpass.getpass("Token de suscripción: ").strip()
            # Validar suscripción en Supabase (requiere active==True y token no vacío)
            if not email or not token:
                logger.error("Debes ingresar correo y token de suscripción.")
                print("\nSUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE\n")
                return
            if not validate_subscription(email, token):
                logger.error("No se pudo validar la suscripción o no está activa. El bot no se iniciará.")
                print("\nSUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE\n")
                return
            self.subscription_email = email
            self.subscription_token = token

            # Iniciar monitor de suscripción en hilo aparte
            def monitor():
                while True:
                    if not validate_subscription(self.subscription_email, self.subscription_token):
                        print("\nSUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE\n")
                        logger.error("SUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE")
                        sys.exit(0)
                    time.sleep(600)  # 10 minutos
            t = threading.Thread(target=monitor, daemon=True)
            t.start()

            # Inicializar componentes
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
                    # --- PAUSA SI EL MERCADO ESTÁ CERRADO ---
                    if not self.is_market_open():
                        logger.info("Mercado cerrado. El bot está en pausa. Esperando apertura...")
                        time.sleep(60)
                        continue
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
                    if hasattr(self, 'telegram_alerts'):
                        self.telegram_alerts.send_error_alert(str(e), "Main trading loop")
                    time.sleep(60)
        except Exception as e:
            logger.error(f"Critical error in start_trading: {str(e)}")
            if hasattr(self, 'telegram_alerts'):
                self.telegram_alerts.send_error_alert(str(e), "Critical error")
            # Disconnect from MT5
            if hasattr(self, 'mt5_connector') and self.mt5_connector:
                self.mt5_connector.disconnect()
            logger.info("Mr.Cashondo Bot stopped")

    def is_market_open(self) -> bool:
        """
        Devuelve True si el mercado FOREX está abierto (domingo 22:00 UTC a viernes 21:00 UTC), False si está cerrado.
        """
        now_utc = datetime.utcnow()
        weekday = now_utc.weekday()  # 0=lunes, 6=domingo
        hour = now_utc.hour
        minute = now_utc.minute
        # Mercado abre domingo 22:00 UTC, cierra viernes 21:00 UTC
        if weekday == 6 and (hour < 22):
            return False  # Domingo antes de apertura
        if weekday == 4 and (hour > 21 or (hour == 21 and minute > 0)):
            return False  # Viernes después de cierre
        if weekday == 5:
            return False  # Sábado
        if weekday == 6 and hour >= 22:
            return True  # Domingo después de apertura
        if 0 <= weekday <= 4:
            if weekday == 4 and hour == 21 and minute == 0:
                return True  # Viernes justo a las 21:00 UTC
            return True  # Lunes a viernes
        return False
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
    
    import threading
    import time
    from subscription_api import validate_subscription

    def _start_subscription_monitor(self, email: str, interval: int = 600):
        """
        Inicia un hilo que valida periódicamente la suscripción en Supabase.
        Si la suscripción deja de estar activa, detiene el bot e imprime mensaje.
        Args:
            email: Email de suscripción
            interval: Intervalo de validación en segundos (default: 600s = 10min)
        """
        import sys
        def monitor():
            while True:
                if not validate_subscription(email):
                    print("\nSUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE\n")
                    sys.exit(0)
                time.sleep(interval)
        t = threading.Thread(target=monitor, daemon=True)
        t.start()

    def start_trading(self) -> None:
        """Start the trading bot with un escaneo completo y validación periódica de suscripción."""
        # ...existing code...
        # Validar email de suscripción desde el inicio
        email = getattr(self, 'subscription_email', None)
        if email:
            self._start_subscription_monitor(email)
        # ...resto del método start_trading...
        try:
            # Validar suscripción SOLO UNA VEZ antes de iniciar el bot
            if not validate_subscription(self.subscription_email, self.subscription_token):
                logger.error("No se pudo validar la suscripción. El bot no se iniciará.")
                return
            # Validar email de suscripción desde el inicio para monitoreo periódico
            self._start_subscription_monitor(self.subscription_email)
            logger.info("Mr.Cashondo Bot started successfully")
            # ...resto del método start_trading...
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

    def start_trading(self) -> None:
        """Inicia el bot de trading con validación robusta de suscripción y monitoreo periódico."""
        import getpass
        import threading
        import sys
        try:
            print("\n=== VALIDACIÓN DE SUSCRIPCIÓN ===")
            email = input("Correo de suscripción: ").strip()
            token = getpass.getpass("Token de suscripción: ").strip()
            # Validar suscripción en Supabase (requiere active==True)
            if not validate_subscription(email, token):
                logger.error("No se pudo validar la suscripción o no está activa. El bot no se iniciará.")
                print("\nSUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE\n")
                return
            self.subscription_email = email
            self.subscription_token = token

            # Iniciar monitor de suscripción en hilo aparte
            def monitor():
                while True:
                    if not validate_subscription(self.subscription_email, self.subscription_token):
                        print("\nSUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE\n")
                        logger.error("SUSCRIPCION NO ACTIVA, RENUEVA O CONTACTA A SOPORTE")
                        sys.exit(0)
                    time.sleep(600)  # 10 minutos
            t = threading.Thread(target=monitor, daemon=True)
            t.start()

            # Inicializar componentes
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
                    if hasattr(self, 'telegram_alerts'):
                        self.telegram_alerts.send_error_alert(str(e), "Main trading loop")
                    time.sleep(60)
        except Exception as e:
            logger.error(f"Critical error in start_trading: {str(e)}")
            if hasattr(self, 'telegram_alerts'):
                self.telegram_alerts.send_error_alert(str(e), "Critical error")
            # Disconnect from MT5
            if hasattr(self, 'mt5_connector') and self.mt5_connector:
                self.mt5_connector.disconnect()
            logger.info("Mr.Cashondo Bot stopped")
