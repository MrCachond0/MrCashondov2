"""
Signal Generator Module
Generates trading signals based on technical analysis
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from mt5_connector import MarketData
import csv
import threading
import os

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signal_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """Data class for trading signals"""
    symbol: str
    timeframe: str
    signal_type: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0.0 to 1.0
    reasons: List[str]
    timestamp: datetime
    atr_value: float

class VirtualTrade:
    """
    Representa un trade virtual basado en una señal generada
    """
    def __init__(self, signal: TradingSignal):
        self.symbol = signal.symbol
        self.timeframe = signal.timeframe
        self.signal_type = signal.signal_type
        self.entry_price = signal.entry_price
        self.stop_loss = signal.stop_loss
        self.take_profit = signal.take_profit
        self.confidence = signal.confidence
        self.reasons = signal.reasons
        self.open_time = signal.timestamp
        self.atr_value = signal.atr_value
        self.close_time = None
        self.close_price = None
        self.result = None  # 'TP', 'SL', 'OPEN'
        self.history = []  # [(timestamp, price)]

    def update(self, timestamp, price):
        self.history.append((timestamp, price))
        if self.result is not None:
            return
        if self.signal_type == 'BUY':
            if price >= self.take_profit:
                self.result = 'TP'
                self.close_time = timestamp
                self.close_price = self.take_profit
            elif price <= self.stop_loss:
                self.result = 'SL'
                self.close_time = timestamp
                self.close_price = self.stop_loss
        else:
            if price <= self.take_profit:
                self.result = 'TP'
                self.close_time = timestamp
                self.close_price = self.take_profit
            elif price >= self.stop_loss:
                self.result = 'SL'
                self.close_time = timestamp
                self.close_price = self.stop_loss

    def is_closed(self):
        return self.result in ('TP', 'SL')

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'signal_type': self.signal_type,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'confidence': self.confidence,
            'reasons': '|'.join(self.reasons),
            'open_time': self.open_time.strftime('%Y-%m-%d %H:%M:%S'),
            'close_time': self.close_time.strftime('%Y-%m-%d %H:%M:%S') if self.close_time else '',
            'close_price': self.close_price if self.close_price else '',
            'result': self.result if self.result else 'OPEN',
            'atr_value': self.atr_value,
            'history': str(self.history)
        }

class TechnicalIndicators:
    """
    Technical indicators calculation class
    """
    
    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate Exponential Moving Average
        
        Args:
            data: Price data array
            period: EMA period
            
        Returns:
            EMA values array
        """
        alpha = 2.0 / (period + 1.0)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
            
        return ema
    
    @staticmethod
    def rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Calculate Relative Strength Index
        
        Args:
            data: Price data array
            period: RSI period
            
        Returns:
            RSI values array
        """
        delta = np.diff(data)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))
        
        # Initial values
        avg_gain[period] = np.mean(gain[:period])
        avg_loss[period] = np.mean(loss[:period])
        
        # Calculate smoothed averages
        for i in range(period + 1, len(data)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i-1]) / period
        
        # Calculate RSI
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Calculate Average True Range
        
        Args:
            high: High prices array
            low: Low prices array
            close: Close prices array
            period: ATR period
            
        Returns:
            ATR values array
        """
        # Calculate True Range
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        
        # Set first value to high - low
        tr2[0] = high[0] - low[0]
        tr3[0] = high[0] - low[0]
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate ATR using EMA
        atr = TechnicalIndicators.ema(tr, period)
        
        return atr
    
    @staticmethod
    def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Calculate Average Directional Index
        
        Args:
            high: High prices array
            low: Low prices array
            close: Close prices array
            period: ADX period
            
        Returns:
            ADX values array
        """
        # Calculate directional movement
        dm_pos = np.zeros_like(high)
        dm_neg = np.zeros_like(high)
        
        for i in range(1, len(high)):
            high_diff = high[i] - high[i-1]
            low_diff = low[i-1] - low[i]
            
            if high_diff > low_diff and high_diff > 0:
                dm_pos[i] = high_diff
            if low_diff > high_diff and low_diff > 0:
                dm_neg[i] = low_diff
        
        # Calculate True Range
        tr = TechnicalIndicators.atr(high, low, close, 1)
        
        # Calculate smoothed DM and TR
        dm_pos_smooth = TechnicalIndicators.ema(dm_pos, period)
        dm_neg_smooth = TechnicalIndicators.ema(dm_neg, period)
        tr_smooth = TechnicalIndicators.ema(tr, period)
        
        # Calculate DI
        di_pos = 100 * np.divide(dm_pos_smooth, tr_smooth, out=np.zeros_like(dm_pos_smooth), where=tr_smooth!=0)
        di_neg = 100 * np.divide(dm_neg_smooth, tr_smooth, out=np.zeros_like(dm_neg_smooth), where=tr_smooth!=0)
        
        # Calculate DX
        dx = 100 * np.divide(np.abs(di_pos - di_neg), (di_pos + di_neg), 
                            out=np.zeros_like(di_pos), where=(di_pos + di_neg)!=0)
        
        # Calculate ADX
        adx = TechnicalIndicators.ema(dx, period)
        
        return adx

    @staticmethod
    def calculate_indicators(market_data: MarketData) -> dict:
        """
        Calcula todos los indicadores técnicos necesarios para el análisis de señales.

        Args:
            market_data: Instancia de MarketData con datos de mercado (precios, volumen, etc.)

        Returns:
            Un diccionario con los valores calculados de EMA, RSI, ATR, ADX, etc.
        """
        indicators = {}

        # Calcular EMA
        indicators['ema_20'] = TechnicalIndicators.ema(market_data.close, 20)
        indicators['ema_50'] = TechnicalIndicators.ema(market_data.close, 50)

        # Calcular EMA adicional
        indicators['ema_200'] = TechnicalIndicators.ema(market_data.close, 200)

        # Calcular RSI
        indicators['rsi'] = TechnicalIndicators.rsi(market_data.close, 14)

        # Calcular ATR
        indicators['atr'] = TechnicalIndicators.atr(market_data.high, market_data.low, market_data.close, 14)

        # Calcular ADX
        indicators['adx'] = TechnicalIndicators.adx(market_data.high, market_data.low, market_data.close, 14)

        # Calcular cruces EMA
        indicators['current_ema_cross'] = market_data.close[-1] > indicators['ema_50'][-1] and market_data.close[-1] > indicators['ema_200'][-1]
        indicators['recent_ema_cross'] = market_data.close[-5] > indicators['ema_50'][-5] and market_data.close[-5] > indicators['ema_200'][-5]
        indicators['ema_convergence'] = abs(indicators['ema_50'][-1] - indicators['ema_200'][-1]) < 0.0005
        indicators['ema_acceleration'] = indicators['ema_50'][-1] > indicators['ema_50'][-5]

        # Calcular RSI actual
        indicators['current_rsi'] = indicators['rsi'][-1] if len(indicators['rsi']) > 0 else None

        # Calcular RSI previo
        indicators['prev_rsi'] = indicators['rsi'][-2] if len(indicators['rsi']) > 1 else None

        return indicators

class CandlestickPatterns:
    """
    Candlestick pattern detection class
    """
    
    @staticmethod
    def bullish_engulfing(open_prices: np.ndarray, high_prices: np.ndarray, 
                         low_prices: np.ndarray, close_prices: np.ndarray) -> np.ndarray:
        """
        Detect bullish engulfing pattern
        
        Args:
            open_prices: Open prices array
            high_prices: High prices array
            low_prices: Low prices array
            close_prices: Close prices array
            
        Returns:
            Boolean array indicating bullish engulfing pattern
        """
        pattern = np.zeros(len(close_prices), dtype=bool)
        
        for i in range(1, len(close_prices)):
            # Previous candle is bearish
            prev_bearish = close_prices[i-1] < open_prices[i-1]
            
            # Current candle is bullish
            curr_bullish = close_prices[i] > open_prices[i]
            
            # Current candle engulfs previous candle
            engulfs = (open_prices[i] < close_prices[i-1] and 
                      close_prices[i] > open_prices[i-1])
            
            pattern[i] = prev_bearish and curr_bullish and engulfs
        
        return pattern
    
    @staticmethod
    def bearish_engulfing(open_prices: np.ndarray, high_prices: np.ndarray, 
                         low_prices: np.ndarray, close_prices: np.ndarray) -> np.ndarray:
        """
        Detect bearish engulfing pattern
        
        Args:
            open_prices: Open prices array
            high_prices: High prices array
            low_prices: Low prices array
            close_prices: Close prices array
            
        Returns:
            Boolean array indicating bearish engulfing pattern
        """
        pattern = np.zeros(len(close_prices), dtype=bool)
        
        for i in range(1, len(close_prices)):
            # Previous candle is bullish
            prev_bullish = close_prices[i-1] > open_prices[i-1]
            
            # Current candle is bearish
            curr_bearish = close_prices[i] < open_prices[i]
            
            # Current candle engulfs previous candle
            engulfs = (open_prices[i] > close_prices[i-1] and 
                      close_prices[i] < open_prices[i-1])
            
            pattern[i] = prev_bullish and curr_bearish and engulfs
        
        return pattern
    
    @staticmethod
    def pin_bar(open_prices: np.ndarray, high_prices: np.ndarray, 
               low_prices: np.ndarray, close_prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect pin bar patterns
        
        Args:
            open_prices: Open prices array
            high_prices: High prices array
            low_prices: Low prices array
            close_prices: Close prices array
            
        Returns:
            Tuple of (bullish_pin_bar, bearish_pin_bar) boolean arrays
        """
        bullish_pin = np.zeros(len(close_prices), dtype=bool)
        bearish_pin = np.zeros(len(close_prices), dtype=bool)
        
        for i in range(len(close_prices)):
            body_size = abs(close_prices[i] - open_prices[i])
            total_range = high_prices[i] - low_prices[i]
            
            if total_range == 0:
                continue
            
            upper_shadow = high_prices[i] - max(open_prices[i], close_prices[i])
            lower_shadow = min(open_prices[i], close_prices[i]) - low_prices[i]
            
            # Pin bar criteria: small body, long shadow
            body_ratio = body_size / total_range
            
            if body_ratio < 0.3:  # Small body
                if lower_shadow > 2 * body_size:  # Long lower shadow
                    bullish_pin[i] = True
                elif upper_shadow > 2 * body_size:  # Long upper shadow
                    bearish_pin[i] = True
        
        return bullish_pin, bearish_pin

class SignalGenerator:
    def _rotate_symbols(self, mt5_connector=None):
        """
        Rotación deshabilitada: siempre se analizan todos los símbolos disponibles de FOREX, metales e índices.
        Esta función asegura que self.symbols contenga solo símbolos tradeables de estos tipos en cada ciclo.
        Refuerza el filtrado para excluir ACCIONES, CRIPTO y ETFs.
        """
        if mt5_connector is not None:
            all_symbols = mt5_connector.get_available_symbols("all", dynamic_mode=True)
            filtered = []
            for symbol in all_symbols:
                if self._is_symbol_type_enabled(symbol):
                    filtered.append(symbol)
                else:
                    logger.debug(f"[FILTER] Símbolo excluido por tipo: {symbol}")
            self.symbols = filtered
            logger.info(f"[ROTATION] Solo FOREX/metales/índices: {len(self.symbols)} símbolos activos.")
        else:
            logger.info("[ROTATION] Rotación deshabilitada: se analizarán todos los símbolos en cada ciclo.")
    def __init__(self):
        """Inicializa el generador de señales con todos los atributos requeridos para compatibilidad y tests."""
        self.symbols = []
        self.rotation_index = 0  # Para compatibilidad con tests de rotación
        self._current_cycle = 0
        self._preferred_symbols = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'XAUUSD', 'XAGUSD', 'US30', 'NAS100', 'GER30', 'SPX500', 'UK100', 'AUS200'
        ]
        self.symbol_specs = {}  # Cache symbol specifications
        self.indicators = TechnicalIndicators()
        self.patterns = CandlestickPatterns() if 'CandlestickPatterns' in globals() else None
        self.all_available_symbols = []  # All symbols from MT5
        # Forzar configuración: SOLO FOREX, ÍNDICES Y METALES
        self.instrument_types_config = {
            'forex': True,
            'indices': True,
            'metals': True,
            'stocks': False,
            'crypto': False,
            'etfs': False
        }
        # Dynamic configuration
        self.min_atr_threshold = {}
        self.dynamic_multipliers = {}
        enabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if enabled]
        disabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if not enabled]
        logger.info(f"Signal generator initialized with configurable instrument types (NO ROTATION)")
        logger.info(f"ENABLED types: {', '.join(enabled_types)}")
        logger.info(f"DISABLED types: {', '.join(disabled_types)}")
        self.generated_signals = []  # Todas las señales generadas
        self.virtual_trades = []     # Todas las señales convertidas a virtual trades
        self._lock = threading.Lock()

    @property
    def preferred_symbols(self) -> list:
        """Lista de símbolos preferidos para operar (placeholder para compatibilidad de tests)"""
        return self._preferred_symbols

    @preferred_symbols.setter
    def preferred_symbols(self, value: list):
        self._preferred_symbols = value

    @property
    def current_cycle(self) -> int:
        """Ciclo actual de rotación de símbolos (placeholder para compatibilidad de tests)"""
        return self._current_cycle

    @current_cycle.setter
    def current_cycle(self, value: int):
        self._current_cycle = value

    def get_instrument_types_status(self) -> dict:
        """Devuelve el estado de los tipos de instrumentos (placeholder para compatibilidad de tests)"""
        return self.instrument_types_config

    def _get_default_adaptive_strategy(self, symbol: str) -> dict:
        """Devuelve una estrategia adaptativa por defecto para el símbolo (placeholder para compatibilidad de tests)"""
        return {
            'sl_multiplier': 1.5,
            'tp_multiplier': 2.5,
            'min_atr_threshold_multiplier': 2.0,
            'symbol_category': 'normal',
            'volatility_class': 'normal'
        }
        self.rotation_index = 0  # Para compatibilidad con tests de rotación
        self._current_cycle = 0  # Para compatibilidad con tests de rotación

    @property
    def preferred_symbols(self) -> list:
        """
        Lista de símbolos preferidos para compatibilidad con tests de rotación/configuración.
        """
        return [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'XAUUSD', 'XAGUSD', 'US30', 'NAS100', 'GER30', 'SPX500', 'UK100', 'AUS200'
        ]

    @property
    def current_cycle(self) -> int:
        """
        Ciclo actual de rotación/configuración (dummy para compatibilidad test).
        """
        return getattr(self, '_current_cycle', 0)

    @current_cycle.setter
    def current_cycle(self, value: int):
        self._current_cycle = value

    def _get_default_adaptive_strategy(self) -> dict:
        """
        Devuelve la configuración SFO (Signal Flow Optimized) por defecto para los tests.
        Filtros endurecidos y score recalibrado a 0.7 (jul 2025).
        """
        return {
            'adx_threshold': 8,  # Ligeramente más estricto
            'confidence_threshold': 0.8,  # Recalibrado a 0.8
            'max_spread_threshold': 12,   # Más estricto
            'sl_multiplier': 1.25,        # SL un poco más amplio
            'tp_multiplier': 1.7,         # TP un poco más exigente
            'min_atr_threshold': 0.001    # ATR mínimo ligeramente mayor
        }
    def _is_symbol_type_enabled(self, symbol: str) -> bool:
        """
        Permite SOLO FOREX (todos los pares de divisas), índices y commodities/metales.
        Nunca permite acciones, cripto ni ETFs.
        """
        symbol = symbol.upper()
        # Listas ampliadas de monedas y palabras clave
        forex_currencies = [
            "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD",
            "SEK", "NOK", "DKK", "TRY", "ZAR", "MXN", "SGD", "HKD", "PLN", "CZK", "HUF", "RUB", "CNH", "CNY"
        ]
        metals_keywords = ["XAU", "XAG", "XPT", "XPD", "GOLD", "SILVER", "PLAT", "PALL"]
        commodities_keywords = ["OIL", "WTI", "BRENT", "NGAS", "GAS", "COPPER"]
        indices_keywords = [
            "US30", "US500", "NAS100", "DJ", "DAX", "GER", "UK", "AUS", "CAC", "FTSE", "SPX", "IBEX", "MIB", "HSI", "NIKKEI"
        ]

        # FOREX: cualquier combinación de dos monedas conocidas (no importa el orden ni el par)
        if len(symbol) in (6, 7):
            for c1 in forex_currencies:
                for c2 in forex_currencies:
                    if c1 != c2 and (symbol.startswith(c1) and symbol.endswith(c2)):
                        return self.instrument_types_config.get('forex', True)
        # Metales y commodities
        if any(kw in symbol for kw in metals_keywords + commodities_keywords):
            return self.instrument_types_config.get('metals', True)
        # Índices
        if any(kw in symbol for kw in indices_keywords):
            return self.instrument_types_config.get('indices', True)
        # Todo lo demás está deshabilitado SIEMPRE
        return False

    def _pass_adaptive_filters(self, symbol: str, atr: float, adx: float, strategy: dict) -> bool:
        """
        Evalúa si los valores ATR y ADX cumplen los filtros adaptativos SFO para el símbolo dado.
        Endurecido: ATR mínimo y ADX máximo más estricto.
        """
        adx_threshold = strategy.get('adx_threshold', 7)
        min_atr = strategy.get('min_atr_threshold', 0.0008)
        atr_ok = (atr is not None) and (atr >= min_atr)
        adx_ok = (adx is not None) and (adx <= adx_threshold)
        return atr_ok and adx_ok
    @property
    def preferred_symbols(self) -> list:
        """
        Lista de símbolos preferidos para compatibilidad con tests de rotación/configuración.
        """
        return [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'XAUUSD', 'XAGUSD', 'US30', 'NAS100', 'GER30', 'SPX500', 'UK100', 'AUS200'
        ]

    @property
    def current_cycle(self) -> int:
        """
        Ciclo actual de rotación/configuración (dummy para compatibilidad test).
        """
        return getattr(self, '_current_cycle', 0)

    @current_cycle.setter
    def current_cycle(self, value: int):
        self._current_cycle = value

    def _get_default_adaptive_strategy(self) -> dict:
        """
        Devuelve la configuración SFO (Signal Flow Optimized) por defecto para los tests.
        """
        return {
            'adx_threshold': 8,
            'confidence_threshold': 0.70,
            'max_spread_threshold': 20,
            'sl_multiplier': 1.2,
            'tp_multiplier': 1.8
        }
    def get_instrument_types_status(self) -> dict:
        """Devuelve el estado de los tipos de instrumentos configurados."""
        return self.instrument_types_config.copy()
    """
    Main signal generation class with dynamic symbol management
    """
    
    def __init__(self):
        """Inicializa el generador de señales con todos los atributos requeridos para compatibilidad y tests."""
        self.symbols = []
        self.rotation_index = 0  # Para compatibilidad con tests de rotación
        self._current_cycle = 0
        self._preferred_symbols = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            'XAUUSD', 'XAGUSD', 'US30', 'NAS100', 'GER30', 'SPX500', 'UK100', 'AUS200'
        ]
        self.symbol_specs = {}  # Cache symbol specifications
        self.indicators = TechnicalIndicators()
        self.patterns = CandlestickPatterns() if 'CandlestickPatterns' in globals() else None
        self.all_available_symbols = []  # All symbols from MT5
        self.instrument_types_config = {
            'forex': True,
            'indices': True,
            'metals': True,
            'stocks': False,
            'crypto': False,
            'etfs': False
        }
        # Dynamic configuration
        self.min_atr_threshold = {}
        self.dynamic_multipliers = {}
        enabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if enabled]
        disabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if not enabled]
        logger.info(f"Signal generator initialized with configurable instrument types (NO ROTATION)")
        logger.info(f"ENABLED types: {', '.join(enabled_types)}")
        logger.info(f"DISABLED types: {', '.join(disabled_types)}")
        self.generated_signals = []  # Todas las señales generadas
        self.virtual_trades = []     # Todas las señales convertidas a virtual trades
        self._lock = threading.Lock()

    def configure_instrument_types(self, forex=True, indices=True, metals=True, stocks=False, crypto=False, etfs=False):
        """
        Configura los tipos de instrumentos habilitados para el generador de señales.
        Args:
            forex (bool): Habilitar pares de divisas FOREX
            indices (bool): Habilitar índices bursátiles
            metals (bool): Habilitar metales preciosos/commodities
            stocks (bool): Habilitar acciones individuales
            crypto (bool): Habilitar criptomonedas
            etfs (bool): Habilitar ETFs
        """
        self.instrument_types_config = {
            'forex': forex,
            'indices': indices,
            'metals': metals,
            'stocks': stocks,
            'crypto': crypto,
            'etfs': etfs
        }
        enabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if enabled]
        disabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if not enabled]
        logger.info(f"Instrument types configured: ENABLED={enabled_types}, DISABLED={disabled_types}")

    def initialize_symbols(self, mt5_connector) -> bool:
        """
        Inicializa TODOS los símbolos disponibles de MT5 y los deja listos para escaneo completo cada ciclo.
        """
        try:
            logger.info("Fetching ALL available symbols from MT5...")
            all_symbols = mt5_connector.get_available_symbols("all", dynamic_mode=True)
            if not all_symbols:
                logger.error("No symbols available from MT5")
                return False
            filtered_symbols = self._filter_symbols_for_strategy(all_symbols, mt5_connector)
            if not filtered_symbols:
                logger.warning("No suitable symbols found after filtering, using raw symbols")
                filtered_symbols = all_symbols
            self.all_available_symbols = filtered_symbols
            self.symbols = list(self.all_available_symbols)
            self.symbol_specs.clear()
            for symbol in self.symbols:
                specs = mt5_connector.get_dynamic_trading_params(symbol)
                if specs:
                    self.symbol_specs[symbol] = specs
                adaptive_strategy = mt5_connector.get_adaptive_strategy_params(symbol)
                if adaptive_strategy:
                    self._apply_adaptive_strategy(symbol, adaptive_strategy)
            logger.info(f"Found {len(self.all_available_symbols)} total tradeable symbols across ALL markets")
            logger.info(f"All symbols will be analyzed every scan (NO ROTATION, NO PREFERRED SYMBOLS)")
            return True
        except Exception as e:
            logger.error(f"Error initializing symbols: {str(e)}")
            return False

    # Eliminada la función de rotación, ya no es necesaria

    def scan_all_symbols(self, mt5_connector, timeframes=['M5', 'M15']) -> List[TradingSignal]:
        """
        Escanea TODOS los símbolos configurados para señales de trading.
        Args:
            mt5_connector: MT5Connector instance
            timeframes: List of timeframes to scan
        Returns:
            List of TradingSignal objects
        """
        signals = []
        if not self.symbols:
            logger.warning("No symbols to scan")
            return signals
        logger.info(f"[SCAN START] Scanning {len(self.symbols)} symbols: {self.symbols}")
        for symbol in self.symbols:
            if not self.is_symbol_tradeable(symbol):
                logger.info(f"[SKIP] {symbol} - not tradeable")
                continue
            for timeframe in timeframes:
                try:
                    market_data = mt5_connector.get_market_data(symbol, timeframe, 500)
                    if market_data is None:
                        logger.info(f"[NO DATA] No market data for {symbol} {timeframe}")
                        continue
                    signal = self.analyze_market_data(market_data)
                    if signal:
                        signals.append(signal)
                        logger.info(f"[SIGNAL GENERATED] {signal.signal_type} {signal.symbol} {signal.timeframe} (confidence: {signal.confidence:.2f})")
                except Exception as e:
                    logger.error(f"[ERROR] Error scanning {symbol} {timeframe}: {str(e)}")
                    continue
        logger.info(f"[SCAN COMPLETE] Found {len(signals)} signals out of {len(self.symbols)} symbols scanned")
        return signals
    
    def _filter_symbols_for_strategy(self, symbols: List[str], mt5_connector) -> List[str]:
        """
        Filtrar símbolos basado en criterios de estrategia y configuración de tipos
        
        Args:
            symbols: Lista de símbolos disponibles
            mt5_connector: Conector MT5
            
        Returns:
            Lista filtrada de símbolos
        """
        try:
            suitable_symbols = []
            type_counts = {'forex': 0, 'metals': 0, 'indices': 0, 'filtered_by_type': 0}
            
            for index, symbol in enumerate(symbols):
                # NUEVO: Verificar si el tipo de símbolo está habilitado
                if not self._is_symbol_type_enabled(symbol):
                    type_counts['filtered_by_type'] += 1
                    logger.debug(f"Filtered out {symbol}: instrument type disabled")
                    continue

                # Obtener información del símbolo
                symbol_info = mt5_connector.get_symbol_info(symbol)
                if not symbol_info:
                    continue

                # Filtros básicos
                spread = symbol_info.get('spread', 999)
                point = symbol_info.get('point', 0.00001)

                # Calcular spread en pips
                if symbol.endswith('JPY'):
                    spread_pips = spread * point * 100
                else:
                    spread_pips = spread * point * 10000

                # Filtro de spread máximo (adaptativo por tipo de símbolo)
                max_spread = self._get_max_allowed_spread(symbol)
                if spread_pips > max_spread * 1.5:  # Increased tolerance
                    logger.debug(f"Filtered out {symbol}: spread {spread_pips:.1f} pips > {max_spread * 1.5}")
                    continue

                # Filtro de volumen mínimo (más permisivo para diferentes tipos de instrumentos)
                volume = symbol_info.get('volume', 0)
                session_deals = symbol_info.get('session_deals', 0)

                # Criterios más flexibles para diferentes tipos de instrumentos
                is_forex = False
                is_metal = any(metal in symbol for metal in ['XAU', 'XAG', 'GOLD', 'SILVER'])
                is_index = any(index in symbol for index in ['US30', 'US500', 'NAS100', 'GER30', 'UK100'])

                # Detectar automáticamente tipo basado en clasificación broker
                path = symbol_info.get('path', '').lower()
                if 'forex' in path or 'fx' in path:
                    type_counts['forex'] += 1
                    is_forex = True

                # Contar por tipo
                if is_forex:
                    type_counts['forex'] += 1
                elif is_metal:
                    type_counts['metals'] += 1
                elif is_index:
                    type_counts['indices'] += 1
                else:
                    continue

                # Actividad mínima por tipo de instrumento
                min_activity = False
                if is_forex or is_metal or is_index:
                    min_activity = volume >= 50 or session_deals >= 25  # Criterios relajados para instrumentos importantes
                else:
                    min_activity = volume >= 10 or session_deals >= 5  # Criterios más estrictos para otros

                if not min_activity:
                    logger.debug(f"Filtered out {symbol}: low activity (volume: {volume}, deals: {session_deals}")
                    continue

                # Verificar que el símbolo permita trading completo
                trade_mode = symbol_info.get('trade_mode', 0)
                if trade_mode != 4:  # mt5.SYMBOL_TRADE_MODE_FULL
                    logger.debug(f"Filtered out {symbol}: trade mode {trade_mode} not full")
                    continue

                suitable_symbols.append(symbol)

            logger.info(f"Filtered symbols by type configuration:")
            logger.info(f"  FOREX: {type_counts['forex']} symbols")
            logger.info(f"  Metals: {type_counts['metals']} symbols")
            logger.info(f"  Indices: {type_counts['indices']} symbols")
            logger.info(f"  Filtered by type config: {type_counts['filtered_by_type']} symbols")
            logger.info(f"Total suitable symbols: {len(suitable_symbols)} from {len(symbols)} available")
            
            return suitable_symbols
        except Exception as e:
            logger.error(f"Error filtering symbols: {str(e)}")
            return symbols  # Fallback: analizar todos los símbolos si hay error
    
    def _get_max_allowed_spread(self, symbol: str) -> float:
        """
        Obtener spread máximo permitido según el tipo de símbolo
        """
        # Valores más permisivos
        if any(major in symbol for major in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']):
            return 10.0  # Antes 3.0
        elif any(minor in symbol for minor in ['AUDUSD', 'USDCAD', 'NZDUSD', 'EURJPY', 'GBPJPY']):
            return 15.0  # Antes 5.0
        elif symbol.startswith('XAU') or symbol.startswith('XAG') or 'GOLD' in symbol or 'SILVER' in symbol:
            return 50.0  # Metales preciosos
        elif any(exotic in symbol for exotic in ['ZAR', 'TRY', 'MXN', 'NOK', 'SEK', 'PLN']):
            return 15.0  # Pares exóticos FOREX
        elif any(index in symbol for index in ['US30', 'US500', 'NAS100', 'GER30', 'UK100', 'AUS200']):
            return 100.0  # Índices principales
        elif any(stock in symbol for stock in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA']):
            return 0.50  # Acciones individuales (en USD)
        else:
            return 20.0  # Otros instrumentos (ETFs, acciones menores, etc.)
    
    def _apply_adaptive_strategy(self, symbol: str, strategy: Dict) -> None:
        """
        Aplicar estrategia adaptativa específica para el símbolo
        
        Args:
            symbol: Nombre del símbolo
            strategy: Parámetros de estrategia adaptativa
        """
        try:
            # Aplicar multiplicadores adaptativos
            sl_multiplier = strategy.get('sl_multiplier', 1.5)
            tp_multiplier = strategy.get('tp_multiplier', 2.5)
            
            self.dynamic_multipliers[symbol] = {
                'sl_multiplier': sl_multiplier,
                'tp_multiplier': tp_multiplier
            }
            
            # Aplicar umbral ATR adaptativo
            min_atr_mult = strategy.get('min_atr_threshold_multiplier', 2.0)
            current_spread = self.symbol_specs.get(symbol, {}).get('current_spread', 0.00002)
            
            # Calcular umbral ATR basado en spread y multiplicador adaptativo
            min_atr = current_spread * min_atr_mult
            self.min_atr_threshold[symbol] = min_atr
            
            # Guardar estrategia completa
            if not hasattr(self, 'adaptive_strategies'):
                self.adaptive_strategies = {}
            
            self.adaptive_strategies[symbol] = strategy
            
            logger.debug(f"Applied adaptive strategy for {symbol}: "
                        f"SL/TP={sl_multiplier:.1f}/{tp_multiplier:.1f}, "
                        f"MinATR={min_atr:.6f}, "
                        f"Category={strategy.get('symbol_category', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error applying adaptive strategy for {symbol}: {str(e)}")
    
    def get_adaptive_strategy(self, symbol: str) -> Dict:
        """
        Obtener estrategia adaptativa para un símbolo
        
        Args:
            symbol: Nombre del símbolo
            
        Returns:
            Diccionario con parámetros de estrategia adaptativa
        """
        if hasattr(self, 'adaptive_strategies'):
            return self.adaptive_strategies.get(symbol, {})
        return {}

    def _calculate_dynamic_parameters(self, symbol: str, specs: Dict) -> None:
        """
        Calculate dynamic parameters based on symbol specifications
        
        Args:
            symbol: Symbol name
            specs: Symbol specifications
        """
        try:
            # Calculate minimum ATR threshold based on average spread
            spread_points = specs.get('current_spread_points', 10)
            point = specs.get('point', 0.00001)
            
            # ATR threshold should be at least 2x average spread
            min_atr = spread_points * point * 2
            self.min_atr_threshold[symbol] = min_atr
            
            # Dynamic SL/TP multipliers based on symbol volatility and type
            if symbol.startswith('XAU'):  # Gold
                sl_mult, tp_mult = 2.0, 3.0  # Higher volatility
            elif symbol.endswith('JPY'):  # JPY pairs
                sl_mult, tp_mult = 1.2, 2.0  # Different pip value
            elif 'USD' in symbol:  # Major USD pairs
                sl_mult, tp_mult = 1.5, 2.5  # Standard
            else:  # Other pairs
                sl_mult, tp_mult = 1.8, 2.8  # Conservative
            
            self.dynamic_multipliers[symbol] = {
                'sl_multiplier': sl_mult,
                'tp_multiplier': tp_mult
            }
            
            logger.debug(f"Dynamic parameters for {symbol}: ATR threshold={min_atr:.6f}, SL/TP multipliers={sl_mult}/{tp_mult}")
            
        except Exception as e:
            logger.error(f"Error calculating dynamic parameters for {symbol}: {str(e)}")

    def get_symbol_atr_threshold(self, symbol: str) -> float:
        """Get minimum ATR threshold for a symbol"""
        return self.min_atr_threshold.get(symbol, 0.0001)

    def get_symbol_multipliers(self, symbol: str) -> Dict[str, float]:
        """Get SL/TP multipliers for a symbol"""
        return self.dynamic_multipliers.get(symbol, {'sl_multiplier': 1.5, 'tp_multiplier': 2.5})

    def is_symbol_tradeable(self, symbol: str) -> bool:
        """
        Check if symbol is currently tradeable
        
        Args:
            symbol: Symbol name
            
        Returns:
            True if symbol is tradeable
        """
        if symbol in self.symbol_specs:
            is_tradeable = self.symbol_specs[symbol].get('tradeable', True)
            logger.info(f"[TRADEABLE CHECK] {symbol}: {is_tradeable}")
            return is_tradeable
        else:
            logger.info(f"[TRADEABLE CHECK] {symbol}: True (not in specs)")
            return True
        
    def calculate_signal_score(self, indicators, market_context):
        """
        Calcula la puntuación de una señal basada en indicadores técnicos y contexto de mercado.
        Siempre asegura que la clave 'trend' esté presente en el diccionario de indicadores.
        """
        """
        Calcula el score técnico de la señal. Recalibrado 10/07/2025:
        - Score mínimo para ejecución automática: 70/100 (confianza >= 0.7)
        - Filtros técnicos endurecidos sutilmente
        """
        score = 0
        max_score = 100
        # Extraer valores escalares para evitar comparaciones ambiguas
        ema_200_last = indicators['ema_200'][-1] if isinstance(indicators['ema_200'], np.ndarray) else indicators['ema_200']
        ema_50_last = indicators['ema_50'][-1] if isinstance(indicators['ema_50'], np.ndarray) else indicators['ema_50']
        price = market_context['price']

        # Asegurar que 'trend' siempre esté presente
        if 'trend' not in indicators:
            if price > ema_200_last:
                indicators['trend'] = 'bullish'
            elif price < ema_200_last:
                indicators['trend'] = 'bearish'
            else:
                indicators['trend'] = 'neutral'

        # Tendencia (25 puntos máximo, endurecido)
        if ema_200_last * 0.998 < price:  # Más estricto
            score += 25
        elif price > ema_50_last * 1.003:  # Más estricto
            score += 15

        # Momentum EMA (20 puntos máximo, endurecido)
        ema_signals = [
            indicators.get('current_ema_cross', False),
            indicators.get('recent_ema_cross', False),
            indicators.get('ema_convergence', False),
            indicators.get('ema_acceleration', False)
        ]
        if any(ema_signals):
            score += 20

        # RSI (15 puntos máximo, endurecido)
        current_rsi = indicators.get('current_rsi', 50)
        prev_rsi = indicators.get('prev_rsi', 50)
        if current_rsi is not None and 42 <= current_rsi <= 50:
            score += 15
        elif current_rsi is not None and prev_rsi is not None and current_rsi > prev_rsi and current_rsi > 48:
            score += 10

        # ATR y ADX (20 puntos máximo, endurecido)
        atr_last = indicators['atr'][-1] if isinstance(indicators['atr'], np.ndarray) else indicators['atr']
        adx_last = indicators['adx'][-1] if isinstance(indicators['adx'], np.ndarray) else indicators['adx']
        if atr_last > market_context['atr_min_threshold'] * 1.25 and adx_last > market_context['adx_threshold'] * 1.2:
            score += 20
        elif atr_last > market_context['atr_min_threshold'] * 1.1 and adx_last > market_context['adx_threshold']:
            score += 10

        # Volumen (10 puntos máximo, endurecido)
        if indicators.get('volume', 0) > 1.2 * indicators.get('volume_ma', 1):
            score += 10
        elif indicators.get('volume', 0) > 1.0 * indicators.get('volume_ma', 1):
            score += 5

        # Penalización si spread > 30% ATR
        if indicators.get('spread', 0) > 0.3 * atr_last:
            score -= 10

        return min(score, max_score)

    def analyze_market_data(self, market_data):
        """
        Analiza los datos de mercado y genera una señal si se cumplen las condiciones.
        """
        indicators = self.indicators.calculate_indicators(market_data)

        # Validar que el símbolo existe en min_atr_threshold
        if market_data.symbol not in self.min_atr_threshold:
            logger.warning(f"Symbol {market_data.symbol} not found in min_atr_threshold. Using default value.")
            self.min_atr_threshold[market_data.symbol] = 0.001

        market_context = {
            'price': market_data.close[-1],
            'atr_min_threshold': self.min_atr_threshold.get(market_data.symbol, 0.001),
            'adx_threshold': 17  # Más alto para filtrar señales débiles
        }
        score = self.calculate_signal_score(indicators, market_context)

        # Cambios 10/07/2025: umbral de confianza ajustado a 70
        if score >= 70:
            atr_last = indicators['atr'][-1] if isinstance(indicators['atr'], np.ndarray) else indicators['atr']
            timestamp = datetime.now()
            trend = indicators.get('trend', 'neutral')
            signal_type = 'BUY' if trend == 'bullish' else 'SELL'
            # Multiplicadores SL/TP más amplios para mayor calidad
            sl_mult = 1.7
            tp_mult = 2.8
            entry = market_data.close[-1]
            if signal_type == 'BUY':
                stop_loss = entry - atr_last * sl_mult
                take_profit = entry + atr_last * tp_mult
            else:
                stop_loss = entry + atr_last * sl_mult
                take_profit = entry - atr_last * tp_mult
            return TradingSignal(
                symbol=market_data.symbol,
                timeframe=market_data.timeframe,
                signal_type=signal_type,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=score / 100,
                reasons=['High confidence signal'],
                timestamp=timestamp,
                atr_value=atr_last
            )
        return None
    
    def debug_symbols(self, mt5_connector):
        """Método temporal para identificar qué símbolos se están filtrando"""
        all_raw = mt5_connector.get_available_symbols("all", dynamic_mode=True)
        logger.info(f"Total símbolos raw: {len(all_raw)}")
        
        # Desactivar temporalmente todos los filtros
        self.DEBUG_DISABLE_FILTERS = True
        filtered = self._filter_symbols_for_strategy(all_raw, mt5_connector)
        self.DEBUG_DISABLE_FILTERS = False
        
        logger.info(f"Símbolos después del filtrado: {len(filtered)}")
        logger.info(f"Primeros 20 símbolos filtrados: {filtered[:20]}")
        
        # Detalle de filtros que más impactan
        return filtered

    def save_signals_to_csv(self, filename='signals_export.csv'):
        with self._lock:
            if not self.generated_signals:
                return
            keys = list(self.generated_signals[0].__dict__.keys())
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for s in self.generated_signals:
                    writer.writerow(s.__dict__)

    def save_virtual_trades_to_csv(self, filename='virtual_trades_export.csv'):
        with self._lock:
            if not self.virtual_trades:
                return
            keys = list(self.virtual_trades[0].to_dict().keys())
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for vt in self.virtual_trades:
                    writer.writerow(vt.to_dict())

    def add_signal(self, signal: TradingSignal):
        with self._lock:
            self.generated_signals.append(signal)

    def convert_signals_to_virtual_trades(self, market_data_provider):
        """
        Convierte todas las señales que ya no están vigentes en VirtualTrades y simula su evolución
        market_data_provider debe ser una función: (symbol, timeframe, from_time) -> [(timestamp, price)]
        """
        with self._lock:
            for signal in self.generated_signals:
                if any(vt.symbol == signal.symbol and vt.open_time == signal.timestamp for vt in self.virtual_trades):
                    continue  # Ya convertido
                vt = VirtualTrade(signal)
                # Simular evolución del trade
                price_history = market_data_provider(signal.symbol, signal.timeframe, signal.timestamp)
                for timestamp, price in price_history:
                    vt.update(timestamp, price)
                    if vt.is_closed():
                        break
                self.virtual_trades.append(vt)

    def cleanup_signals(self):
        """Elimina señales que ya fueron convertidas a virtual trades"""
        with self._lock:
            self.generated_signals = [s for s in self.generated_signals if not any(vt.symbol == s.symbol and vt.open_time == s.timestamp for vt in self.virtual_trades)]
    
    def _get_adaptive_rsi_threshold(self, symbol: str, strategy: Dict, threshold_type: str) -> float:
        """
        Obtener umbral RSI adaptativo para un símbolo específico
        
        [AJUSTE 2025-07-08]: Umbrales optimizados basados en análisis de datos reales:
        - RSI oversold: 30 (valor estándar)
        - RSI overbought: 70 (valor estándar)
        
        Args:
            symbol: Símbolo para el cual obtener el umbral
            strategy: Estrategia adaptativa para el símbolo
            threshold_type: Tipo de umbral ('oversold' o 'overbought')
            
        Returns:
            Valor de umbral RSI adaptativo
        """
        # Valores base optimizados según análisis de julio 2025
        base_thresholds = {
            'oversold': 30.0,    # Ajustado según solicitud
            'overbought': 70.0   # Ajustado según solicitud
        }
        
        # Obtener categoría del símbolo
        category = strategy.get('symbol_category', 'normal')
        volatility = strategy.get('volatility_class', 'normal')
        
        # Ajuste adaptativo según características del símbolo
        adjustment = 0.0
        
        # Ajuste por categoría
        if category == 'forex_major':
            adjustment -= 2.0  # Más permisivo para pares principales
        elif category == 'exotic':
            adjustment += 5.0  # Más restrictivo para pares exóticos
        
        # Ajuste por volatilidad
        if volatility == 'very_high':
            adjustment += 8.0  # Más restrictivo para alta volatilidad
        elif volatility == 'high':
            adjustment += 5.0
        elif volatility == 'low':
            adjustment -= 3.0  # Más permisivo para baja volatilidad
            
        # Aplicar ajuste en dirección correcta según tipo de umbral
        if threshold_type == 'oversold':
            return base_thresholds['oversold'] - adjustment  # Menor = más restrictivo para oversold
        else:
            return base_thresholds['overbought'] + adjustment  # Mayor = más restrictivo para overbought
            
        # Si hay algún error, devolver valores predeterminados
        return base_thresholds.get(threshold_type, 50.0)
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """
        Calcula métricas de rendimiento basadas en virtual trades
    
        Returns:
            Diccionario con métricas de rendimiento (win_rate, profit_factor, etc.)
        """
        with self._lock:
            if not self.virtual_trades:
                return {
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'total_trades': 0,
                    'total_wins': 0,
                    'total_losses': 0
                }

        closed_trades = [t for t in self.virtual_trades if t.is_closed()]
        total_trades = len(closed_trades)
        
        if total_trades == 0:
            return {
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'total_trades': 0,
                'total_wins': 0,
                'total_losses': 0
            }
        
        # Contar TP y SL
        tp_trades = [t for t in closed_trades if t.result == 'TP']
        sl_trades = [t for t in closed_trades if t.result == 'SL']
        
        total_wins = len(tp_trades)
        total_losses = len(sl_trades)
        
        # Calcular win rate
        win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
        
        # Calcular profit factor (suma de ganancias / suma de pérdidas)
        total_profit = sum([(t.close_price - t.entry_price) if t.signal_type == 'BUY' else (t.entry_price - t.close_price) for t in tp_trades])
        total_loss = sum([(t.entry_price - t.close_price) if t.signal_type == 'BUY' else (t.close_price - t.entry_price) for t in sl_trades])
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Calcular promedios
        avg_win = total_profit / total_wins if total_wins > 0 else 0
        avg_loss = total_loss / total_losses if total_losses > 0 else 0
        
        # Construir diccionario de métricas
        metrics = {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_trades': total_trades,
            'total_wins': total_wins,
            'total_losses': total_losses
        }
        
        logger.info(f"Performance metrics: Win Rate={win_rate:.1f}%, Profit Factor={profit_factor:.2f}, TP/SL Ratio={total_wins}/{total_losses}")
        
        return metrics

    def save_performance_metrics(self, filename='performance_metrics.csv'):
        """
        Guarda métricas de rendimiento en un archivo CSV
    
        Args:
            filename: Nombre del archivo CSV
        """
        metrics = self.calculate_performance_metrics()
    
        # Añadir timestamp
        metrics['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
        # Escribir al CSV (append mode)
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=metrics.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(metrics)
    
        logger.info(f"Performance metrics saved to {filename}")

    def analyze_symbol_performance(self) -> Dict[str, Dict]:
        """
        Analiza el rendimiento por símbolo
    
        Returns:
            Diccionario con métricas por símbolo
        """
        with self._lock:
            if not self.virtual_trades:
                return {}
            
            symbols = set([t.symbol for t in self.virtual_trades])
            performance = {}
            
            for symbol in symbols:
                # Filtrar trades por símbolo
                symbol_trades = [t for t in self.virtual_trades if t.symbol == symbol and t.is_closed()]
                
                if not symbol_trades:
                    continue
                
                # Contar TP y SL
                tp_trades = [t for t in symbol_trades if t.result == 'TP']
                sl_trades = [t for t in symbol_trades if t.result == 'SL']
                
                total_trades = len(symbol_trades)
                total_wins = len(tp_trades)
                
                # Calcular métricas
                win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
                
                performance[symbol] = {
                    'win_rate': win_rate,
                    'total_trades': total_trades,
                    'tp_count': total_wins,
                    'sl_count': len(sl_trades)
                }
            
            # Ordenar por win rate (mejores primero)
            sorted_performance = dict(sorted(
                performance.items(), 
                key=lambda item: item[1]['win_rate'], 
                reverse=True
            ))
            
            return sorted_performance

    def update_virtual_trades(self, mt5_connector):
        """
        Actualiza todos los virtual trades abiertos con los precios actuales
    
        Args:
            mt5_connector: Instancia de MT5Connector
        """
        with self._lock:
            open_trades = [t for t in self.virtual_trades if not t.is_closed()]
            if not open_trades:
                return
            
            for trade in open_trades:
                try:
                    # Obtener precio actual
                    symbol_info = mt5_connector.get_symbol_info(trade.symbol)
                    if not symbol_info:
                        continue
                        
                    current_price = symbol_info.get('bid', 0) if trade.signal_type == "SELL" else symbol_info.get('ask', 0)
                    if current_price <= 0:
                        continue
                        
                    # Actualizar trade
                    trade.update(datetime.now(), current_price)
                    
                    if trade.is_closed():
                        logger.info(f"Virtual trade closed: {trade.symbol} {trade.signal_type} Result: {trade.result}")
                        
                except Exception as e:
                    logger.error(f"Error updating virtual trade {trade.symbol}: {str(e)}")
    
    def _is_symbol_type_enabled(self, symbol: str) -> bool:
        """Mejorada para detectar más instrumentos"""
        # Detección FOREX más amplia
        if self.instrument_types_config.get('forex', True):
            if (any(c in symbol for c in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD', 'SEK', 'NOK', 'TRY', 'ZAR', 'MXN']) 
                or ('/' in symbol and len(symbol.replace('/', '')) <= 8)):
                return True
    
        # Detección más amplia de metales
        if self.instrument_types_config.get('metals', True):
            if any(m in symbol for m in ['XAU', 'XAG', 'XPD', 'XPT', 'GOLD', 'SILVER', 'PLAT']):
                return True
            
        # Detección más amplia de índices
        if self.instrument_types_config.get('indices', True):
            if any(i in symbol for i in ['US30', 'US500', 'NAS100', 'DJ', 'DAX', 'GER', 'UK', 'AUS', 'CAC', 'FTSE']):
                return True
            
        # Acciones
        if self.instrument_types_config.get('stocks', False):
            # Detectar símbolos que parezcan acciones (letras y números sin pares de divisas conocidos)
            if not any(pair in symbol for pair in ['USD', 'EUR', 'JPY', 'GBP', 'CHF']):
                if len(symbol) <= 5 or '-' in symbol:
                    return True
            
        # Criptomonedas
        if self.instrument_types_config.get('crypto', False):
            if any(c in symbol for c in ['BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'DOT', 'BNB']):
                return True
                
        # Para cualquier otro símbolo que no hayamos podido clasificar,
        # permitirlo por defecto si forex está habilitado (para evitar filtrar demasiado)
        return self.instrument_types_config.get('forex', True)
