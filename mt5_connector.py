"""
MetaTrader 5 Connector Module
Manages connection and order execution with MT5 platform
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mt5_connector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
@dataclass
class OrderRequest:
    """Data class for order requests"""
    symbol: str
    action: int  # mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL
    volume: float
    price: float
    sl: float
    tp: float
    comment: str = "MrcashondoV2"  # Cambiado para identificar versión V2
    # filling_mode eliminado: la lógica de filling_mode se gestiona internamente en send_order

@dataclass
class MarketData:
    """Data class for market data"""
    symbol: str
    timeframe: str
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    time: np.ndarray

    def __init__(self, symbol: str, timeframe: str, open: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, time: np.ndarray):
        self.symbol = symbol
        self.timeframe = timeframe
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.time = time

class MT5Connector:
    """
    MetaTrader 5 connector for automated trading operations
    """
    
    def __init__(self):
        """Initialize MT5 connector with credentials from environment"""
        self.login = int(os.getenv('MT5_LOGIN'))
        self.password = os.getenv('MT5_PASSWORD')
        self.server = os.getenv('MT5_SERVER')
        self.connected = False
        self.account_info = None
        self.account_currency = None
        
    def connect(self) -> bool:
        """
        Connect to MetaTrader 5 platform
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            import MetaTrader5 as mt5
            # Initialize MT5 connection
            if not mt5.initialize():
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
            # Authorize with MT5
            login_result = mt5.login(self.login, password=self.password, server=self.server)
            if not login_result:
                logger.error(f"MT5 login failed: {mt5.last_error()} (login={self.login}, server={self.server})")
                mt5.shutdown()
                return False
            # Get account information
            self.account_info = mt5.account_info()
            if self.account_info is None:
                logger.error("Failed to get account information")
                mt5.shutdown()
                return False
            self.connected = True
            self.account_currency = self.account_info.currency
            logger.info(f"Successfully connected to MT5 - Account: {self.account_info.login}")
            logger.info(f"Balance: {self.account_info.balance}, Equity: {self.account_info.equity}")
            return True
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MetaTrader 5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
    
    def get_market_data(self, symbol: str, timeframe: str, count: int = 500) -> Optional[MarketData]:
        """
        Get market data for analysis
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Timeframe (e.g., "M1", "M5", "M15")
            count: Number of bars to retrieve
            
        Returns:
            MarketData object or None if error
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return None
        
        try:
            # Convert timeframe string to MT5 constant
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            tf = tf_map.get(timeframe)
            if tf is None:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None
            
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is None or len(rates) == 0:
                logger.error(f"Failed to get rates for {symbol}: {mt5.last_error()}")
                return None

            # Convert rates to numpy arrays using field access
            open_prices = np.array([rate['open'] for rate in rates])
            high_prices = np.array([rate['high'] for rate in rates])
            low_prices = np.array([rate['low'] for rate in rates])
            close_prices = np.array([rate['close'] for rate in rates])
            volumes = np.array([rate['tick_volume'] for rate in rates])
            times = np.array([rate['time'] for rate in rates])

            # Convert to MarketData object
            market_data = MarketData(symbol, timeframe, open_prices, high_prices, low_prices, close_prices, volumes, times)

            logger.info(f"Retrieved {len(rates)} bars for {symbol} {timeframe}")

            # Validar datos insuficientes
            if len(market_data.close) < 2:
                logger.warning(f"Skipping {symbol} due to insufficient data: {len(market_data.close)} bars")
                return None

            return market_data

        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Get detailed symbol information including trading parameters
        
        Args:
            symbol: Symbol name to get information for
        Returns:
            Dictionary with symbol information (siempre incluye 'leverage')
        """
        try:
            if not self.connected:
                logger.error("MT5 not connected")
                return {}
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Failed to get symbol info for {symbol}")
                return {}
            # Get tick info for current prices
            tick_info = mt5.symbol_info_tick(symbol)
            if not tick_info:
                logger.warning(f"Failed to get tick info for {symbol}")
                tick_info = None
            # Asegurar que 'leverage' esté presente y válido
            leverage = getattr(symbol_info, 'leverage', None)
            if leverage is None or leverage <= 0:
                # Intentar obtener leverage de la cuenta si no está disponible o es inválido
                account_info = mt5.account_info()
                leverage = getattr(account_info, 'leverage', 100) if account_info and getattr(account_info, 'leverage', 0) > 0 else 100
            # Si sigue sin estar presente, forzar 100 como valor seguro
            if leverage is None or leverage <= 0:
                leverage = 100
            # Prepare symbol information dictionary
            info = {
                'leverage': leverage,
                'symbol': symbol,
                'description': symbol_info.description,
                'currency_base': symbol_info.currency_base,
                'currency_profit': symbol_info.currency_profit,
                'currency_margin': symbol_info.currency_margin,
                'digits': symbol_info.digits,
                'point': symbol_info.point,
                'spread': symbol_info.spread,
                'trade_stops_level': getattr(symbol_info, 'trade_stops_level', 0),
                'freeze_level': getattr(symbol_info, 'freeze_level', 0),
                'trade_mode': symbol_info.trade_mode,
                'min_volume': symbol_info.volume_min,
                'max_volume': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'volume_limit': getattr(symbol_info, 'volume_limit', 0),
                'margin_initial': getattr(symbol_info, 'margin_initial', 0),
                'margin_maintenance': getattr(symbol_info, 'margin_maintenance', 0),
                'session_deals': getattr(symbol_info, 'session_deals', 0),
                'session_buy_orders': getattr(symbol_info, 'session_buy_orders', 0),
                'session_sell_orders': getattr(symbol_info, 'session_sell_orders', 0),
                'volume': getattr(symbol_info, 'volume', 0),
                'volumehigh': getattr(symbol_info, 'volumehigh', 0),
                'volumelow': getattr(symbol_info, 'volumelow', 0),
                'time': getattr(symbol_info, 'time', 0),
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'last': symbol_info.last,
                'swap_long': symbol_info.swap_long,
                'swap_short': symbol_info.swap_short,
                'swap_sunday': getattr(symbol_info, 'swap_sunday', 0),
                'swap_monday': getattr(symbol_info, 'swap_monday', 0),
                'swap_tuesday': getattr(symbol_info, 'swap_tuesday', 0),
                'swap_wednesday': getattr(symbol_info, 'swap_wednesday', 0),
                'swap_thursday': getattr(symbol_info, 'swap_thursday', 0),
                'swap_friday': getattr(symbol_info, 'swap_friday', 0),
                'swap_saturday': getattr(symbol_info, 'swap_saturday', 0),
                'contract_size': getattr(symbol_info, 'trade_contract_size', 100000),
                'tick_value': getattr(symbol_info, 'trade_tick_value', 1.0),
                'tick_size': getattr(symbol_info, 'trade_tick_size', 0.00001),
                'execution_mode': getattr(symbol_info, 'trade_execution_mode', 0),
                # 'filling_mode' eliminado: la lógica de filling_mode se gestiona internamente
                'expiration_mode': getattr(symbol_info, 'expiration_mode', 0),
                'order_gtc_mode': getattr(symbol_info, 'order_gtc_mode', 0),
                'option_mode': getattr(symbol_info, 'option_mode', 0),
                'option_right': getattr(symbol_info, 'option_right', 0),
                'visible': symbol_info.visible,
                'select': symbol_info.select,
                'custom': symbol_info.custom,
                'background_color': getattr(symbol_info, 'background_color', 0),
                'path': symbol_info.path,
                'isin': getattr(symbol_info, 'isin', ''),
                'category': getattr(symbol_info, 'category', ''),
                'exchange': getattr(symbol_info, 'exchange', ''),
                'formula': getattr(symbol_info, 'formula', ''),
                'page': getattr(symbol_info, 'page', ''),
                'sector': getattr(symbol_info, 'sector', ''),
                'industry': getattr(symbol_info, 'industry', ''),
                'country': getattr(symbol_info, 'country', ''),
                'sector_name': getattr(symbol_info, 'sector_name', ''),
                'industry_name': getattr(symbol_info, 'industry_name', ''),
                'country_name': getattr(symbol_info, 'country_name', ''),
                'subscription_delay': getattr(symbol_info, 'subscription_delay', 0),
                'trade_calc_mode': getattr(symbol_info, 'trade_calc_mode', 0),
                'trade_stops_level': getattr(symbol_info, 'trade_stops_level', 0),
                'trade_freeze_level': getattr(symbol_info, 'trade_freeze_level', 0),
                'trade_exemode': getattr(symbol_info, 'trade_exemode', 0),
                'start_time': getattr(symbol_info, 'start_time', 0),
                'expiration_time': getattr(symbol_info, 'expiration_time', 0),
                'sessions_quotes': getattr(symbol_info, 'sessions_quotes', 0),
                'sessions_trades': getattr(symbol_info, 'sessions_trades', 0)
            }
            
            # Add current tick information if available
            if tick_info:
                info.update({
                    'current_bid': tick_info.bid,
                    'current_ask': tick_info.ask,
                    'current_last': tick_info.last,
                    'current_volume': tick_info.volume,
                    'current_time': tick_info.time,
                    'current_flags': tick_info.flags,
                    'current_volume_real': tick_info.volume_real
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {str(e)}")
            return {}
    
    def get_dynamic_trading_params(self, symbol: str) -> Dict:
        """
        Get dynamic trading parameters for a symbol
        
        Args:
            symbol: Symbol name
            
        Returns:
            Dictionary with dynamic trading parameters
        """
        try:
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return {}
            
            # Calculate dynamic parameters
            params = {
                'symbol': symbol,
                'min_volume': symbol_info.get('min_volume', 0.01),
                'max_volume': symbol_info.get('max_volume', 100.0),
                'volume_step': symbol_info.get('volume_step', 0.01),
                'digits': symbol_info.get('digits', 5),
                'point': symbol_info.get('point', 0.00001),
                'spread': symbol_info.get('spread', 0),
                'trade_stops_level': symbol_info.get('trade_stops_level', 0),
                'freeze_level': symbol_info.get('freeze_level', 0),
                # 'filling_mode' eliminado: la lógica de filling_mode se gestiona internamente
                'execution_mode': symbol_info.get('execution_mode', mt5.SYMBOL_TRADE_EXECUTION_INSTANT),
                'contract_size': symbol_info.get('contract_size', 100000),
                'tick_value': symbol_info.get('tick_value', 1.0),
                'tick_size': symbol_info.get('tick_size', 0.00001),
                'margin_initial': symbol_info.get('margin_initial', 0),
                'swap_long': symbol_info.get('swap_long', 0),
                'swap_short': symbol_info.get('swap_short', 0),
                'current_bid': symbol_info.get('current_bid', 0),
                'current_ask': symbol_info.get('current_ask', 0),
                'current_spread': abs(symbol_info.get('current_ask', 0) - symbol_info.get('current_bid', 0))
            }
            
            # Calculate minimum stop loss/take profit distance
            min_stop_distance = max(
                symbol_info.get('trade_stops_level', 0) * symbol_info.get('point', 0.00001),
                symbol_info.get('current_spread', 0) * 2
            )
            
            params['min_stop_distance'] = min_stop_distance
            
            return params
            
        except Exception as e:
            logger.error(f"Error getting dynamic trading params for {symbol}: {str(e)}")
            return {}
    
    def send_order(self, order: OrderRequest) -> Optional[Dict]:
        """
        Envía una orden de trading a MT5 usando el filling mode más compatible para el símbolo:
        - Prioriza IOC, luego RETURN, luego FOK, según lo que soporte el instrumento (bitmask filling_modes)
        - Si no se puede determinar, fallback a IOC
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return None
        try:
            symbol_specs = self.get_dynamic_trading_params(order.symbol)
            if not symbol_specs:
                logger.error(f"Cannot get symbol specifications for {order.symbol}")
                return None
            digits = symbol_specs['digits']
            price = round(order.price, digits)
            sl = round(order.sl, digits)
            tp = round(order.tp, digits)
            min_volume = symbol_specs.get('min_volume', 0.01)
            max_volume = symbol_specs.get('max_volume', 100.0)
            volume_step = symbol_specs.get('volume_step', 0.01)
            adjusted_volume = max(min_volume, min(order.volume, max_volume))
            volume_steps = round(adjusted_volume / volume_step)
            final_volume = volume_steps * volume_step
            # Validar stops
            sl, tp, stops_valid = self.validate_and_adjust_stops(
                symbol=order.symbol,
                order_type=order.action,
                price=price,
                sl=sl,
                tp=tp
            )
            if not stops_valid:
                logger.error(f"Stops inválidos para {order.symbol}. Intentando ajuste agresivo.")
                sl, tp, stops_valid = self.validate_and_adjust_stops(
                    symbol=order.symbol,
                    order_type=order.action,
                    price=price,
                    sl=sl,
                    tp=tp,
                    force_adjustment=True
                )
                if not stops_valid:
                    logger.error(f"No se pudieron validar stops ni con ajuste agresivo para {order.symbol}")
                    return None
                else:
                    logger.info(f"Stops ajustados agresivamente para {order.symbol}: SL={sl}, TP={tp}")
            sl = round(sl, digits)
            tp = round(tp, digits)
            current_spread = symbol_specs.get('current_spread', 0.00002)
            spread_points = int(current_spread / symbol_specs.get('point', 0.00001))
            deviation = max(5, min(50, spread_points * 2))
            request_base = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": order.symbol,
                "volume": final_volume,
                "type": order.action,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": deviation,
                "magic": 12345,
                "comment": order.comment,
                "type_time": mt5.ORDER_TIME_GTC,
            }
            # --- Selección robusta de filling mode ---
            try:
                symbol_info = mt5.symbol_info(order.symbol)
                filling_modes = getattr(symbol_info, 'filling_modes', None)
                filling_mode = None
                filling_mode_name = None
                logger.info(f"[FILLING MODES] {order.symbol}: filling_mode={getattr(symbol_info, 'filling_mode', None)}, filling_modes={filling_modes}")
                request = dict(request_base)
                if filling_modes is not None:
                    # Si el broker expone filling_modes, usar la lógica habitual
                    if filling_modes & getattr(mt5, 'SYMBOL_FILLING_IOC', 1):
                        filling_mode = getattr(mt5, 'ORDER_FILLING_IOC', 1)
                        filling_mode_name = 'IOC'
                    elif filling_modes & getattr(mt5, 'SYMBOL_FILLING_RETURN', 2):
                        filling_mode = getattr(mt5, 'ORDER_FILLING_RETURN', 2)
                        filling_mode_name = 'RETURN'
                    elif filling_modes & getattr(mt5, 'SYMBOL_FILLING_FOK', 4):
                        filling_mode = getattr(mt5, 'ORDER_FILLING_FOK', 4)
                        filling_mode_name = 'FOK'
                    else:
                        logger.warning(f"No filling mode válido detectado para {order.symbol}, usando IOC por defecto")
                        filling_mode = getattr(mt5, 'ORDER_FILLING_IOC', 1)
                        filling_mode_name = 'IOC'
                    request["type_filling"] = filling_mode
                    logger.info(f"Enviando orden con filling mode {filling_mode_name} para {order.symbol}")
                else:
                    # Si el broker NO expone filling_modes, NO incluir type_filling (Market Execution puro)
                    logger.warning(f"No se pudo obtener filling_modes para {order.symbol}, NO se incluirá type_filling (Market Execution)")
                    logger.info(f"Enviando orden SIN type_filling para {order.symbol}")
                try:
                    result = mt5.order_send(request)
                    if result is not None and hasattr(result, 'retcode'):
                        if result.retcode == mt5.TRADE_RETCODE_DONE or result.retcode == mt5.TRADE_RETCODE_PLACED:
                            logger.info(f"Order sent successfully for {order.symbol} with filling mode {filling_mode_name or 'None'}. Retcode: {result.retcode}")
                            return {
                                'retcode': result.retcode,
                                'order': result.order,
                                'deal': getattr(result, 'deal', None),
                                'comment': getattr(result, 'comment', ''),
                                'mode': filling_mode_name,
                                'result': result
                            }
                        else:
                            logger.warning(f"Order failed for {order.symbol} with filling mode {filling_mode_name or 'None'}. Retcode: {result.retcode} - {self._get_retcode_description(result.retcode)}")
                    else:
                        logger.warning(f"No result or retcode for {order.symbol} with filling mode {filling_mode_name or 'None'}.")
                except Exception as mode_error:
                    logger.error(f"Exception sending order for {order.symbol} with filling mode {filling_mode_name or 'None'}: {mode_error}")
                logger.error(f"Order failed for {order.symbol} with filling mode {filling_mode_name or 'None'}.")
                return None
            except Exception as e:
                logger.error(f"Error sending order: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Error sending order: {str(e)}")
            return None

    def _get_retcode_description(self, retcode: int) -> str:
        """
        Get description for MT5 return codes
        
        Args:
            retcode: MT5 return code
            
        Returns:
            Human readable description
        """
        retcode_descriptions = {
            mt5.TRADE_RETCODE_REQUOTE: "Requote",
            mt5.TRADE_RETCODE_REJECT: "Request rejected",
            mt5.TRADE_RETCODE_CANCEL: "Request canceled",
            mt5.TRADE_RETCODE_PLACED: "Order placed",
            mt5.TRADE_RETCODE_DONE: "Request completed",
            mt5.TRADE_RETCODE_DONE_PARTIAL: "Request partially completed",
            mt5.TRADE_RETCODE_ERROR: "Request processing error",
            mt5.TRADE_RETCODE_TIMEOUT: "Request timeout",
            mt5.TRADE_RETCODE_INVALID: "Invalid request",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume",
            mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid stops",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "Trade disabled",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "Market closed",
            mt5.TRADE_RETCODE_NO_MONEY: "Insufficient money",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "Price changed",
            mt5.TRADE_RETCODE_PRICE_OFF: "Off quotes",
            mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Invalid expiration",
            mt5.TRADE_RETCODE_ORDER_CHANGED: "Order changed",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Too many requests",
            mt5.TRADE_RETCODE_NO_CHANGES: "No changes",
            mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Auto trading disabled",
            mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "Auto trading disabled by client",
            mt5.TRADE_RETCODE_LOCKED: "Request locked",
            mt5.TRADE_RETCODE_FROZEN: "Order or position frozen",
            mt5.TRADE_RETCODE_INVALID_FILL: "Invalid order filling type",
            mt5.TRADE_RETCODE_CONNECTION: "No connection",
            mt5.TRADE_RETCODE_ONLY_REAL: "Only real accounts allowed",
            mt5.TRADE_RETCODE_LIMIT_ORDERS: "Orders limit reached",
            mt5.TRADE_RETCODE_LIMIT_VOLUME: "Volume limit reached",
            mt5.TRADE_RETCODE_INVALID_ORDER: "Invalid or prohibited order type",
            mt5.TRADE_RETCODE_POSITION_CLOSED: "Position closed",
            mt5.TRADE_RETCODE_INVALID_CLOSE_VOLUME: "Invalid close volume",
            mt5.TRADE_RETCODE_CLOSE_ORDER_EXIST: "Close order already exists",
            mt5.TRADE_RETCODE_LIMIT_POSITIONS: "Positions limit reached"
        }
        
        return retcode_descriptions.get(retcode, f"Unknown retcode: {retcode}")
    
    def get_positions(self) -> List[Dict]:
        """
        Get current open positions
        
        Returns:
            List of position dictionaries
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'comment': pos.comment
                })
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []
    
    def modify_position(self, ticket: int, sl: float, tp: float) -> bool:
        """
        Modify position SL/TP
        
        Args:
            ticket: Position ticket
            sl: New stop loss
            tp: New take profit
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return False
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                logger.error(f"Position {ticket} not found")
                return False
            
            position = positions[0]
            
            # Create modify request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": ticket,
                "sl": sl,
                "tp": tp,
            }
            
            # Send modify request
            result = mt5.order_send(request)
            if result is None:
                logger.error(f"Modify failed: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Modify failed with retcode: {result.retcode}")
                return False
            
            logger.info(f"Position {ticket} modified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error modifying position: {str(e)}")
            return False
    
    def close_position(self, ticket: int) -> bool:
        """
        Close position
        
        Args:
            ticket: Position ticket to close
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return False
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                logger.error(f"Position {ticket} not found")
                return False
            
            position = positions[0]
            
            # Determine opposite order type
            if position.type == mt5.ORDER_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY
            
            # Create close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": mt5.symbol_info_tick(position.symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(position.symbol).ask,
                "deviation": 10,
                "magic": 12345,
                "comment": "Close by Mr.Cashondo Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close request
            result = mt5.order_send(request)
            if result is None:
                logger.error(f"Failed to send close order: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close order failed: {result.retcode} - {result.comment}")
                return False
            
            logger.info(f"Position {ticket} closed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False
    
    def get_account_balance(self) -> float:
        """
        Get current account balance
        
        Returns:
            Account balance
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return 0.0
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("Cannot get account info")
                return 0.0
            
            return account_info.balance
            
        except Exception as e:
            logger.error(f"Error getting account balance: {str(e)}")
            return 0.0
    
    def get_current_price(self, symbol: str) -> Optional[Tuple[float, float]]:
        """
        Get current bid/ask prices
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Tuple of (bid, ask) prices or None
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Cannot get tick data for {symbol}")
                return None
            
            return (tick.bid, tick.ask)
            
        except Exception as e:
            logger.error(f"Error getting current price: {str(e)}")
            return None
        
    def get_available_symbols(self, filter_type: str = "forex", dynamic_mode: bool = True) -> List[str]:
        """
        Get available symbols from MT5 completely dynamically
        
        Args:
            filter_type: Type of symbols to filter ("forex", "metals", "indices", "crypto", "all")
            dynamic_mode: If True, detects all symbols automatically. If False, uses curated list.
            
        Returns:
            List of available symbol names
        """
        try:
            if not self.connected:
                logger.error("MT5 not connected")
                return []
            
            # Get all available symbols
            symbols = mt5.symbols_get()
            if not symbols:
                logger.error("Failed to get symbols from MT5")
                return []
            
            available_symbols = []
            
            if dynamic_mode:
                # COMPLETAMENTE DINÁMICO: detectar automáticamente todos los símbolos
                for symbol in symbols:
                    symbol_name = symbol.name
                    
                    # Check if symbol is available for trading and visible in Market Watch
                    if not (symbol.visible and symbol.select and symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL):
                        continue
                    
                    # Filter by category using intelligent detection
                    if filter_type == "forex":
                        if self._is_forex_pair(symbol_name, symbol):
                            available_symbols.append(symbol_name)
                    elif filter_type == "metals":
                        if self._is_metal_symbol(symbol_name, symbol):
                            available_symbols.append(symbol_name)
                    elif filter_type == "indices":
                        if self._is_index_symbol(symbol_name, symbol):
                            available_symbols.append(symbol_name)
                    elif filter_type == "crypto":
                        if self._is_crypto_symbol(symbol_name, symbol):
                            available_symbols.append(symbol_name)
                    elif filter_type == "stocks":
                        if self._is_stock_symbol(symbol_name, symbol):
                            available_symbols.append(symbol_name)
                    elif filter_type == "all":
                        # Include all tradeable symbols
                        available_symbols.append(symbol_name)
            else:
                # Modo curado original (para compatibilidad)
                forex_majors = [
                    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", 
                    "USDCAD", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP",
                    "AUDJPY", "EURAUD", "EURCHF", "AUDCAD", "GBPCHF"
                ]
                
                metals = ["XAUUSD", "XAGUSD", "XAUEUR", "XAUAUD", "XAUJPY"]
                indices = ["US30", "US500", "NAS100", "GER30", "UK100", "AUS200"]
                
                for symbol in symbols:
                    symbol_name = symbol.name
                    
                    if not (symbol.visible and symbol.select):
                        continue
                    
                    if filter_type == "forex" and symbol_name in forex_majors:
                        available_symbols.append(symbol_name)
                    elif filter_type == "metals" and symbol_name in metals:
                        available_symbols.append(symbol_name)
                    elif filter_type == "indices" and symbol_name in indices:
                        available_symbols.append(symbol_name)
                    elif filter_type == "all" and symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                        available_symbols.append(symbol_name)
            
            # Ordenar por liquidez (volumen) y spread
            available_symbols = self._rank_symbols_by_quality(available_symbols)
            
            logger.info(f"Found {len(available_symbols)} available {filter_type} symbols (dynamic_mode={dynamic_mode})")
            if available_symbols:
                logger.info(f"Top symbols: {', '.join(available_symbols[:10])}")
            
            return available_symbols
            
        except Exception as e:
            logger.error(f"Error getting available symbols: {str(e)}")
            return []
    
    def _is_forex_pair(self, symbol_name: str, symbol_info) -> bool:
        """
        Detectar si un símbolo es un par FOREX automáticamente
        
        [MEJORA 2025-07-08]: Detección completamente dinámica de pares FOREX
        usando múltiples criterios para máxima compatibilidad con cualquier broker.
        
        Args:
            symbol_name: Nombre del símbolo
            symbol_info: Información del símbolo de MT5
            
        Returns:
            True si es un par FOREX
        """
        # Lista extendida de códigos de monedas ISO 4217
        currencies = {
            # Monedas principales
            "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD",
            # Monedas secundarias
            "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "TRY", "ZAR",
            "MXN", "SGD", "HKD", "CNH", "RUB", "BRL", "KRW", "INR",
            # Monedas emergentes
            "CNY", "THB", "MYR", "IDR", "PHP", "VND", "EGP", "ILS",
            "AED", "SAR", "QAR", "KWD", "BHD", "OMR", "JOD", "LBP"
        }
        
        # Verificar patrones comunes de pares FOREX
        patterns = [
            # Formato estándar: XXXYYY (6 caracteres)
            len(symbol_name) == 6 and symbol_name[:3] in currencies and symbol_name[3:] in currencies,
            # Formato con separador: XXX.YYY, XXX/YYY, XXX_YYY
            '.' in symbol_name and len(symbol_name.replace('.', '')) == 6,
            '/' in symbol_name and len(symbol_name.replace('/', '')) == 6,
            '_' in symbol_name and len(symbol_name.replace('_', '')) == 6
        ]
        
        # Verificar criterios adicionales (nueva detección mejorada)
        if any(patterns):
            return True            # Verificar por path (categoría) en MT5
            if hasattr(symbol_info, 'path'):
                path = symbol_info.path.lower()
                if 'forex' in path or 'currencies' in path or 'fx' in path:
                    return True
            elif isinstance(symbol_info, dict) and 'path' in symbol_info:
                path = symbol_info['path'].lower()
                if 'forex' in path or 'currencies' in path or 'fx' in path:
                    return True
              # Verificar por descripción
            if hasattr(symbol_info, 'description'):
                desc = symbol_info.description.lower()
                if any(term in desc for term in ['forex', 'currency pair', 'fx rate', 'exchange rate']):
                    return True
            elif isinstance(symbol_info, dict) and 'description' in symbol_info:
                desc = symbol_info['description'].lower()
                if any(term in desc for term in ['forex', 'currency pair', 'fx rate', 'exchange rate']):
                    return True
              # Verificar tamaño de contrato típico de FOREX
            if hasattr(symbol_info, 'volume_min') and 0.01 <= symbol_info.volume_min <= 0.1:
                # Tamaño de lote micro/mini típico de FOREX
                return True
            elif isinstance(symbol_info, dict) and 'volume_min' in symbol_info:
                if 0.01 <= symbol_info['volume_min'] <= 0.1:
                    # Tamaño de lote micro/mini típico de FOREX
                    return True
            
        return False
        path_indicators = ["forex", "fx", "currency", "currencies", "cur"]
        category_match = any(indicator in symbol_info.path.lower() for indicator in path_indicators)
        
        # Verificar por base/profit currency
        currency_match = (hasattr(symbol_info, 'currency_base') and 
                         hasattr(symbol_info, 'currency_profit') and
                         symbol_info.currency_base in currencies and 
                         symbol_info.currency_profit in currencies)
        
        return any(patterns) or category_match or currency_match
    
    def _is_metal_symbol(self, symbol_name: str, symbol_info) -> bool:
        """
        Detectar si un símbolo es un metal precioso
        """
        metal_patterns = ["XAU", "XAG", "XPD", "XPT", "GOLD", "SILVER", "PLATINUM", "PALLADIUM"]
        name_match = any(pattern in symbol_name.upper() for pattern in metal_patterns)
        
        path_indicators = ["metals", "precious", "gold", "silver"]
        path_match = any(indicator in symbol_info.path.lower() for indicator in path_indicators)
        
        return name_match or path_match
    
    def _is_index_symbol(self, symbol_name: str, symbol_info) -> bool:
        """
        Detectar si un símbolo es un índice
        """
        index_patterns = ["US30", "US500", "NAS100", "GER30", "UK100", "AUS200", "JPN225", "FRA40", "SPA35", "ITA40"]
        name_match = any(pattern in symbol_name.upper() for pattern in index_patterns)
        
        path_indicators = ["indices", "index", "stock"]
        path_match = any(indicator in symbol_info.path.lower() for indicator in path_indicators)
        
        return name_match or path_match
    
    def _is_crypto_symbol(self, symbol_name: str, symbol_info) -> bool:
        """
        Detectar si un símbolo es una criptomoneda
        """
        crypto_patterns = ["BTC", "ETH", "LTC", "XRP", "ADA", "DOT", "LINK", "BCH", "USDT", "USDC"]
        name_match = any(pattern in symbol_name.upper() for pattern in crypto_patterns)
        
        path_indicators = ["crypto", "digital", "coin", "token"]
        path_match = any(indicator in symbol_info.path.lower() for indicator in path_indicators)
        
        return name_match or path_match
    
    def _is_stock_symbol(self, symbol_name: str, symbol_info) -> bool:
        """
        Detectar si un símbolo es una acción individual
        """
        # Patrones de acciones comunes
        stock_patterns = [
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX",
            "AMD", "INTC", "PYPL", "ADBE", "CRM", "ORCL", "UBER", "LYFT"
        ]
        
        # Verificar si es una acción conocida
        name_match = any(pattern in symbol_name.upper() for pattern in stock_patterns)
        
        # Verificar por path/categoría
        path_indicators = ["nasdaq", "nyse", "stocks", "shares", "equity", "stock"]
        
        # Manejar tanto objetos como diccionarios
        path_match = False
        is_etf = False
        
        if hasattr(symbol_info, 'path'):
            path = symbol_info.path.lower()
            path_match = any(indicator in path for indicator in path_indicators)
            is_etf = any(etf in path for etf in ["etf", "fund", "trust"])
        elif isinstance(symbol_info, dict) and 'path' in symbol_info:
            path = symbol_info['path'].lower()
            path_match = any(indicator in path for indicator in path_indicators)
            is_etf = any(etf in path for etf in ["etf", "fund", "trust"])
        
        return (name_match or path_match) and not is_etf

    def _rank_symbols_by_quality(self, symbols: List[str]) -> List[str]:
        """
        Ordenar símbolos por calidad de trading (liquidez, spread, etc.)
        
        Args:
            symbols: Lista de símbolos a ordenar
            
        Returns:
            Lista ordenada por calidad
        """
        try:
            symbol_quality = []
            
            for symbol in symbols:
                quality_score = self._calculate_symbol_quality(symbol)
                if quality_score > 0:
                    symbol_quality.append((symbol, quality_score))
            
            # Ordenar por puntuación de calidad (mayor es mejor)
            symbol_quality.sort(key=lambda x: x[1], reverse=True)
            
            return [symbol for symbol, _ in symbol_quality]
            
        except Exception as e:
            logger.error(f"Error ranking symbols: {str(e)}")
            return symbols
    
    def _calculate_symbol_quality(self, symbol: str) -> float:
        """
        Calcular puntuación de calidad para un símbolo
        
        Args:
            symbol: Nombre del símbolo
            
        Returns:
            Puntuación de calidad (0-100)
        """
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return 0
            
            tick_info = mt5.symbol_info_tick(symbol)
            if not tick_info:
                return 0
            
            quality_score = 0
            
            # Factor 1: Spread (menor es mejor)
            spread_points = symbol_info.spread
            if spread_points > 0:
                spread_penalty = min(50, spread_points)  # Máximo 50 puntos de penalización
                quality_score += (50 - spread_penalty)
            
            # Factor 2: Volumen (mayor es mejor)
            volume = getattr(symbol_info, 'volume', 0)
            if volume > 0:
                volume_score = min(25, volume / 1000)  # Normalizar volumen
                quality_score += volume_score
            
            # Factor 3: Actividad (número de deals)
            deals = getattr(symbol_info, 'session_deals', 0)
            if deals > 0:
                deals_score = min(15, deals / 100)  # Normalizar deals
                quality_score += deals_score
            
            # Factor 4: Preferencia por pares principales
            major_pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
            if symbol in major_pairs:
                quality_score += 10
            
            return quality_score
            
        except Exception as e:
            logger.error(f"Error calculating quality for {symbol}: {str(e)}")
            return 0

    def get_symbol_specifications(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed symbol specifications dynamically
        
        Args:
            symbol: Symbol name
            
        Returns:
            Dictionary with comprehensive symbol specifications or None
        """
        try:
            if not self.connected:
                logger.error("MT5 not connected")
                return None
            
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Failed to get symbol info for {symbol}")
                return None
            
            # Get current tick for spread and prices
            tick = mt5.symbol_info_tick(symbol)
            
            return {
                'name': symbol_info.name,
                'description': symbol_info.description,
                'currency_base': symbol_info.currency_base,
                'currency_profit': symbol_info.currency_profit,
                'currency_margin': symbol_info.currency_margin,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'spread_float': symbol_info.spread_float,
                'trade_mode': symbol_info.trade_mode,
                'trade_stops_level': symbol_info.trade_stops_level,
                'trade_freeze_level': symbol_info.trade_freeze_level,
                'min_lot': symbol_info.volume_min,
                'max_lot': symbol_info.volume_max,
                'lot_step': symbol_info.volume_step,
                'contract_size': symbol_info.trade_contract_size,
                'tick_value': symbol_info.trade_tick_value,
                'tick_size': symbol_info.trade_tick_size,
                'swap_long': symbol_info.swap_long,
                'swap_short': symbol_info.swap_short,
                'margin_initial': symbol_info.margin_initial,
                'margin_maintenance': symbol_info.margin_maintenance,
                'session_deals': symbol_info.session_deals,
                'session_buy_orders': symbol_info.session_buy_orders,
                'session_sell_orders': symbol_info.session_sell_orders,
                'visible': symbol_info.visible,
                'select': symbol_info.select,
                'tradeable': symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL,
                # Obtener el mejor modo de llenado y los modos válidos
                'filling_mode': self._get_filling_mode(symbol_info)[0],  # El mejor modo
                'valid_filling_modes': self._get_filling_mode(symbol_info)[1],  # Lista de modos válidos
                'current_bid': tick.bid if tick else None,
                'current_ask': tick.ask if tick else None,
                'current_spread_points': (tick.ask - tick.bid) / symbol_info.point if tick else None
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol specifications for {symbol}: {str(e)}")
            return None

    def _get_filling_mode(self, symbol_info) -> int:
        """
        Devuelve una lista de filling modes válidos para Libertex MT5.
        Siempre retorna [ORDER_FILLING_IOC, ORDER_FILLING_RETURN] en ese orden.
        Nunca incluye FOK.
        """
        try:
            import MetaTrader5 as mt5
            modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]
            symbol_name = getattr(symbol_info, 'name', 'unknown') if symbol_info else 'unknown'
            logger.info(f"[FILLING MODES] {symbol_name} (Libertex MT5). Usando modos: {modes}")
            return modes[0], modes
        except Exception as e:
            logger.error(f"Error determining filling mode: {str(e)}")
            return mt5.ORDER_FILLING_IOC, [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]

    def calculate_dynamic_sl_tp(self, symbol: str, signal_type: str, entry_price: float, 
                               atr_value: float, sl_multiplier: float = 1.5, 
                               tp_multiplier: float = 2.5) -> Dict:
        """
        Calculate dynamic SL and TP based on symbol specifications and ATR
        
        Args:
            symbol: Trading symbol
            signal_type: "BUY" or "SELL"
            entry_price: Entry price
            atr_value: ATR value for the symbol
            sl_multiplier: SL distance multiplier
            tp_multiplier: TP distance multiplier
            
        Returns:
            Dictionary with calculated SL and TP values
        """
        try:
            symbol_info = self.get_symbol_specifications(symbol)
            if not symbol_info:
                logger.error(f"Cannot get symbol info for {symbol}")
                return {}
            
            # Get minimum stops level
            stops_level = symbol_info['trade_stops_level']
            point = symbol_info['point']
            digits = symbol_info['digits']
            
            # Calculate SL and TP distances
            sl_distance = atr_value * sl_multiplier
            tp_distance = atr_value * tp_multiplier
            
            # Ensure distances meet minimum stops level
            min_distance = stops_level * point
            sl_distance = max(sl_distance, min_distance)
            tp_distance = max(tp_distance, min_distance)
            
            if signal_type == "BUY":
                sl = entry_price - sl_distance
                tp = entry_price + tp_distance
            else:  # SELL
                sl = entry_price + sl_distance
                tp = entry_price - tp_distance
            
            # Round to symbol digits
            sl = round(sl, digits)
            tp = round(tp, digits)
            
            logger.info(f"Calculated SL: {sl}, TP: {tp} for symbol {symbol}")
            
            return {
                'stop_loss': sl,
                'take_profit': tp,
                'sl_distance_points': sl_distance / point,
                'tp_distance_points': tp_distance / point,
                'risk_reward_ratio': tp_distance / sl_distance,
                'min_stops_level': stops_level
            }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic SL/TP for symbol {symbol}: {str(e)}")
            return {}

    def validate_order_parameters(self, symbol: str, order_type: int, volume: float, 
                                 price: float, sl: float, tp: float) -> Tuple[bool, str]:
        """
        Validate order parameters against symbol specifications
        
        Args:
            symbol: Trading symbol
            order_type: Order type (BUY/SELL)
            volume: Order volume
            price: Order price
            sl: Stop loss
            tp: Take profit
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            symbol_info = self.get_symbol_specifications(symbol)
            if not symbol_info:
                return False, f"Cannot get symbol info for {symbol}"
            
            # Check if symbol is tradeable
            if not symbol_info['tradeable']:
                return False, f"Symbol {symbol} is not tradeable"
            
            # Validate volume
            if volume < symbol_info['min_lot']:
                return False, f"Volume {volume} below minimum {symbol_info['min_lot']}"
            
            if volume > symbol_info['max_lot']:
                return False, f"Volume {volume} above maximum {symbol_info['max_lot']}"
            
            # Check volume step
            lot_step = symbol_info['lot_step']
            if abs(volume % lot_step) > 1e-8:
                return False, f"Volume {volume} not multiple of lot step {lot_step}"
            
            # Validate stops level
            stops_level = symbol_info['trade_stops_level']
            point = symbol_info['point']
            min_distance = stops_level * point
            
            if order_type == mt5.ORDER_TYPE_BUY:
                sl_distance = abs(price - sl)
                tp_distance = abs(tp - price)
            else:
                sl_distance = abs(sl - price)
                tp_distance = abs(price - tp)
            
            if sl_distance < min_distance:
                return False, f"SL distance {sl_distance} below minimum {min_distance}"
            
            if tp_distance < min_distance:
                return False, f"TP distance {tp_distance} below minimum {min_distance}"
            
            logger.info(f"Order parameters validated successfully for symbol {symbol}")
            return True, "Order parameters valid"
            
        except Exception as e:
            logger.error(f"Error validating order parameters for symbol {symbol}: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def get_market_hours(self, symbol: str) -> Dict:
        """
        Get market hours for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with market hours information
        """
        try:
            if not self.connected:
                return {}
            
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return {}
            
            # Get trading sessions
            sessions = []
            for day in range(7):  # 0=Sunday, 6=Saturday
                session = mt5.symbol_info_sessionsquotes(symbol, day, 0)
                if session:
                    sessions.append({
                        'day': day,
                        'from': session[0].from_time,
                        'to': session[0].to_time
                    })
            
            return {
                'sessions': sessions,
                'trade_allowed': symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL,
                'session_deals': symbol_info.session_deals,
                'session_buy_orders': symbol_info.session_buy_orders,
                'session_sell_orders': symbol_info.session_sell_orders
            }
            
        except Exception as e:
            logger.error(f"Error getting market hours for {symbol}: {str(e)}")
            return {}
    
    def get_adaptive_strategy_params(self, symbol: str) -> Dict:
        """
        Obtener parámetros de estrategia adaptativa basados en características del símbolo
        
        Args:
            symbol: Nombre del símbolo
            
        Returns:
            Diccionario con parámetros de estrategia adaptados
        """
        try:
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return self._get_default_strategy_params()
            
            # Calcular características del símbolo
            spread = symbol_info.get('spread', 0)
            point = symbol_info.get('point', 0.00001)
            spread_in_pips = spread * point * 10000 if symbol.endswith('JPY') else spread * point * 100000
            
            # Obtener datos históricos para análisis de volatilidad
            volatility_data = self._analyze_symbol_volatility(symbol)
            
            # Clasificar el símbolo
            symbol_class = self._classify_symbol(symbol, symbol_info, spread_in_pips, volatility_data)
            
            # Generar parámetros adaptativos
            strategy_params = self._generate_adaptive_params(symbol, symbol_class, spread_in_pips, volatility_data)
            
            logger.info(f"Adaptive strategy for {symbol}: Class={symbol_class['category']}, "
                       f"Spread={spread_in_pips:.1f} pips, Volatility={volatility_data['classification']}")
            
            return strategy_params
            
        except Exception as e:
            logger.error(f"Error getting adaptive strategy params for {symbol}: {str(e)}")
            return self._get_default_strategy_params()
    
    def _analyze_symbol_volatility(self, symbol: str) -> Dict:
        """
        Analizar la volatilidad histórica del símbolo
        """
        try:
            # Obtener datos de diferentes timeframes
            timeframes = [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4, mt5.TIMEFRAME_D1]
            volatility_analysis = {
                'atr_15m': 0, 'atr_1h': 0, 'atr_4h': 0, 'atr_daily': 0,
                'daily_range': 0, 'weekly_range': 0, 'classification': 'normal'
            }
            
            for i, tf in enumerate(timeframes):
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 100)
                if rates is not None and len(rates) > 14:
                    # Calcular ATR
                    highs = rates['high']
                    lows = rates['low']
                    closes = rates['close']
                    
                    tr_values = []
                    for j in range(1, len(rates)):
                        tr1 = highs[j] - lows[j]
                        tr2 = abs(highs[j] - closes[j-1])
                        tr3 = abs(lows[j] - closes[j-1])
                        tr_values.append(max(tr1, tr2, tr3))
                    
                    atr = sum(tr_values[-14:]) / 14 if len(tr_values) >= 14 else sum(tr_values) / len(tr_values)
                    
                    # Almacenar ATR para cada timeframe
                    if i == 0: volatility_analysis['atr_15m'] = atr
                    elif i == 1: volatility_analysis['atr_1h'] = atr
                    elif i == 2: volatility_analysis['atr_4h'] = atr
                    elif i == 3: volatility_analysis['atr_daily'] = atr
            
            # Clasificar volatilidad
            daily_atr = volatility_analysis['atr_daily']
            point = self.get_symbol_info(symbol).get('point', 0.00001)
            daily_atr_pips = daily_atr / point
            
            if symbol.endswith('JPY'):
                daily_atr_pips *= 0.01
            else:
                daily_atr_pips *= 0.0001
            
            if daily_atr_pips > 150:
                volatility_analysis['classification'] = 'high'
            elif daily_atr_pips > 80:
                volatility_analysis['classification'] = 'medium-high'
            elif daily_atr_pips > 50:
                volatility_analysis['classification'] = 'normal'
            elif daily_atr_pips > 30:
                volatility_analysis['classification'] = 'low-medium'
            else:
                volatility_analysis['classification'] = 'low'
            
            return volatility_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing volatility for {symbol}: {str(e)}")
            return {'classification': 'normal', 'atr_daily': 0.001}
    
    def _classify_symbol(self, symbol: str, symbol_info: Dict, spread_pips: float, volatility: Dict) -> Dict:
        """
        Clasificar el símbolo para determinar estrategia óptima
        """
        # Clasificación base por tipo
        if symbol.startswith('XAU') or 'GOLD' in symbol:
            category = 'precious_metals'
            liquidity = 'high'
        elif symbol.startswith('XAG') or 'SILVER' in symbol:
            category = 'precious_metals'
            liquidity = 'medium'
        elif any(major in symbol for major in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']):
            category = 'major_pairs'
            liquidity = 'very_high'
        elif any(minor in symbol for minor in ['AUDUSD', 'USDCAD', 'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP']):
            category = 'minor_pairs'
            liquidity = 'high'
        elif symbol.endswith('JPY') or symbol.startswith('JPY'):
            category = 'jpy_pairs'
            liquidity = 'medium-high'
        elif any(exotic in symbol for exotic in ['ZAR', 'TRY', 'MXN', 'NOK', 'SEK', 'PLN']):
            category = 'exotic_pairs'
            liquidity = 'low-medium'
        else:
            category = 'cross_pairs'
            liquidity = 'medium'
        
        # Ajustar por spread
        if spread_pips <= 2:
            spread_class = 'tight'
        elif spread_pips <= 5:
            spread_class = 'normal'
        elif spread_pips <= 10:
            spread_class = 'wide'
        else:
            spread_class = 'very_wide'
        
        # Ajustar liquidez por spread
        if spread_class in ['wide', 'very_wide']:
            if liquidity == 'very_high':
                liquidity = 'high'
            elif liquidity == 'high':
                liquidity = 'medium'
        
        return {
            'category': category,
            'liquidity': liquidity,
            'spread_class': spread_class,
            'volatility': volatility['classification'],
            'spread_pips': spread_pips
        }
    
    def _generate_adaptive_params(self, symbol: str, symbol_class: Dict, spread_pips: float, volatility: Dict) -> Dict:
        """
        Generar parámetros de estrategia adaptativos
        """
        # Parámetros base
        params = {
            'timeframes': ['M15', 'M30', 'H1'],
            'sl_multiplier': 1.5,
            'tp_multiplier': 2.5,
            'min_atr_threshold_multiplier': 2.0,
            'confidence_threshold': 0.6,
            'max_spread_threshold': 10,
            'ema_periods': [20, 50, 200],
            'rsi_period': 14,
            'atr_period': 14,
            'adx_threshold': 25,
            'volume_filter': False,
            'session_filter': False,  # Temporarily disabled for testing
            'news_filter': False
        }
        
        # Adaptaciones por categoría
        category = symbol_class['category']
        
        if category == 'major_pairs':
            # Pares principales: estrategia estándar con filtros estrictos
            params.update({
                'sl_multiplier': 1.2,
                'tp_multiplier': 2.0,
                'confidence_threshold': 0.65,
                'max_spread_threshold': 3,
                'adx_threshold': 20,
                'volume_filter': False  # Temporarily disabled for testing
            })
            
        elif category == 'minor_pairs':
            # Pares menores: parámetros ligeramente más conservadores
            params.update({
                'sl_multiplier': 1.5,
                'tp_multiplier': 2.3,
                'confidence_threshold': 0.6,
                'max_spread_threshold': 5,
                'timeframes': ['M30', 'H1'],
            })
            
        elif category == 'jpy_pairs':
            # Pares JPY: ajustar por diferente valor de pip
            params.update({
                'sl_multiplier': 1.0,  # JPY se mueve más
                'tp_multiplier': 1.8,
                'min_atr_threshold_multiplier': 1.5,
                'confidence_threshold': 0.62,
                'max_spread_threshold': 4
            })
            
        elif category == 'precious_metals':
            # Metales: mayor volatilidad, parámetros más amplios
            params.update({
                'sl_multiplier': 2.5,
                'tp_multiplier': 4.0,
                'confidence_threshold': 0.7,
                'max_spread_threshold': 50,
                'timeframes': ['M30', 'H1', 'H4'],
                'adx_threshold': 30,
                'min_atr_threshold_multiplier': 3.0
            })
            
        elif category == 'exotic_pairs':
            # Pares exóticos: muy conservador
            params.update({
                'sl_multiplier': 2.0,
                'tp_multiplier': 3.5,
                'confidence_threshold': 0.75,
                'max_spread_threshold': 20,
                'timeframes': ['H1', 'H4'],
                'adx_threshold': 35,
                'session_filter': False,  # Temporarily disabled for testing
                'news_filter': True
            })
        
        # Adaptaciones por volatilidad
        volatility_class = volatility['classification']
        
        if volatility_class == 'high':
            # Alta volatilidad: aumentar SL/TP, mayor prudencia
            params['sl_multiplier'] *= 1.4
            params['tp_multiplier'] *= 1.3
            params['confidence_threshold'] += 0.05
            params['adx_threshold'] += 5
            
        elif volatility_class == 'low':
            # Baja volatilidad: reducir SL/TP, ser más agresivo
            params['sl_multiplier'] *= 0.8
            params['tp_multiplier'] *= 0.9
            params['confidence_threshold'] -= 0.05
            params['adx_threshold'] -= 5
        
        # Adaptaciones por spread
        if spread_pips > 5:
            # Spread alto: ser más selectivo
            params['confidence_threshold'] += 0.1
            params['tp_multiplier'] *= 1.2  # TP más amplio para compensar spread
            
        elif spread_pips < 2:
            # Spread bajo: ser más agresivo
            params['confidence_threshold'] -= 0.05
        
        # Límites de seguridad
        params['sl_multiplier'] = max(0.8, min(3.0, params['sl_multiplier']))
        params['tp_multiplier'] = max(1.2, min(5.0, params['tp_multiplier']))
        params['confidence_threshold'] = max(0.5, min(0.8, params['confidence_threshold']))
        params['adx_threshold'] = max(15, min(40, params['adx_threshold']))
        
        # Información adicional
        params.update({
            'symbol_category': category,
            'liquidity_class': symbol_class['liquidity'],
            'spread_class': symbol_class['spread_class'],
            'volatility_class': volatility_class,
            'adapted_for_spread': spread_pips,
            'recommended_risk_per_trade': self._get_recommended_risk(symbol_class),
            'session_times': self._get_optimal_sessions(symbol),
            'min_volume_threshold': self._get_min_volume_threshold(symbol_class)
        })
        
        return params
    
    def _get_default_strategy_params(self) -> Dict:
        """Parámetros de estrategia por defecto"""
        return {
            'timeframes': ['M15', 'M30', 'H1'],
            'sl_multiplier': 1.5,
            'tp_multiplier': 2.5,
            'min_atr_threshold_multiplier': 2.0,
            'confidence_threshold': 0.6,
            'max_spread_threshold': 10,
            'ema_periods': [20, 50, 200],
            'rsi_period': 14,
            'atr_period': 14,
            'adx_threshold': 25,
            'symbol_category': 'unknown',
            'recommended_risk_per_trade': 0.01
        }
    
    def _get_recommended_risk(self, symbol_class: Dict) -> float:
        """Obtener riesgo recomendado por operación según la clase del símbolo"""
        category = symbol_class['category']
        liquidity = symbol_class['liquidity']
        spread_class = symbol_class['spread_class']
        
        base_risk = 0.01  # 1% base
        
        # Ajustar por categoría
        if category == 'major_pairs':
            risk_multiplier = 1.0
        elif category == 'minor_pairs':
            risk_multiplier = 0.8
        elif category == 'precious_metals':
            risk_multiplier = 0.6
        elif category == 'exotic_pairs':
            risk_multiplier = 0.4
        else:
            risk_multiplier = 0.7
        
        # Ajustar por liquidez
        if liquidity == 'very_high':
            liquidity_multiplier = 1.0
        elif liquidity == 'high':
            liquidity_multiplier = 0.9
        elif liquidity == 'medium':
            liquidity_multiplier = 0.7
        else:
            liquidity_multiplier = 0.5
        
        # Ajustar por spread
        if spread_class == 'tight':
            spread_multiplier = 1.0
        elif spread_class == 'normal':
            spread_multiplier = 0.8
        elif spread_class == 'wide':
            spread_multiplier = 0.6
        else:
            spread_multiplier = 0.4
        
        final_risk = base_risk * risk_multiplier * liquidity_multiplier * spread_multiplier
        return max(0.002, min(0.015, final_risk))  # Entre 0.2% y 1.5%
    
    def _get_optimal_sessions(self, symbol: str) -> List[str]:
        """Obtener sesiones de trading óptimas para el símbolo"""
        # Sesiones principales para diferentes regiones
        if any(pair in symbol for pair in ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY']):
            return ['asia', 'london', 'newyork']
        elif any(pair in symbol for pair in ['EURUSD', 'GBPUSD', 'EURGBP', 'EURCHF']):
            return ['london', 'newyork']
        elif any(pair in symbol for pair in ['AUDUSD', 'NZDUSD', 'AUDNZD']):
            return ['asia', 'london']
        elif symbol.startswith('XAU') or symbol.startswith('XAG'):
            return ['london', 'newyork']  # Metales más activos en estas sesiones
        else:
            return ['london', 'newyork']  # Por defecto
    
    def _get_min_volume_threshold(self, symbol_class: Dict) -> int:
        """Obtener umbral mínimo de volumen según la clase del símbolo"""
        category = symbol_class['category']

        thresholds = {
            'major_pairs': 1000,
            'minor_pairs': 500,
            'exotic_pairs': 100,
            'precious_metals': 200,
            'indices': 300
        }

        return thresholds.get(category, 100)
    
    def validate_and_adjust_stops(self, symbol: str, order_type: int, price: float, 
                                  sl: float, tp: float, force_adjustment: bool = False) -> Tuple[float, float, bool]:
        """
        Valida y ajusta los niveles de SL/TP para asegurar que cumplan con los requisitos del broker.
        Incluye ajustes específicos por tipo de instrumento para máxima compatibilidad.
        
        Args:
            symbol: Símbolo de trading
            order_type: Tipo de orden (BUY=0, SELL=1)
            price: Precio de ejecución
            sl: Stop Loss propuesto
            tp: Take Profit propuesto
            force_adjustment: Si es True, aplica ajustes más agresivos para garantizar validez
            
        Returns:
            Tupla de (SL ajustado, TP ajustado, son válidos)
        """
        try:
            # Obtener especificaciones del símbolo
            symbol_specs = self.get_dynamic_trading_params(symbol)
            if not symbol_specs:
                logger.error(f"No se pueden obtener especificaciones para {symbol}")
                return sl, tp, False

            # Garantizar que price, sl y tp sean valores numéricos
            try:
                price = float(price) if price is not None else 0.0
                sl = float(sl) if sl is not None else 0.0
                tp = float(tp) if tp is not None else 0.0
            except (ValueError, TypeError):
                logger.error(f"Valores no numéricos en stops para {symbol}: price={price}, sl={sl}, tp={tp}")
                return sl, tp, False

            # Verificar si los precios son válidos (no 0 o None)
            if price <= 0:
                logger.error(f"Precio inválido para {symbol}: {price}")
                return sl, tp, False
                
            # Obtener parámetros clave
            digits = symbol_specs.get('digits', 5)
            point = float(symbol_specs.get('point', 0.00001))
            stops_level = float(symbol_specs.get('trade_stops_level', 0))

            # Clasificar el instrumento para aplicar lógica adecuada
            instrument_category = self._determine_instrument_category(symbol, symbol_specs)

            # Factor de seguridad adicional (aumentado para acciones y problemas reportados)
            safety_factor = 10 if force_adjustment else 6  # Incrementado sustancialmente para prevenir errores

            # Calcular distancia mínima en precio (con factor de seguridad)
            min_distance_points = max(stops_level, 5) * safety_factor  # Siempre al menos 5 puntos
            min_distance_price = min_distance_points * point

            # Añadir margen de seguridad específico según tipo de instrumento (valores significativamente aumentados)
            if instrument_category == "forex":
                if 'JPY' in symbol:
                    min_distance_price = max(min_distance_price, 0.20 if force_adjustment else 0.10)    # Mínimo 10-20 pips para pares JPY
                else:
                    min_distance_price = max(min_distance_price, 0.0020 if force_adjustment else 0.0010)  # Mínimo 10-20 pips para forex normal
            elif instrument_category == "metal":
                min_distance_price = max(min_distance_price, 1.0 if force_adjustment else 0.6)        # Mínimo 0.6-1.0 USD para oro/plata
            elif instrument_category == "index":
                min_distance_price = max(min_distance_price, 5.0 if force_adjustment else 3.0)         # Mínimo 3-5 puntos para índices
            elif instrument_category == "stock":
                min_distance_price = max(min_distance_price, 3.0 if force_adjustment else 2.0)        # Mínimo 2-3 USD para acciones
            elif instrument_category == "crypto":
                min_distance_price = max(min_distance_price, 40.0 if force_adjustment else 20.0)      # Mínimo 20-40 USD para criptomonedas
            else:
                min_distance_price = max(min_distance_price, 2.0 if force_adjustment else 1.0)        # Valor seguro por defecto

            # Si el min_distance_price es mayor que el precio, usar un porcentaje del precio como fallback
            if min_distance_price >= price:
                min_distance_price = price * 0.05  # 5% del precio como distancia mínima de emergencia
                
            # Obtener información actual del mercado
            current_price_data = self.get_current_price(symbol)
            if current_price_data:
                bid, ask = current_price_data
                # Usar el precio relevante según el tipo de orden
                market_price = ask if order_type == 0 else bid
                # Si el precio de orden está alejado del mercado, usar el precio de mercado para validación
                if abs(price - market_price) > min_distance_price * 2:
                    logger.warning(f"Precio de orden {price} alejado del mercado {market_price}. Usando precio de mercado para validación.")
                    price = market_price
                
            # Prevenir stops negativos para cualquier instrumento
            if sl <= 0:
                # Para stops nulos o negativos, crear un stop por defecto basado en la categoría del instrumento
                if order_type == 0:  # BUY
                    sl = max(price - min_distance_price, price * 0.90)
                else:  # SELL
                    sl = min(price + min_distance_price, price * 1.10)
                logger.warning(f"SL ajustado para evitar valor negativo o nulo: {sl} para {symbol}")
            
            # Verificar y ajustar SL según tipo de orden
            if order_type == 0:  # BUY (mt5.ORDER_TYPE_BUY)
                # Para compras, SL debe estar por DEBAJO del precio de entrada
                if sl >= price or price - sl < min_distance_price:
                    sl = max(price - min_distance_price, price * 0.90)
                    logger.warning(f"SL ajustado a {sl} para cumplir distancia mínima en {symbol}")
            else:  # SELL (mt5.ORDER_TYPE_SELL)
                # Para ventas, SL debe estar por ENCIMA del precio de entrada
                if sl <= price or sl - price < min_distance_price:
                    sl = min(price + min_distance_price, price * 1.10)
                    logger.warning(f"SL ajustado a {sl} para cumplir distancia mínima en {symbol}")
            
            # Manejo similar para TP nulos o inválidos
            if tp <= 0:
                # Para TPs nulos o negativos, crear un TP por defecto basado en el SL (ratio 1.5)
                if order_type == 0:  # BUY
                    tp = price + max((price - sl) * 1.5, min_distance_price)
                else:  # SELL
                    tp = price - max((sl - price) * 1.5, min_distance_price)
                logger.warning(f"TP ajustado para evitar valor negativo o nulo: {tp} para {symbol}")

            # Verificar y ajustar TP según tipo de orden
            if order_type == 0:  # BUY
                # Para compras, TP debe estar por ENCIMA del precio de entrada
                if tp <= price or tp - price < min_distance_price:
                    tp = price + max(min_distance_price, abs(price - sl) * 1.5)
                    logger.warning(f"TP ajustado a {tp} para cumplir distancia mínima en {symbol}")
            else:  # SELL
                # Para ventas, TP debe estar por DEBAJO del precio de entrada
                if tp >= price or price - tp < min_distance_price:
                    tp = price - max(min_distance_price, abs(sl - price) * 1.5)
                    logger.warning(f"TP ajustado a {tp} para cumplir distancia mínima en {symbol}")

            # Validar stops ajustados para mantener la relación riesgo-recompensa
            if abs(tp - sl) / max(abs(price - sl), 1e-8) < 1.3:
                if order_type == 0:
                    tp = price + max(abs(price - sl) * 1.5, min_distance_price)
                else:
                    tp = price - max(abs(sl - price) * 1.5, min_distance_price)
                logger.info(f"TP ajustado dinámicamente para mantener riesgo-recompensa en {symbol}: TP={tp}")

            # Redondear a los dígitos correctos
            sl = round(sl, digits)
            tp = round(tp, digits)

            # Chequeo final: nunca retornar stops negativos o cero
            if sl <= 0:
                sl = round(price * 0.90, digits) if order_type == 0 else round(price * 1.10, digits)
                logger.error(f"SL era <= 0 tras todos los ajustes, forzado a {sl} para {symbol}")
            if tp <= 0:
                tp = round(price * 1.05, digits) if order_type == 0 else round(price * 0.95, digits)
                logger.error(f"TP era <= 0 tras todos los ajustes, forzado a {tp} para {symbol}")

            logger.info(f"Stops validados para {symbol}: SL={sl}, TP={tp} (distancia mínima: {min_distance_price})")
            return sl, tp, True
            
        except Exception as e:
            logger.error(f"Error validando stops para {symbol}: {str(e)}")
            return sl, tp, False
            
    def _determine_instrument_category(self, symbol: str, symbol_specs: dict) -> str:
        """
        Determina la categoría del instrumento basado en su símbolo y propiedades
        
        Args:
            symbol: Símbolo del instrumento
            symbol_specs: Información del símbolo de MT5
            
        Returns:
            Categoría del instrumento: "forex", "index", "stock", "metal", "crypto", "unknown"
        """
        try:
            # Determinar por path si está disponible
            path = ''
            
            # Manejar diferentes tipos de entradas (dict o objeto)
            if isinstance(symbol_specs, dict) and 'path' in symbol_specs:
                path = str(symbol_specs['path']).lower()
            elif hasattr(symbol_specs, 'path') and symbol_specs.path:
                path = str(symbol_specs.path).lower()
            
            # Determinar categoría por path si disponible
            if path:
                if any(keyword in path for keyword in ['forex', 'currencies', 'fx', 'major', 'minor']):
                    return 'forex'
                elif any(keyword in path for keyword in ['indices', 'index', 'indice']):
                    return 'index'
                elif any(keyword in path for keyword in ['metals', 'commodities', 'xau', 'gold', 'xag']):
                    return 'metal'
                else:
                    return 'unknown'
            
            # Determinar por patrones en el símbolo
            symbol_upper = symbol.upper()
            
            # Detección de FOREX mejorada
            forex_currencies = ['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF', 'CNY', 'MXN', 'SEK', 'NOK']
            if len(symbol_upper) <= 8 and any(symbol_upper.startswith(curr) or symbol_upper.endswith(curr) for curr in forex_currencies):
                # Verificar que tenga al menos dos códigos de moneda
                if sum(1 for curr in forex_currencies if curr in symbol_upper) >= 2:
                    return "forex"
            
            # Detección de metales más robusta
            metal_patterns = ['XAU', 'GOLD', 'XAG', 'SILVER', 'PLAT', 'PLATINUM', 'COPPER', 'PALLADIUM', 'XPD', 'XPT']
            if any(pattern in symbol_upper for pattern in metal_patterns):
                return "metal"
                
            # Detección de índices más amplia
            index_patterns = ['US30', 'SPX', 'SP500', 'NAS100', 'NDX', 'DAX', 'UK100', 'FTSE', 'CAC', 'IBEX', 'N225', 'HSI']
            if any(pattern in symbol_upper for pattern in index_patterns):
                return "index"
                
            # Detección de criptomonedas
            crypto_patterns = ['BTC', 'ETH', 'LTC', 'XRP', 'DOGE', 'BCH', 'BNB', 'USDT']
            if any(pattern in symbol_upper for pattern in crypto_patterns):
                return "crypto"
                
            # Lógica adicional para símbolos específicos
            if 'USD' in symbol_upper and len(symbol_upper) >= 3 and len(symbol_upper) <= 8:
                return "forex"  # Probable par de divisas
                
            # Por defecto asumimos acciones si no se puede categorizar y parece tener formato de ticker
            if len(symbol_upper) <= 5 and symbol_upper.isalpha():
                return "stock"
                
            # Último recurso
            return "unknown"
            
        except Exception as e:
            logger.error(f"Error determinando categoría para {symbol}: {str(e)}")
            return "unknown"
    
    def get_account_info(self) -> Dict:
        """
        Get account information as a dictionary
        
        Returns:
            Dictionary with account information or empty dict if error
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return {}
        
        try:
            # Get fresh account info
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("Cannot get account info")
                return {}
            
            # Validate leverage
            if account_info.leverage <= 0:
                logger.error("Leverage inválido en la cuenta. Usando valor predeterminado de 100.")
                account_info = account_info._replace(leverage=100)

            # Convert named tuple to dictionary
            result = {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'margin_free': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'leverage': account_info.leverage,
                'currency': account_info.currency
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}
    
    def get_total_exposure(self) -> float:
        """
        Calcula la exposición total del capital en posiciones abiertas (riesgo real si todas cierran en SL).
        Returns:
            float: Exposición total en la moneda de la cuenta
        """
        try:
            positions = self.get_positions()
            if not positions:
                return 0.0

            total_risk = 0.0
            for position in positions:
                symbol = position.get('symbol', '')
                volume = position.get('volume', 0.0)
                entry_price = position.get('price_open', 0.0)
                sl = position.get('sl', 0.0)
                # Si no hay SL, no se puede calcular el riesgo
                if not sl or sl <= 0 or entry_price <= 0:
                    continue
                symbol_info = self.get_symbol_info(symbol)
                if not symbol_info:
                    logger.warning(f"No se pudo obtener información para {symbol}")
                    continue
                contract_size = symbol_info.get('contract_size', 100000.0)
                point = symbol_info.get('point', 0.0001)
                digits = symbol_info.get('digits', 5)
                pip_size = 0.01 if symbol.endswith('JPY') else 0.0001
                sl_distance = abs(entry_price - sl)
                sl_pips = sl_distance / pip_size
                pip_value_per_lot = pip_size * contract_size
                pip_value = symbol_info.get('tick_value', pip_value_per_lot)
                risk = sl_pips * pip_value * volume
                # Conversión a moneda de cuenta si es necesario
                if symbol_info.get('currency_profit') != self.account_currency:
                    conversion_pair = f"{symbol_info.get('currency_profit')}{self.account_currency}"
                    alt_conversion_pair = f"{self.account_currency}{symbol_info.get('currency_profit')}"
                    conversion_rate = 1.0
                    conversion_tick = mt5.symbol_info_tick(conversion_pair)
                    if conversion_tick:
                        conversion_rate = conversion_tick.bid
                    else:
                        alt_conversion_tick = mt5.symbol_info_tick(alt_conversion_pair)
                        if alt_conversion_tick and alt_conversion_tick.bid > 0:
                            conversion_rate = 1.0 / alt_conversion_tick.bid
                    risk *= conversion_rate
                total_risk += risk
            logger.info(f"Exposición total actual (riesgo real): {total_risk:.2f} {self.account_currency}")
            return total_risk
        except Exception as e:
            logger.error(f"Error calculando exposición total: {str(e)}")
            return 0.0
    
    def adjust_stops(entry_price: float, sl: float, tp: float, min_distance: float) -> Tuple[float, float]:
        if abs(sl - entry_price) < min_distance:
            sl = entry_price - min_distance
        if abs(tp - entry_price) < min_distance:
            tp = entry_price + min_distance
        if abs(tp - sl) / abs(entry_price - sl) < 1.5:  # Mantener riesgo-recompensa mínimo
            tp = sl + abs(entry_price - sl) * 1.5
        return sl, tp

    def get_symbol_leverage(self, symbol: str) -> float:
        """
        Retrieve the leverage for a given symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Leverage value or a default value if unavailable.
        """
        try:
            symbol_info = self.get_symbol_info(symbol)
            leverage = symbol_info.get('leverage', None)
            if leverage is None or leverage <= 0:
                logger.warning(f"Leverage not found or invalid for {symbol}. Using default leverage of 100.")
                return 100.0
            return leverage
        except Exception as e:
            logger.error(f"Error retrieving leverage for {symbol}: {str(e)}")
            return 100.0

    def propagate_leverage_to_risk_manager(self, risk_manager):
        """
        Propagate leverage information to the RiskManager.

        Args:
            risk_manager: Instance of RiskManager.
        """
        try:
            for symbol in self.get_all_symbols():
                leverage = self.get_symbol_leverage(symbol)
                risk_manager.update_symbol_leverage(symbol, leverage)
                logger.info(f"Leverage for {symbol} propagated to RiskManager: {leverage}")
        except Exception as e:
            logger.error(f"Error propagating leverage to RiskManager: {str(e)}")
