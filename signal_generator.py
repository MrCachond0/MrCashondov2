from calendar_blackout import CalendarBlackout

class SignalGenerator:
    def filter_and_rank_signals(self, signals, mt5_connector):
        """
        Filtra y rankea señales según criterios de probabilidad, spread, tipo de par, timeframe, ATR/spread y volumen.
        Devuelve solo las mejores señales ordenadas por score.
        """
        def get_pair_type(symbol):
            majors = ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
            minors = ['EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CHFJPY', 'EURCAD', 'EURAUD', 'GBPCAD', 'NZDJPY', 'CADJPY', 'AUDCAD', 'AUDNZD', 'NZDCAD', 'GBPAUD', 'GBPNZD']
            s = symbol.replace('m','').replace('_','').upper()
            if s in majors:
                return 4
            if s in minors:
                return 3
            if any(x in s for x in ['XAU','XAG','GOLD','SILVER']):
                return 2
            if any(x in s for x in ['US30','NAS','GER','UK','SPX','DJ','INDEX']):
                return 1
            return 0

        filtered = []
        for sig in signals:
            # Spread filter
            symbol_info = mt5_connector.get_symbol_info(sig.symbol)
            spread = symbol_info.get('spread', 0)
            # Filtro por tipo
            if get_pair_type(sig.symbol) == 1 and spread > 200:
                continue
            elif get_pair_type(sig.symbol) >= 2 and spread > 35:
                continue
            # ATR/Spread filter
            atr = getattr(sig, 'atr_value', None)
            if atr is not None and spread > 0 and (atr/spread) < 2:
                continue
            # Volumen filter
            vol_actual = symbol_info.get('current_volume_real', 0)
            prom_20 = symbol_info.get('volumehigh', 1)  # fallback
            if prom_20 == 0:
                prom_20 = 1
            volume_score = vol_actual / prom_20 if prom_20 else 1
            if volume_score < 0.7:
                continue
            # Confianza
            if getattr(sig, 'confidence', 0) < 0.8:
                continue
            # Score para ranking
            score = (
                2.0 * getattr(sig, 'confidence', 0) - 0.01 * spread +
                0.2 * get_pair_type(sig.symbol) +
                0.1 * (1 if sig.timeframe in ['H1','H4'] else 0) +
                (0.2 * min(atr/spread, 3) if (atr and spread) else 0)
            )
            filtered.append((score, sig))
        # Ordenar por score descendente
        filtered.sort(key=lambda x: x[0], reverse=True)
        return [s for _,s in filtered]
    # ADVERTENCIA: Para optimización de rendimiento, priorizar la rotación inteligente de símbolos y evitar latencias por análisis multiframe innecesario.
    # Sugerencia: Implementar caché de datos de mercado y limitar el análisis multitemporal solo a símbolos con condiciones previas favorables.
    def __init__(self, instrument_manager=None):
        self.instrument_manager = instrument_manager or InstrumentManager()
        self.logger = logger
        self.confidence_threshold = 0.7
        self.timeframes = ['M5', 'M15', 'H1']
        self.preferred_symbols = []
        self.calendar_blackout = CalendarBlackout()

    def scan_all_symbols(self, mt5_connector, timeframes=None):
        """
        Escanea todos los símbolos disponibles y genera señales válidas con análisis multitemporal, confluencias y filtro de sesiones activas.
        """
        from context_analyzer import analyze_context, analyze_key_levels, get_fibonacci_levels
        from filters.pre_filters import has_sufficient_data, spread_within_reasonable_bounds, symbol_is_tradeable
        signals = []
        symbols = self.instrument_manager.load_symbols()
        tfs = timeframes or self.timeframes
        for symbol in symbols:
            # --- Blackout por calendario económico (Fase 5) ---
            if self.calendar_blackout.is_blackout(symbol):
                self.logger.info(f"[BLACKOUT] {symbol}: Blackout activo por evento económico de alto impacto. No operar.")
                continue
            # --- Análisis multitemporal ---
            data_h4 = mt5_connector.get_market_data(symbol, 'H4', 300)
            data_h1 = mt5_connector.get_market_data(symbol, 'H1', 300)
            if not data_h4 or not data_h1:
                continue
            close_h4 = data_h4['close']
            high_h4 = data_h4['high']
            low_h4 = data_h4['low']
            context = analyze_context(close_h4, high_h4, low_h4)
            trend_macro = context['trend']
            # --- Filtro por sesiones activas ---
            if not self.is_optimal_trading_hour(mt5_connector, symbol):
                # Excepción: instrumentos especiales fuera de horario si volumen alto
                if not self.is_special_instrument(symbol):
                    continue
                data_m5 = mt5_connector.get_market_data(symbol, 'M5', 100)
                if not data_m5 or 'tick_volume' not in data_m5:
                    continue
                tick_vol = data_m5['tick_volume']
                if len(tick_vol) < 20 or tick_vol[-1] < np.mean(tick_vol[-20:]):
                    continue
            # Descartar pares si falta 1h o menos para cierre de mercado
            if self.is_market_closing_soon(mt5_connector, symbol, threshold_minutes=60):
                self.logger.info(f"{symbol}: Falta 1h o menos para cierre de mercado, descartando para evitar overnight.")
                continue
            # --- Fin análisis multitemporal ---
            for tf in tfs:
                market_data = mt5_connector.get_market_data(symbol, tf, 300)
                if not market_data:
                    continue
                # Añadir tendencia macro y contexto al market_data
                market_data['trend_macro'] = trend_macro
                market_data['context'] = context
                # --- Confluencias ---
                reasons = []
                # 1. Tendencia macro alineada
                close = np.array(market_data['close'])
                if trend_macro == 'bullish' and close[-1] < context.get('fibonacci', {}).get('50.0', close[-1]):
                    continue
                if trend_macro == 'bearish' and close[-1] > context.get('fibonacci', {}).get('50.0', close[-1]):
                    continue
                reasons.append(f"Tendencia macro {trend_macro}")
                # 2. EMA 21/50 (cruce o rebote)
                from context_analyzer import calculate_ema
                ema21 = calculate_ema(close, 21)
                ema50 = calculate_ema(close, 50)
                ema_cross = ema21[-1] > ema50[-1] if trend_macro == 'bullish' else ema21[-1] < ema50[-1]
                if ema_cross:
                    reasons.append('Cruce EMA 21/50')
                # 3. RSI (divergencias o sobrecompra/sobreventa)
                from indicators.rsi import calculate_rsi
                rsi = calculate_rsi(close, 14)
                rsi_signal = False
                if trend_macro == 'bullish' and rsi[-1] > 50:
                    rsi_signal = True
                if trend_macro == 'bearish' and rsi[-1] < 50:
                    rsi_signal = True
                if rsi_signal:
                    reasons.append('RSI alineado con tendencia')
                # 4. Acción del precio (pin bar, engulfing)
                from indicators.candlestick_patterns import pin_bar, bullish_engulfing, bearish_engulfing
                open_prices = np.array(market_data['open'])
                high_prices = np.array(market_data['high'])
                low_prices = np.array(market_data['low'])
                close_prices = close
                pin_bull, pin_bear = pin_bar(open_prices, high_prices, low_prices, close_prices)
                engulf_bull = bullish_engulfing(open_prices, high_prices, low_prices, close_prices)
                engulf_bear = bearish_engulfing(open_prices, high_prices, low_prices, close_prices)
                if trend_macro == 'bullish' and (pin_bull[-1] or engulf_bull[-1]):
                    reasons.append('Price action alcista')
                if trend_macro == 'bearish' and (pin_bear[-1] or engulf_bear[-1]):
                    reasons.append('Price action bajista')
                # 5. Niveles clave y Fibonacci
                key_levels = analyze_key_levels(close.tolist())
                fib_levels = get_fibonacci_levels(close.tolist())
                if key_levels:
                    reasons.append('Nivel clave detectado')
                if fib_levels:
                    reasons.append('Fibonacci relevante')
                # 6. Tick volume (si disponible)
                if 'tick_volume' in market_data:
                    tick_vol = np.array(market_data['tick_volume'])
                    if len(tick_vol) > 20:
                        ma_vol = np.mean(tick_vol[-20:])
                        if tick_vol[-1] > 1.2 * ma_vol:
                            reasons.append('Volumen alto')
                # --- Validar mínimo 3 confluencias ---
                if len(reasons) < 3:
                    continue
                # ATR y RR
                from indicators.atr import calculate_atr
                atr = calculate_atr(high_prices, low_prices, close_prices, 14)[-1]
                entry = close[-1]
                stop_loss = entry - 1.2 * atr if trend_macro == 'bullish' else entry + 1.2 * atr
                take_profit = entry + 2.4 * atr if trend_macro == 'bullish' else entry - 2.4 * atr
                rr = abs(take_profit - entry) / abs(entry - stop_loss)
                if rr < 2.0:
                    continue
                reasons.append('R:R >= 1:2')
                # Filtros técnicos adicionales (ATR mínimo, etc.)
                if atr < 0.0005:
                    continue
                # Scoring/confianza (placeholder, ajustar con lógica real si aplica)
                confidence = 0.8
                if confidence < self.confidence_threshold:
                    continue
                # Construir señal
                signal = TradingSignal(
                    symbol=symbol,
                    timeframe=market_data.get('timeframe', tf),
                    signal_type='BUY' if trend_macro == 'bullish' else 'SELL',
                    entry_price=entry,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=confidence,
                    reasons=reasons,
                    timestamp=datetime.datetime.utcnow(),
                    atr_value=atr
                )
                signals.append(signal)
        # Filtrar y rankear señales antes de devolver
        ranked_signals = self.filter_and_rank_signals(signals, mt5_connector)
        return ranked_signals
    def is_optimal_trading_hour(self, mt5_connector, symbol: str) -> bool:
        """
        Determina si el símbolo está dentro de la ventana operativa óptima según la sesión de mercado.
        Requiere que mt5_connector.get_market_session_info(symbol) retorne dict con 'open' y 'close' (datetime).
        """
        """
        Determina si el símbolo está dentro de la ventana operativa óptima según la sesión de mercado.
        """
        # Suponiendo que mt5_connector.get_market_session_info devuelve dict con 'open', 'close' (datetime)
        import datetime
        session_info = mt5_connector.get_market_session_info(symbol)
        if not session_info:
            return False
        now = datetime.datetime.now().astimezone()
        open_time = session_info.get('open')
        close_time = session_info.get('close')
        if not open_time or not close_time:
            return False
        return open_time <= now < close_time

    def is_market_closing_soon(self, mt5_connector, symbol: str, threshold_minutes: int = 60) -> bool:
        """
        Determina si falta menos de threshold_minutes para el cierre del mercado del símbolo.
        """
        """
        Determina si falta menos de threshold_minutes para el cierre del mercado del símbolo.
        """
        import datetime
        session_info = mt5_connector.get_market_session_info(symbol)
        if not session_info:
            return False
        now = datetime.datetime.now().astimezone()
        close_time = session_info.get('close')
        if not close_time:
            return False
        delta = (close_time - now).total_seconds() / 60
        return 0 <= delta <= threshold_minutes

    def is_special_instrument(self, symbol: str) -> bool:
        """
        Determina si el símbolo es un instrumento especial (metales, índices, etc.).
        """
        """
        Determina si el símbolo es un instrumento especial (metales, índices, etc.).
        """
        special_keywords = ['XAU', 'XAG', 'GOLD', 'SILVER', 'IND', 'NAS', 'SPX', 'DOW', 'GER', 'UK', 'HK', 'JPN', 'OIL', 'WTI', 'BRENT']
        return any(k in symbol.upper() for k in special_keywords)
        # (Eliminado bloque duplicado y mal indentado que causaba el IndentationError)

    def analyze_market_data_multiframe(self, symbol, market_data, data_h1, data_h4):
        """
        Analiza los datos de mercado en M5/M15 y valida con tendencia macro y confluencias mínimas.
        """
        # Filtros pre-técnicos (eliminatorios)
        symbol_info = market_data.get('symbol_info', {})
        if not has_sufficient_data(market_data):
            self.logger.debug(f"{symbol}: Insuficientes datos históricos.")
            return None
        if not spread_within_reasonable_bounds(symbol_info):
            self.logger.debug(f"{symbol}: Spread fuera de rango.")
            return None
        if not symbol_is_tradeable(symbol_info):
            self.logger.debug(f"{symbol}: No tradeable.")
            return None

        # --- Tendencia macro (H4) ---
        trend_macro = market_data.get('trend_macro', 'neutral')
        if trend_macro == 'neutral':
            return None

        # --- Indicadores técnicos en timeframe de entrada ---
        indicators = TechnicalIndicators.calculate_indicators(market_data)
        reasons = []

        # 1. Tendencia macro alineada
        close = np.array(market_data['close'])
        if trend_macro == 'bullish' and close[-1] < indicators['ema_200'][-1]:
            return None
        if trend_macro == 'bearish' and close[-1] > indicators['ema_200'][-1]:
            return None
        reasons.append(f"Tendencia macro {trend_macro}")

        # 2. EMA 21/50 (cruce o rebote)
        ema21 = calculate_ema(close, 21)
        ema50 = indicators['ema_50']
        ema_cross = ema21[-1] > ema50[-1] if trend_macro == 'bullish' else ema21[-1] < ema50[-1]
        if ema_cross:
            reasons.append('Cruce EMA 21/50')

        # 3. RSI (divergencias o sobrecompra/sobreventa)
        rsi = calculate_rsi(close, 14)
        rsi_signal = False
        if trend_macro == 'bullish' and rsi[-1] > 50:
            rsi_signal = True
        if trend_macro == 'bearish' and rsi[-1] < 50:
            rsi_signal = True
        if rsi_signal:
            reasons.append('RSI alineado con tendencia')

        # 4. Acción del precio (pin bar, engulfing)
        open_prices = np.array(market_data['open'])
        high_prices = np.array(market_data['high'])
        low_prices = np.array(market_data['low'])
        close_prices = close
        pin_bull, pin_bear = CandlestickPatterns.pin_bar(open_prices, high_prices, low_prices, close_prices)
        engulf_bull = CandlestickPatterns.bullish_engulfing(open_prices, high_prices, low_prices, close_prices)
        engulf_bear = CandlestickPatterns.bearish_engulfing(open_prices, high_prices, low_prices, close_prices)
        if trend_macro == 'bullish' and (pin_bull[-1] or engulf_bull[-1]):
            reasons.append('Price action alcista')
        if trend_macro == 'bearish' and (pin_bear[-1] or engulf_bear[-1]):
            reasons.append('Price action bajista')


        # 5. Niveles clave y Fibonacci (integración con context_analyzer)
        try:
            from context_analyzer import analyze_key_levels, get_fibonacci_levels
            key_levels = analyze_key_levels(close.tolist())
            fib_levels = get_fibonacci_levels(close.tolist())
            if key_levels:
                reasons.append('Nivel clave detectado')
            if fib_levels:
                reasons.append('Fibonacci relevante')
        except Exception as e:
            self.logger.debug(f"{symbol}: Error en análisis de niveles clave/Fibonacci: {e}")

        # 6. Tick volume (si disponible)
        if 'tick_volume' in market_data:
            tick_vol = np.array(market_data['tick_volume'])
            if len(tick_vol) > 20:
                ma_vol = np.mean(tick_vol[-20:])
                if tick_vol[-1] > 1.2 * ma_vol:
                    reasons.append('Volumen alto')

        # --- Validar mínimo 3 confluencias ---
        if len(reasons) < 3:
            return None

        # ATR y RR
        atr = indicators['atr'][-1] if isinstance(indicators['atr'], np.ndarray) else indicators['atr']
        entry = close[-1]
        stop_loss = entry - 1.2 * atr if trend_macro == 'bullish' else entry + 1.2 * atr
        take_profit = entry + 2.4 * atr if trend_macro == 'bullish' else entry - 2.4 * atr
        rr = abs(take_profit - entry) / abs(entry - stop_loss)
        if rr < 2.0:
            return None
        reasons.append('R:R >= 1:2')

        # Filtros técnicos adicionales
        if not atr_sufficient(atr):
            return None
        if not adx_sufficient(indicators['adx'][-1]):
            return None
        if not rsi_favorable(indicators['rsi'][-1]):
            return None

        # Scoring/confianza (placeholder, ajustar con lógica real si aplica)
        confidence = 0.8
        if confidence < self.confidence_threshold:
            return None

        # Construir señal
        signal = TradingSignal(
            symbol=symbol,
            timeframe=market_data.get('timeframe', 'M5'),
            signal_type='BUY' if trend_macro == 'bullish' else 'SELL',
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reasons=reasons,
            timestamp=datetime.utcnow(),
            atr_value=atr
        )
        return signal
def is_optimal_trading_hour(mt5_connector, symbol: str) -> bool:
    """
    Determina si es horario óptimo para operar según la hora del servidor MT5 y el tipo de instrumento.
    Args:
        mt5_connector: Instancia de MT5Connector conectada.
        symbol: Símbolo a evaluar.
    Returns:
        bool: True si es horario óptimo, False si debe evitarse (por ejemplo, durante rollover/swap).
    """
    # Definir ventanas de trading óptimas (UTC) por tipo de instrumento
    forex_hours = [(8, 22)]  # 8:00 a 22:00 UTC (Londres+NY)
    metals_hours = [(9, 21)]
    indices_hours = [(13, 21)]
    rollover_hours = [(23, 0), (0, 1)]  # 23:00 a 01:00 UTC (evitar rollover)

    # Obtener hora del servidor MT5
    server_time = mt5_connector.get_server_time()
    if not server_time:
        return True  # Si no se puede obtener, no filtrar
    hour = server_time.hour

    # Determinar tipo de instrumento
    symbol_lower = symbol.lower()
    if any(x in symbol_lower for x in ['xau', 'xag', 'gold', 'silver']):
        allowed_hours = metals_hours
    elif any(x in symbol_lower for x in ['us30', 'nas100', 'ger30', 'uk100', 'spx', 'dj', 'index']):
        allowed_hours = indices_hours
    else:
        allowed_hours = forex_hours

    # Evitar horario de rollover
    for start, end in rollover_hours:
        if start < end:
            if start <= hour < end:
                return False
        else:  # Rollover cruza medianoche
            if hour >= start or hour < end:
                return False

    # Verificar si está dentro de la ventana permitida
    for start, end in allowed_hours:
        if start <= hour < end:
            return True
    return False
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
# Importar InstrumentManager modular
from core.instrument_manager import InstrumentManager
# Importar filtros y técnicos
from filters.pre_filters import has_sufficient_data, spread_within_reasonable_bounds, symbol_is_tradeable
from filters.technical_filters import atr_sufficient, adx_sufficient, rsi_favorable
from indicators.ema import calculate_ema
from indicators.rsi import calculate_rsi
from indicators.macd import calculate_macd

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
    @staticmethod
    def find_fractals(data: np.ndarray, window: int = 2) -> Tuple[List[int], List[int]]:
        """
        Detecta índices de swing highs y swing lows (fractales) en los datos de precios.
        Args:
            data: array de precios (close)
            window: número de velas a cada lado para considerar un fractal
        Returns:
            (swing_highs, swing_lows): listas de índices
        """
        swing_highs = []
        swing_lows = []
        for i in range(window, len(data) - window):
            is_high = all(data[i] > data[i - j] for j in range(1, window + 1)) and all(data[i] > data[i + j] for j in range(1, window + 1))
            is_low = all(data[i] < data[i - j] for j in range(1, window + 1)) and all(data[i] < data[i + j] for j in range(1, window + 1))
            if is_high:
                swing_highs.append(i)
            if is_low:
                swing_lows.append(i)
        return swing_highs, swing_lows

    @staticmethod
    def find_nearest_level(price: float, levels: List[float]) -> float:
        """
        Encuentra el nivel más cercano a un precio dado.
        """
        if not levels:
            return price
        return min(levels, key=lambda x: abs(x - price))
    """
    Technical indicators calculation class
    """
    
    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        return calculate_ema(data, period)

    @staticmethod
    def rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        return calculate_rsi(data, period)

    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        # Si tienes un módulo externo para ATR, usa aquí. Si no, usa la implementación previa.
        tr = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
        atr = pd.Series(tr).rolling(window=period).mean().values
        atr = np.concatenate([np.full(period, np.nan), atr])
        return atr

    @staticmethod
    def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        # Si tienes un módulo externo para ADX, usa aquí. Si no, usa la implementación previa.
        return np.full_like(close, 25.0)

    @staticmethod
    def calculate_indicators(market_data: MarketData) -> dict:
        close = np.array(market_data.close)
        high = np.array(market_data.high)
        low = np.array(market_data.low)
        indicators = {
            'ema_20': calculate_ema(close, 20),
            'ema_50': calculate_ema(close, 50),
            'ema_200': calculate_ema(close, 200),
            'rsi': calculate_rsi(close, 14),
            'atr': TechnicalIndicators.atr(high, low, close, 14),
            'adx': TechnicalIndicators.adx(high, low, close, 14),
        }
        # Calcular cruces EMA
        indicators['current_ema_cross'] = close[-1] > indicators['ema_50'][-1] and close[-1] > indicators['ema_200'][-1]
        indicators['recent_ema_cross'] = close[-5] > indicators['ema_50'][-5] and close[-5] > indicators['ema_200'][-5]
        indicators['ema_convergence'] = abs(indicators['ema_50'][-1] - indicators['ema_200'][-1]) < 0.0005
        indicators['ema_acceleration'] = indicators['ema_50'][-1] > indicators['ema_50'][-5]
        indicators['current_rsi'] = indicators['rsi'][-1] if len(indicators['rsi']) > 0 else None
        indicators['prev_rsi'] = indicators['rsi'][-2] if len(indicators['rsi']) > 1 else None
        # MACD y señal
        macd, macd_signal = calculate_macd(close)
        indicators['macd'] = macd
        indicators['macd_signal'] = macd_signal
        # Tendencia simple: EMA20 > EMA50 = alcista
        indicators['trend'] = 'bullish' if indicators['ema_20'][-1] > indicators['ema_50'][-1] else 'bearish'
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
    def __init__(self):
        """
        Inicializa el generador de señales usando el InstrumentManager modular y los filtros/indicadores externos.
        """
        self.instrument_manager = InstrumentManager()
        self.symbols = []
        self.rotation_index = 0
        self._current_cycle = 0
        self.symbol_specs = {}
        self.indicators = TechnicalIndicators()
        self.patterns = CandlestickPatterns() if 'CandlestickPatterns' in globals() else None
        self.all_available_symbols = []
        self.instrument_types_config = {
            'forex': True,
            'indices': True,
            'metals': True,
            'stocks': False,
            'crypto': False,
            'etfs': False
        }
        self.min_atr_threshold = {}
        self.dynamic_multipliers = {}
        enabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if enabled]
        disabled_types = [tipo for tipo, enabled in self.instrument_types_config.items() if not enabled]
        logger.info(f"Signal generator initialized with modular InstrumentManager and filters.")
        logger.info(f"ENABLED types: {', '.join(enabled_types)}")
        logger.info(f"DISABLED types: {', '.join(disabled_types)}")
        self.generated_signals = []
        self.virtual_trades = []
        self._lock = threading.Lock()

    def initialize_symbols(self):
        """
        Inicializa la lista de símbolos usando el InstrumentManager modular.
        """
        self.all_available_symbols = self.instrument_manager.load_symbols()
        self.symbols = list(self.all_available_symbols)
        self.rotation_index = 0
        logger.info(f"Inicializados {len(self.symbols)} símbolos para escaneo dinámico (InstrumentManager).")

    def _rotate_symbols(self, batch_size=50):
        """
        Rota el subconjunto de símbolos activos para escaneo usando InstrumentManager.
        """
        for batch in self.instrument_manager.rotate_symbols(batch_size=batch_size):
            self.symbols = batch
            logger.info(f"Rotación de símbolos: {self.symbols[0]} - {self.symbols[-1]} ({len(self.symbols)})")
            yield batch
    def calculate_dynamic_tp(self, close_prices: np.ndarray, entry_price: float, atr: float, signal_type: str) -> float:
        """
        Calcula un TP dinámico usando swings/fractales y ATR.
        """
        highs, lows = TechnicalIndicators.find_fractals(close_prices)
        if signal_type == 'BUY':
            # Buscar el swing high más cercano por encima del entry
            swing_highs = [close_prices[i] for i in highs if close_prices[i] > entry_price]
            tp_fractal = TechnicalIndicators.find_nearest_level(entry_price, swing_highs)
            tp_atr = entry_price + 2 * atr
            return min(tp_fractal, tp_atr) if swing_highs else tp_atr
        else:
            swing_lows = [close_prices[i] for i in lows if close_prices[i] < entry_price]
            tp_fractal = TechnicalIndicators.find_nearest_level(entry_price, swing_lows)
            tp_atr = entry_price - 2 * atr
            return max(tp_fractal, tp_atr) if swing_lows else tp_atr

    def calculate_partial_tp(self, entry_price: float, stop_loss: float, signal_type: str, r_multiple: float = 1.5) -> float:
        """
        Calcula el nivel de TP parcial (por ejemplo, 1.5R).
        """
        r = abs(entry_price - stop_loss)
        if signal_type == 'BUY':
            return entry_price + r_multiple * r
        else:
            return entry_price - r_multiple * r
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
        Analiza los datos de mercado y genera una señal si se cumplen las condiciones y el horario de mercado MT5 es óptimo.
        """
        # Filtro horario óptimo usando hora de MT5
        if hasattr(self, 'mt5_connector') and self.mt5_connector:
            if not is_optimal_trading_hour(self.mt5_connector, market_data.symbol):
                logger.info(f"⏰ Fuera de horario óptimo para operar {market_data.symbol}. No se genera señal.")
                return None

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
