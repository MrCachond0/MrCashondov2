"""
Risk Management Module
Handles position sizing, risk calculation, and trade management
"""
import logging
import math
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class RiskParameters:
    """Risk management parameters optimized for SFO strategy"""
    max_risk_per_trade: float = 0.02  # 2% del balance/margen (ajustado para scalping/day trading)
    max_daily_loss: float = 0.04  # 4% diario
    max_open_positions: int = 3
    min_risk_reward_ratio: float = 1.4  # Ratio mínimo real 1.4
    sl_atr_multiplier: float = 1.2  # SL: mínimo 1.2 × ATR
    tp_atr_multiplier: float = 1.7  # TP: mínimo 1.7 × ATR
    breakeven_multiplier: float = 1.2  # Break-even a 1.2R
    trailing_stop_multiplier: float = 1.4  # Trailing stop a 1.4R

@dataclass
class PositionSize:
    """Position sizing calculation result"""
    volume: float
    risk_amount: float
    risk_percentage: float
    pip_value: float
    stop_loss_pips: float

class RiskManager:
    def get_exposure_limit(self, symbol_info: dict, account_info: dict) -> float:
        """
        Calcula el límite de exposición permitido para una operación según el tipo de instrumento.
        FOREX: 40% del balance, Metales: 25% del balance, Índices: 20% (por defecto).
        """
        try:
            balance = account_info.get('balance', 0)
            symbol = symbol_info.get('symbol', '').upper()
            if any(x in symbol for x in ['XAU', 'XAG', 'GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM']):
                limit_pct = 0.25  # Metales
            elif any(x in symbol for x in ['EUR', 'USD', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']):
                limit_pct = 0.40  # Majors FOREX
            else:
                limit_pct = 0.20  # Índices u otros
            exposure_limit = balance * limit_pct
            logger.info(f"[RISK] Exposure limit calculado: {exposure_limit} (balance={balance}, symbol={symbol}, limit_pct={limit_pct})")
            return exposure_limit
        except Exception as e:
            logger.error(f"[RISK] Error calculando exposure limit: {str(e)}")
            return 0.0
    def calculate_margin_required(self, symbol: str, volume: float, entry_price: float, symbol_info: dict) -> float:
        """
        Calcula el margen requerido para una operación dada.
        Args:
            symbol: Símbolo del instrumento
            volume: Volumen de la operación
            entry_price: Precio de entrada
            symbol_info: Diccionario con información del símbolo (de MT5Connector)
        Returns:
            Margen requerido en la moneda de la cuenta
        """
        try:
            contract_size = symbol_info.get('contract_size', 100000)
            leverage = symbol_info.get('leverage', 100)
            if leverage <= 0:
                leverage = 100  # Valor por defecto si no está disponible
            margin = (contract_size * volume * entry_price) / leverage
            if margin <= 0:
                logger.warning(f"[RISK] Margin calculado <= 0 para {symbol}. contract_size={contract_size}, volume={volume}, entry_price={entry_price}, leverage={leverage}")
            logger.info(f"[RISK] Margin requerido para {symbol}: {margin}")
            return margin
        except Exception as e:
            logger.error(f"[RISK] Error calculando margen requerido para {symbol}: {str(e)}")
            return 0.0
    def adjust_signal_filters(self, signal_generator, min_score: float = 0.8, min_atr: float = 0.0005, min_adx: float = 20):
        """
        Ajusta los filtros técnicos del generador de señales endureciendo el score mínimo y los umbrales de ATR/ADX.
        Args:
            signal_generator: Instancia de SignalGenerator.
            min_score (float): Score mínimo para ejecución automática.
            min_atr (float): Umbral mínimo de ATR para filtrar baja volatilidad.
            min_adx (float): Umbral mínimo de ADX para filtrar mercados sin tendencia.
        """
        # Endurece el score mínimo
        if hasattr(signal_generator, 'confidence_threshold'):
            signal_generator.confidence_threshold = min_score
            logger.info(f"Nuevo score mínimo para ejecución automática: {min_score}")
        # Ajusta umbrales ATR y ADX si existen
        if hasattr(signal_generator, 'min_atr_threshold'):
            signal_generator.min_atr_threshold = min_atr
            logger.info(f"Nuevo umbral mínimo ATR: {min_atr}")
        if hasattr(signal_generator, 'min_adx_threshold'):
            signal_generator.min_adx_threshold = min_adx
            logger.info(f"Nuevo umbral mínimo ADX: {min_adx}")
        # Si el generador usa umbrales por símbolo, sugerir ajuste en su método correspondiente
        if hasattr(signal_generator, 'get_symbol_atr_threshold'):
            logger.info("Revisar umbrales ATR/ADX por símbolo en SignalGenerator para coherencia con la volatilidad actual.")
    def __init__(self, risk_params: RiskParameters = None):
        """
        Inicializa el gestor de riesgo y el registro de posiciones abiertas por símbolo.
        Args:
            risk_params (RiskParameters, opcional): Parámetros de riesgo personalizados.
        """
        self.risk_params = risk_params or RiskParameters()
        # Dict[str, int]: símbolo -> cantidad de posiciones abiertas
        self.open_positions_by_symbol = {}
        self.positions_count = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.cooldown = False
        self.cooldown_loss_limit = 2  # Detener tras 2 pérdidas seguidas
    def register_trade_result(self, result: str):
        """
        Registra el resultado de una operación ('WIN', 'LOSS', 'BE').
        Si hay 2 pérdidas seguidas, activa cooldown.
        """
        if result == 'LOSS':
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.cooldown_loss_limit:
                self.cooldown = True
                logger.warning(f"[COOLDOWN] Activado tras {self.consecutive_losses} pérdidas consecutivas.")
        elif result == 'WIN' or result == 'BE':
            self.consecutive_losses = 0
            self.cooldown = False

    def can_trade(self) -> bool:
        """
        Indica si se puede operar (no en cooldown).
        """
        return not self.cooldown

    def can_open_position(self, symbol: str) -> Tuple[bool, str]:
        """
        Verifica si se puede abrir una nueva posición para el símbolo dado.
        Permite máximo 1 posición abierta por símbolo.
        Returns:
            (bool, str): True si se puede abrir, False y motivo si no.
        """
        count = self.open_positions_by_symbol.get(symbol, 0)
        if count >= 1:
            logger.warning(f"[RISK] Rechazo apertura: Ya existe una posición abierta para {symbol} (máximo 1 permitido)")
            return False, f"Ya existe una posición abierta para {symbol} (máximo 1 permitido)"
        if self.positions_count >= self.risk_params.max_open_positions:
            logger.warning(f"[RISK] Rechazo apertura: Se alcanzó el máximo global de posiciones abiertas ({self.risk_params.max_open_positions})")
            return False, f"Se alcanzó el máximo global de posiciones abiertas ({self.risk_params.max_open_positions})"
        return True, "Permiso concedido"

    def register_open_position(self, symbol: str):
        """
        Registra la apertura de una posición para el símbolo dado.
        Limita a 1 posición por símbolo.
        """
        if self.open_positions_by_symbol.get(symbol, 0) >= 1:
            logger.warning(f"[RISK] Intento de abrir más de una posición en {symbol}. Operación bloqueada.")
            return False
        self.open_positions_by_symbol[symbol] = 1
        self.positions_count += 1
        logger.info(f"[RISK] Posición registrada para {symbol}. Total posiciones abiertas: {self.positions_count}")
        return True

    def register_close_position(self, symbol: str):
        """
        Registra el cierre de una posición para el símbolo dado.
        """
        if self.open_positions_by_symbol.get(symbol, 0) > 0:
            self.open_positions_by_symbol[symbol] = 0
            self.positions_count = max(0, self.positions_count - 1)
            logger.info(f"[RISK] Posición cerrada para {symbol}. Total posiciones abiertas: {self.positions_count}")
        else:
            logger.warning(f"[RISK] Intento de cerrar posición inexistente en {symbol}.")
        self.positions_count = max(0, self.positions_count - 1)

    def calculate_sl_tp(self, entry_price: float, atr: float, signal_type: str) -> Tuple[float, float]:
        """
        Calcula el Stop Loss y Take Profit óptimos según los nuevos multiplicadores ATR y ratio mínimo.
        Args:
            entry_price: Precio de entrada de la operación
            atr: Valor actual del ATR
            signal_type: 'BUY' o 'SELL'
        Returns:
            (stop_loss, take_profit)
        """
        params = self.risk_params
        sl_dist = params.sl_atr_multiplier * atr
        tp_dist = params.tp_atr_multiplier * atr
        # Asegura ratio mínimo
        if tp_dist / sl_dist < params.min_risk_reward_ratio:
            tp_dist = sl_dist * params.min_risk_reward_ratio
        if signal_type == 'BUY':
            stop_loss = entry_price - sl_dist
            take_profit = entry_price + tp_dist
        else:
            stop_loss = entry_price + sl_dist
            take_profit = entry_price - tp_dist
        return stop_loss, take_profit

    def manage_partial_and_trailing(self,
                                   position_id: int,
                                   entry_price: float,
                                   stop_loss: float,
                                   take_profit: float,
                                   current_price: float,
                                   signal_type: str,
                                   volume: float,
                                   close_prices: 'np.ndarray',
                                   atr: float,
                                   broker_api,
                                   r_partial: float = 1.0,
                                   r_trailing: float = 1.5,
                                   trailing_period: int = 20) -> None:
        """
        Gestiona el cierre parcial y trailing stop para una posición abierta.
        - Si el precio alcanza el TP parcial (por defecto 1R), cierra la mitad de la posición.
        - El resto de la posición se gestiona con trailing stop estructural.
        - Si el trailing stop es alcanzado, cierra el runner.

        Args:
            position_id (int): ID de la posición en el broker.
            entry_price (float): Precio de entrada de la operación.
            stop_loss (float): Nivel de stop loss inicial.
            take_profit (float): Nivel de take profit final.
            current_price (float): Precio actual del mercado.
            signal_type (str): 'BUY' o 'SELL'.
            volume (float): Volumen total de la posición.
            close_prices (np.ndarray): Serie de precios de cierre.
            atr (float): Valor actual del ATR.
            broker_api: Objeto/conector para ejecutar órdenes parciales y modificar SL.
            r_partial (float): Multiplicador de R para TP parcial (por defecto 1.0).
            r_trailing (float): Multiplicador de R para activar trailing (por defecto 1.0).
            trailing_period (int): Periodo para el cálculo de trailing estructural.
        """
        # 1. Cierre parcial si corresponde (TP1 = 1R)
        r1 = abs(entry_price - stop_loss)
        tp1 = entry_price + r1 if signal_type == 'BUY' else entry_price - r1
        partial_close_done = broker_api.is_partial_closed(position_id) if hasattr(broker_api, 'is_partial_closed') else False
        if not partial_close_done:
            if (signal_type == 'BUY' and current_price >= tp1) or (signal_type == 'SELL' and current_price <= tp1):
                partial_vol, runner_vol = self.split_position_for_partial(volume)
                if broker_api.is_partial_close_allowed(position_id):
                    broker_api.close_partial(position_id, partial_vol)
                    logger.info(f"[PARTIAL CLOSE] Posición {position_id}: Cerrada mitad ({partial_vol}) en TP1 {current_price:.5f}")
                    # Mover SL a break even
                    break_even = entry_price
                    broker_api.modify_stop_loss(position_id, break_even)
                    logger.info(f"[BREAKEVEN] SL movido a entrada para runner de posición {position_id}")

        # 2. Trailing stop para el runner (a partir de 1.5R)
        r15 = 1.5 * abs(entry_price - stop_loss)
        tp_trailing = entry_price + r15 if signal_type == 'BUY' else entry_price - r15
        if (signal_type == 'BUY' and current_price >= tp_trailing) or (signal_type == 'SELL' and current_price <= tp_trailing):
            trailing_stop = self.calculate_trailing_stop(
                close_prices=close_prices,
                entry_price=entry_price,
                current_price=current_price,
                stop_loss=stop_loss,
                signal_type=signal_type,
                atr=atr,
                period=trailing_period
            )
            if trailing_stop is not None:
                broker_api.modify_stop_loss(position_id, trailing_stop)
                logger.info(f"[TRAILING] SL actualizado a {trailing_stop:.5f} para runner de posición {position_id}")

        # 3. Cierre runner si SL o TP final alcanzados
        if (signal_type == 'BUY' and (current_price <= stop_loss or current_price >= take_profit)) or \
           (signal_type == 'SELL' and (current_price >= stop_loss or current_price <= take_profit)):
            if broker_api.is_position_open(position_id):
                broker_api.close_position(position_id)
                logger.info(f"[FINAL CLOSE] Runner de posición {position_id} cerrado en {current_price:.5f}")

    # ---
    # NOTA DE USO:
    # Este método debe ser llamado periódicamente desde el ciclo de gestión de posiciones activas (main.py),
    # pasando el ID de la posición, precios relevantes y el objeto broker_api que implemente:
    # - close_partial(position_id, volume)
    # - modify_stop_loss(position_id, new_sl)
    # - is_partial_close_allowed(position_id)
    # - is_partial_closed(position_id)
    # - is_position_open(position_id)
    # - close_position(position_id)
    #
    # Esto asegura la integración perfecta de la lógica de cierre parcial y trailing.
    def calculate_dynamic_tp_sl(self, close_prices: np.ndarray, entry_price: float, signal_type: str, atr: float) -> Tuple[float, float]:
        """
        Calcula SL y TP dinámicos usando fractales y estructura de mercado.
        El TP prioriza el swing high/low relevante (resistencia/soporte) más cercano.
        Si no hay, usa múltiplo de ATR.
        """
        from signal_generator import TechnicalIndicators
        highs, lows = TechnicalIndicators.find_fractals(close_prices)
        if signal_type == 'BUY':
            # SL: último swing low
            swing_lows = [close_prices[i] for i in lows if close_prices[i] < entry_price]
            sl_fractal = TechnicalIndicators.find_nearest_level(entry_price, swing_lows)
            sl_atr = entry_price - 1.2 * atr
            stop_loss = max(sl_fractal, sl_atr) if swing_lows else sl_atr
            # TP: resistencia/swing high más cercano por encima de entry
            swing_highs = [close_prices[i] for i in highs if close_prices[i] > entry_price]
            tp_fractal = TechnicalIndicators.find_nearest_level(entry_price, swing_highs)
            tp_atr = entry_price + 2 * atr
            # Si el swing high está demasiado lejos (>3*ATR), usar tp_atr
            if swing_highs and abs(tp_fractal - entry_price) <= 3 * atr:
                take_profit = tp_fractal
            else:
                take_profit = tp_atr
        else:
            # SL: último swing high
            swing_highs = [close_prices[i] for i in highs if close_prices[i] > entry_price]
            sl_fractal = TechnicalIndicators.find_nearest_level(entry_price, swing_highs)
            sl_atr = entry_price + 1.2 * atr
            stop_loss = min(sl_fractal, sl_atr) if swing_highs else sl_atr
            # TP: soporte/swing low más cercano por debajo de entry
            swing_lows = [close_prices[i] for i in lows if close_prices[i] < entry_price]
            tp_fractal = TechnicalIndicators.find_nearest_level(entry_price, swing_lows)
            tp_atr = entry_price - 2 * atr
            if swing_lows and abs(tp_fractal - entry_price) <= 3 * atr:
                take_profit = tp_fractal
            else:
                take_profit = tp_atr
        return stop_loss, take_profit

    def calculate_trailing_stop_structural(
        self,
        close_prices: np.ndarray,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        signal_type: str,
        atr: float,
        period: int = 20
    ) -> float:
        """
        Calcula el nivel de trailing stop usando fractales recientes o EMA20.
        El trailing solo se activa después de alcanzar 1R (precio se mueve a favor al menos el riesgo inicial).
        Args:
            close_prices (np.ndarray): Array de precios de cierre.
            entry_price (float): Precio de entrada de la operación.
            current_price (float): Precio actual.
            stop_loss (float): SL original.
            signal_type (str): 'BUY' o 'SELL'.
            atr (float): Valor actual del ATR.
            period (int): Ventana para buscar fractales y calcular EMA.
        Returns:
            float: Nivel sugerido para el trailing stop, o None si no corresponde moverlo.
        """
        from signal_generator import TechnicalIndicators
        highs, lows = TechnicalIndicators.find_fractals(close_prices)
        closes_np = np.array(close_prices)
        ema = TechnicalIndicators.ema(closes_np, period)
        risk = abs(entry_price - stop_loss)
        if signal_type == 'BUY':
            # Solo trail si el precio avanzó al menos 1R
            if current_price < entry_price + risk:
                return None
            # Buscar el swing low más reciente por debajo del precio actual
            swing_lows = [close_prices[i] for i in lows if close_prices[i] < current_price]
            trailing_fractal = TechnicalIndicators.find_nearest_level(current_price, swing_lows) if swing_lows else None
            trailing_ema = ema[-1] if len(ema) > 0 else None
            # El trailing más conservador (más alto)
            trailing_stop = max(filter(lambda x: x is not None, [trailing_fractal, trailing_ema, entry_price + 0.1 * risk]))
            # Nunca bajar el SL por debajo del entry
            trailing_stop = max(trailing_stop, entry_price)
            return trailing_stop if trailing_stop > stop_loss else None
        else:
            if current_price > entry_price - risk:
                return None
            swing_highs = [close_prices[i] for i in highs if close_prices[i] > current_price]
            trailing_fractal = TechnicalIndicators.find_nearest_level(current_price, swing_highs) if swing_highs else None
            trailing_ema = ema[-1] if len(ema) > 0 else None
            trailing_stop = min(filter(lambda x: x is not None, [trailing_fractal, trailing_ema, entry_price - 0.1 * risk]))
            trailing_stop = min(trailing_stop, entry_price)
            return trailing_stop if trailing_stop < stop_loss else None

    def calculate_partial_tp(
        self,
        entry_price: float,
        stop_loss: float,
        signal_type: str,
        r_multiple: float = 1.0
    ) -> float:
        """
        Calcula el nivel de Take Profit parcial (por defecto 1R o 1.5R).

        Args:
            entry_price (float): Precio de entrada de la operación.
            stop_loss (float): Nivel de stop loss.
            signal_type (str): 'BUY' o 'SELL'.
            r_multiple (float): Multiplicador de R para el TP parcial (1.0 = 1R, 1.5 = 1.5R, etc).

        Returns:
            float: Nivel de precio para el TP parcial.
        """
        r = abs(entry_price - stop_loss)
        if signal_type == 'BUY':
            return entry_price + r_multiple * r
        else:
            return entry_price - r_multiple * r

    def calculate_trailing_stop(self, close_prices: np.ndarray, entry_price: float, current_price: float, stop_loss: float, signal_type: str, atr: float, period: int = 20) -> float:
        """
        Wrapper para trailing estructural. Devuelve el nuevo SL sugerido o None si no corresponde moverlo.
        """
        return self.calculate_trailing_stop_structural(
            close_prices=close_prices,
            entry_price=entry_price,
            current_price=current_price,
            stop_loss=stop_loss,
            signal_type=signal_type,
            atr=atr,
            period=period
        )
    def should_take_partial_profit(self, entry_price: float, stop_loss: float, current_price: float, signal_type: str, r_multiple: float = 1.0) -> bool:
        """
        Determina si se debe tomar ganancia parcial (por ejemplo, en 1R o 1.5R).
        """
        risk = abs(entry_price - stop_loss)
        if signal_type == 'BUY':
            return current_price >= entry_price + r_multiple * risk
        else:
            return current_price <= entry_price - r_multiple * risk

    def split_position_for_partial(self, volume: float) -> Tuple[float, float]:
        """
        Divide el volumen en dos partes para TP parcial y runner.
        Por defecto, mitad y mitad.
        """
        return volume / 2, volume / 2

    def calculate_break_even(self, entry_price: float, stop_loss: float, signal_type: str, r_multiple: float = 1.0) -> float:
        """
        Calcula el nivel de break-even (mover SL a entrada tras 1R).
        """
        r = abs(entry_price - stop_loss)
        if signal_type == 'BUY':
            return entry_price + r_multiple * r
        else:
            return entry_price - r_multiple * r
    def calculate_position_size_fixed_usd(self, symbol: str, entry_price: float, stop_loss: float,
                                         symbol_info: Dict, fixed_risk_usd: float) -> Optional[PositionSize]:
        """
        Calcula el tamaño de la posición para que el riesgo máximo sea exactamente el monto fijo en USD indicado.
        Si el volumen calculado es menor al mínimo permitido por el broker, ajusta al mínimo y lo notifica en el log.
        Args:
            symbol: Símbolo a operar
            entry_price: Precio de entrada
            stop_loss: Precio de stop loss
            symbol_info: Info del símbolo (dict MT5)
            fixed_risk_usd: Monto fijo en USD a arriesgar
        Returns:
            PositionSize con el volumen calculado y detalles
        """
        try:
            sl_distance = abs(entry_price - stop_loss)
            if sl_distance == 0:
                logger.error(f"[POSITION SIZE USD] SL igual a entry para {symbol}. Usando distancia mínima de emergencia.")
                point = symbol_info.get('point', 0.0001)
                emergency_distance = max(10 * point, 0.001)
                stop_loss = entry_price - emergency_distance
                sl_distance = emergency_distance
            contract_size = symbol_info.get('contract_size', 100000.0)
            # Determinar pip_size según el símbolo
            if 'JPY' in symbol:
                pip_size = 0.01
            elif any(metal in symbol for metal in ['XAU', 'XAG', 'GOLD', 'SILVER']):
                pip_size = 0.1
            else:
                pip_size = 0.0001
            if sl_distance <= 0:
                sl_distance = pip_size * 10
                logger.warning(f"[POSITION SIZE USD] sl_distance era 0, ajustado a {sl_distance}")
            sl_pips = sl_distance / pip_size
            pip_value_per_lot = pip_size * contract_size
            tick_value = symbol_info.get('tick_value', 0)
            if tick_value > 0:
                pip_value = tick_value
            else:
                pip_value = pip_value_per_lot
            if pip_value <= 0:
                if 'JPY' in symbol:
                    pip_value = 1000.0
                elif any(metal in symbol for metal in ['XAU', 'XAG']):
                    pip_value = 100.0
                else:
                    pip_value = 10.0
                logger.warning(f"[POSITION SIZE USD] pip_value era 0, usando fallback: {pip_value}")
            if sl_pips <= 0:
                sl_pips = 10.0
                logger.warning(f"[POSITION SIZE USD] sl_pips ajustado a emergencia: {sl_pips}")
            # Volumen para que la pérdida máxima sea fixed_risk_usd
            volume = fixed_risk_usd / (sl_pips * pip_value)
            min_vol = symbol_info.get('volume_min', symbol_info.get('min_volume', 0.01))
            max_vol = symbol_info.get('volume_max', symbol_info.get('max_volume', 100.0))
            step_vol = symbol_info.get('volume_step', 0.01)
            if min_vol <= 0:
                min_vol = 0.01
                logger.warning(f"[POSITION SIZE USD] min_vol era 0, ajustado a {min_vol}")
            # Redondear al múltiplo permitido
            volume = max(min_vol, min(max_vol, round(volume / step_vol) * step_vol))
            if volume < min_vol:
                logger.warning(f"[POSITION SIZE USD] Volumen calculado por debajo del mínimo permitido para {symbol}: {volume}. Se usará el mínimo permitido.")
                volume = min_vol
            if volume <= 0:
                volume = min_vol
                logger.warning(f"[POSITION SIZE USD] Volumen era 0, usando mínimo: {min_vol} para {symbol}")
            return PositionSize(
                volume=volume,
                risk_amount=fixed_risk_usd,
                risk_percentage=0.0,
                pip_value=pip_value,
                stop_loss_pips=sl_pips
            )
        except Exception as e:
            logger.error(f"Error en cálculo de posición (fixed USD) para {symbol}: {e}")
            min_vol = symbol_info.get('volume_min', 0.01)
            return PositionSize(
                volume=min_vol,
                risk_amount=fixed_risk_usd,
                risk_percentage=0.0,
                pip_value=10.0,
                stop_loss_pips=10.0
            )
    def adjust_stops(self, signal_type: str, entry_price: float, stop_loss: float, take_profit: float, symbol_info: dict, atr: float = None) -> tuple:
        """
        Ajusta el stop loss y take profit para GARANTIZAR stops válidos, ejecutables y óptimos.
        NUNCA retorna stops inválidos. Usa ATR, multiplicadores dinámicos y lógica de fallback robusta.
        
        Args:
            signal_type: "BUY" o "SELL"
            entry_price: Precio de entrada
            stop_loss: Stop loss propuesto
            take_profit: Take profit propuesto
            symbol_info: Info del símbolo (para stops_level y point)
            atr: Valor ATR actual (opcional, para stops dinámicos)
        Returns:
            (stop_loss_ajustado, take_profit_ajustado, True) - SIEMPRE válidos
        """
        import math
        
        # Validación de entrada
        if entry_price <= 0:
            logger.error(f"[ADJUST_STOPS] Entry price inválido: {entry_price}")
            entry_price = 1.0  # Fallback seguro
            
        point = symbol_info.get('point', 0.0001)
        stops_level = symbol_info.get('stops_level', 0)
        digits = symbol_info.get('digits', 5)
        
        # Garantizar que point nunca sea 0
        if point <= 0:
            point = 0.01 if 'JPY' in str(symbol_info.get('symbol', '')) else 0.0001
            logger.warning(f"[ADJUST_STOPS] Point era 0, ajustado a {point}")
        
        # Distancia mínima ROBUSTA y EJECUTABLE
        base_distance = max(stops_level * point if stops_level > 0 else 10 * point, 5 * point)
        
        # Factor de seguridad adicional para garantizar ejecución
        safety_multiplier = 3.0  # Triplicar distancia mínima para máxima seguridad
        min_sl_distance = base_distance * safety_multiplier
        
        # Si ATR disponible, usar como referencia mínima mejorada
        if atr is not None and atr > 0:
            atr_based_distance = atr * 0.8  # 80% del ATR como mínimo
            min_sl_distance = max(min_sl_distance, atr_based_distance)
            logger.info(f"[ADJUST_STOPS] Usando ATR para distancia mínima: {atr_based_distance}")
        
        # Multiplicadores dinámicos optimizados
        sl_mult = max(1.2, symbol_info.get('sl_multiplier', 1.5))  # Mínimo 1.2x ATR
        tp_mult = max(2.0, symbol_info.get('tp_multiplier', 2.5))  # Mínimo 2.0x ATR

        # --- TP DINÁMICO SEGÚN ESTRUCTURA DEL MERCADO Y ATR ---
        # Si tienes un módulo de estructura, reemplaza este bloque por la lógica real de swing high/low o soporte/resistencia
        if atr is not None and atr > 0:
            adx = symbol_info.get('adx', None)
            # Ajuste de tp_mult según ADX (fuerza de tendencia)
            if adx is not None:
                if adx > 25:
                    tp_mult = 2.5  # Mercado fuerte, TP más ambicioso
                elif adx < 15:
                    tp_mult = 1.5  # Mercado débil, TP más conservador
            # Rango dinámico: entre 1.5 y 2.5 × ATR
            if signal_type == "BUY":
                take_profit = entry_price + max(tp_mult * atr, min_sl_distance)
                stop_loss = entry_price - max(sl_mult * atr, min_sl_distance)
            else:
                take_profit = entry_price - max(tp_mult * atr, min_sl_distance)
                stop_loss = entry_price + max(sl_mult * atr, min_sl_distance)
            logger.info(f"[ADJUST_STOPS] TP dinámico: SL={stop_loss}, TP={take_profit}, ATR={atr}, ADX={adx}")
        
        # --- VALIDACIÓN Y AJUSTE FINAL ROBUSTO ---
        if signal_type == "BUY":
            # Para BUY: SL debe estar DEBAJO del entry
            if stop_loss >= entry_price or stop_loss <= 0:
                stop_loss = entry_price - min_sl_distance
                logger.warning(f"[ADJUST_STOPS] SL BUY ajustado por validación: {stop_loss}")
            
            # Garantizar distancia mínima
            if entry_price - stop_loss < min_sl_distance:
                stop_loss = entry_price - min_sl_distance
                logger.warning(f"[ADJUST_STOPS] SL BUY ajustado por distancia: {stop_loss}")
            
            # Para BUY: TP debe estar ARRIBA del entry
            if take_profit <= entry_price or take_profit <= 0:
                take_profit = entry_price + min_sl_distance
                logger.warning(f"[ADJUST_STOPS] TP BUY ajustado por validación: {take_profit}")
            
            # Garantizar distancia mínima TP
            if take_profit - entry_price < min_sl_distance:
                take_profit = entry_price + min_sl_distance
                logger.warning(f"[ADJUST_STOPS] TP BUY ajustado por distancia: {take_profit}")
                
        else:  # SELL
            # Para SELL: SL debe estar ARRIBA del entry
            if stop_loss <= entry_price or stop_loss <= 0:
                stop_loss = entry_price + min_sl_distance
                logger.warning(f"[ADJUST_STOPS] SL SELL ajustado por validación: {stop_loss}")
            
            # Garantizar distancia mínima
            if stop_loss - entry_price < min_sl_distance:
                stop_loss = entry_price + min_sl_distance
                logger.warning(f"[ADJUST_STOPS] SL SELL ajustado por distancia: {stop_loss}")
            
            # Para SELL: TP debe estar DEBAJO del entry
            if take_profit >= entry_price or take_profit <= 0:
                take_profit = entry_price - min_sl_distance
                logger.warning(f"[ADJUST_STOPS] TP SELL ajustado por validación: {take_profit}")
            
            # Garantizar distancia mínima TP
            if entry_price - take_profit < min_sl_distance:
                take_profit = entry_price - min_sl_distance
                logger.warning(f"[ADJUST_STOPS] TP SELL ajustado por distancia: {take_profit}")
        
        # --- VALIDACIÓN DE RATIO RIESGO/BENEFICIO ---
        sl_distance = abs(entry_price - stop_loss)
        tp_distance = abs(take_profit - entry_price)
        
        # Garantizar ratio mínimo 1:1.3
        if tp_distance < sl_distance * 1.3:
            if signal_type == "BUY":
                take_profit = entry_price + (sl_distance * 1.5)
            else:
                take_profit = entry_price - (sl_distance * 1.5)
            logger.info(f"[ADJUST_STOPS] TP ajustado para ratio 1:1.5 = {take_profit}")
        
        # --- PREVENIR VALORES NEGATIVOS O CERO ---
        if stop_loss <= 0:
            stop_loss = entry_price * 0.95 if signal_type == "BUY" else entry_price * 1.05
            logger.error(f"[ADJUST_STOPS] SL era <= 0, ajustado a {stop_loss}")
        
        if take_profit <= 0:
            take_profit = entry_price * 1.05 if signal_type == "BUY" else entry_price * 0.95
            logger.error(f"[ADJUST_STOPS] TP era <= 0, ajustado a {take_profit}")
        
        # --- REDONDEO FINAL ---
        stop_loss = round(stop_loss, digits)
        take_profit = round(take_profit, digits)
        
        logger.info(f"[ADJUST_STOPS] FINAL {signal_type}: Entry={entry_price}, SL={stop_loss}, TP={take_profit}")
        
        # GARANTIZAR que NUNCA retornamos stops inválidos
        return stop_loss, take_profit, True

    def calculate_risk_amount(self, balance: float, risk_pct: float = 0.01, *args, **kwargs) -> float:
        """
        Calcula el monto a arriesgar por operación según el balance o free_margin y el porcentaje de riesgo.
        Si el balance o free_margin es muy bajo, retorna un mínimo seguro (ej. 100 USD).
        """
        try:
            risk_pct = float(risk_pct)
            balance = float(balance)
            # Si el balance es muy bajo, usar mínimo seguro
            if balance <= 0:
                logger.warning(f"[RISK AMOUNT] Balance/free_margin <= 0, usando fallback de 100.0")
                return 100.0
            risk_amount = balance * risk_pct
            # Si el resultado es muy bajo, usar mínimo seguro
            if risk_amount < 10.0:
                logger.warning(f"[RISK AMOUNT] Monto de riesgo muy bajo ({risk_amount}), usando mínimo 10.0")
                return 10.0
            logger.info(f"[RISK AMOUNT] Calculado: balance={balance}, risk_pct={risk_pct} => risk_amount={risk_amount}")
            return risk_amount
        except Exception as e:
            logger.error(f"[RISK AMOUNT] Error calculando monto de riesgo: {e}")
            return 100.0
    def calculate_dynamic_exposure_limit(self, free_margin: float, symbol: str, strategy: dict, *args, **kwargs) -> float:
        """
        Calcula el límite dinámico de exposición para un símbolo basado en el free_margin real y el 1% de riesgo máximo.
        Siempre usa el free_margin actual, nunca el balance, y nunca descarta señales válidas si el free_margin es suficiente para cubrir el margen requerido de la nueva posición.
        """
        if free_margin is None or free_margin <= 0:
            logger.warning(f"[EXPOSURE LIMIT] free_margin no proporcionado o inválido, usando 0 como referencia")
            free_margin = 0.0
        # Ajuste: usar 40% para FOREX, 25% para metales, 20% para índices
        symbol_upper = symbol.upper() if symbol else ''
        if any(x in symbol_upper for x in ['XAU', 'XAG', 'GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM']):
            max_risk_pct = 0.25
        elif any(x in symbol_upper for x in ['EUR', 'USD', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']):
            max_risk_pct = 0.40
        else:
            max_risk_pct = 0.20
        limit = free_margin * max_risk_pct
        logger.info(f"[EXPOSURE LIMIT] Para {symbol}: free_margin={free_margin}, límite {max_risk_pct*100:.0f}%={limit}")
        return limit
    def calculate_margin_buffer(self, volume: float, contract_size: float, price: float, leverage: float = 100.0, symbol: str = None, *args, **kwargs) -> float:
        """
        Calcula el margen requerido para una operación, compatible con llamadas de 4 a 6 argumentos.
        Si se pasa un diccionario como uno de los argumentos, extrae los valores necesarios.
        """
        # Compatibilidad con llamadas variables y argumentos tipo dict
        # Permite: (volume, contract_size, price, leverage, symbol, symbol_info)
        # o (volume, contract_size, price, symbol_info_dict)
        # o (volume, contract_size, price, leverage, symbol, ...)
        # Si se pasa un dict en vez de leverage, lo detectamos
        if isinstance(leverage, dict):
            symbol_info = leverage
            leverage = symbol_info.get('leverage', 100.0)
            symbol = symbol_info.get('symbol', symbol)
        elif len(args) > 0 and isinstance(args[0], dict):
            symbol_info = args[0]
            leverage = symbol_info.get('leverage', 100.0)
            symbol = symbol_info.get('symbol', symbol)
        # Validación de tipos
        try:
            volume = float(volume)
            contract_size = float(contract_size)
            price = float(price)
            leverage = float(leverage) if leverage else 100.0
        except Exception as e:
            logger.error(f"[MARGIN BUFFER] Error de tipo en argumentos: {e}")
            return 0.0
        # Cálculo estándar de margen
        try:
            margin = (volume * contract_size * price) / leverage
            logger.info(f"[MARGIN BUFFER] Calculado para {symbol}: Vol={volume}, CS={contract_size}, Price={price}, Lev={leverage} => Margin={margin:.2f}")
            return margin
        except Exception as e:
            logger.error(f"[MARGIN BUFFER] Error calculando margen: {e}")
            return 0.0
        """
        Calcula el margen requerido con un buffer dinámico basado en la volatilidad del símbolo.
        Admite entre 4 y 6 argumentos posicionales para máxima compatibilidad.

        Args:
            volume: Volumen de la posición.
            contract_size: Tamaño del contrato del símbolo.
            price: Precio actual del símbolo.
            leverage: Apalancamiento del símbolo (opcional, por compatibilidad)
            symbol: Símbolo de trading (opcional, por compatibilidad)
            *args: Argumentos adicionales ignorados para compatibilidad.
            **kwargs: Argumentos adicionales ignorados para compatibilidad.

        Returns:
            Margen requerido con buffer dinámico.
        """
        try:
            # Permitir llamada con 4, 5 o 6 argumentos posicionales
            # Si se llama con más de 4 argumentos, reasignar según orden esperado
            if len(args) >= 1 and symbol is None:
                symbol = args[0]
            if len(args) >= 2:
                # Si se pasa un sexto argumento, lo ignoramos (compatibilidad futura)
                pass
            # Si leverage no es válido, intentar obtenerlo por símbolo
            if (leverage is None or leverage <= 0) and hasattr(self, 'symbol_leverage') and symbol is not None:
                leverage = self.symbol_leverage.get(symbol, 100.0)
            if leverage is None or leverage <= 0:
                leverage = 100.0
            base_margin = (volume * contract_size * price) / leverage
            volatility = self._determine_volatility(symbol) if symbol is not None else 'low'
            buffer_factor = 1.1 if volatility == 'low' else 1.25
            return base_margin * buffer_factor
        except Exception as e:
            logger.error(f"Error calculando margen con buffer para {symbol}: {str(e)}")
            return 0.0

    def _determine_volatility(self, symbol: str) -> str:
        """
        Determina la volatilidad del símbolo basado en parámetros predefinidos.

        Args:
            symbol: Símbolo de trading.

        Returns:
            'low', 'medium', o 'high' dependiendo de la volatilidad.
        """
        if 'XAU' in symbol or 'XAG' in symbol:
            return 'high'
        elif symbol.endswith('JPY'):
            return 'medium'
        else:
            return 'low'
    
    def calculate_leverage(self, symbol: str) -> int:
        """
        Calcula el leverage según el tipo de instrumento.
        """
        category = self._categorize_by_symbol_name(symbol)
        leverage_map = {
            "forex": 500,
            "metal": 100,
            "index": 50,
            "other": 20
        }
        return leverage_map.get(category, 100)  # Default: 100

    def optimize_sl_tp(self, entry_price: float, atr: float) -> Tuple[float, float]:
        """
        Optimiza los niveles de SL y TP basados en ATR y volatilidad.
        """
        sl = entry_price - atr * 1.5
        tp = entry_price + atr * 2.5
        return sl, tp

    """
    Risk management class for calculating position sizes and managing trades
    """
    
    def __init__(self, risk_params: Optional[RiskParameters] = None):
        """
        Initialize risk manager
        
        Args:
            risk_params: Risk parameters, uses default if None
        """
        self.risk_params = risk_params or RiskParameters()
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.positions_count = 0
        self.symbol_leverage = {}  # New attribute to store symbol-specific leverage

    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float, 
                               account_balance: float, symbol_info: Dict, free_margin: float = None, 
                               take_profit: float = None, signal_type: str = None) -> Optional[PositionSize]:
        """
        Calcula el tamaño de la posición según el modo de riesgo configurado (porcentaje de margen o monto fijo en USD).
        Si el modo es 'fixed_usd', usa el monto fijo configurado en risk_config.py.
        Si el modo es 'percent_margin', usa el cálculo clásico (1% del margen disponible).
        """
        from risk_config import RISK_MODE, FIXED_RISK_USD
        if RISK_MODE == "fixed_usd":
            return self.calculate_position_size_fixed_usd(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                symbol_info=symbol_info,
                fixed_risk_usd=FIXED_RISK_USD
            )
        # --- MODO CLÁSICO: porcentaje de margen ---
        try:
            # --- INTEGRACIÓN DE AJUSTE DE STOPS ---
            if signal_type is not None and take_profit is not None:
                stop_loss, take_profit, _ = self.adjust_stops(signal_type, entry_price, stop_loss, take_profit, symbol_info)

            # Validar que el SL no sea igual al entry
            sl_distance = abs(entry_price - stop_loss)
            if sl_distance == 0:
                logger.error(f"[POSITION SIZE] SL igual a entry para {symbol}. Aplicando distancia mínima de emergencia.")
                # En lugar de abortar, usar distancia mínima de emergencia
                point = symbol_info.get('point', 0.0001)
                emergency_distance = max(10 * point, 0.001)
                if signal_type == "BUY":
                    stop_loss = entry_price - emergency_distance
                else:
                    stop_loss = entry_price + emergency_distance
                sl_distance = emergency_distance
                logger.warning(f"[POSITION SIZE] SL de emergencia aplicado: {stop_loss}")

            # Usar el margen libre como referencia de riesgo real
            if free_margin is None or free_margin <= 0:
                logger.warning(f"[POSITION SIZE] free_margin no proporcionado o inválido, usando balance como referencia")
                free_margin = account_balance

            max_risk_pct = min(self.risk_params.max_risk_per_trade, 0.01)  # Máximo 1%
            risk_amount = free_margin * max_risk_pct

            # Cálculo de valor por pip/lote ROBUSTO
            contract_size = symbol_info.get('contract_size', 100000.0)
            # ...resto del código clásico...
        except Exception as e:
            logger.error(f"Error en cálculo de posición (percent_margin) para {symbol}: {e}")
            min_vol = symbol_info.get('volume_min', 0.01)
            return PositionSize(
                volume=min_vol,
                risk_amount=0.0,
                risk_percentage=0.0,
                pip_value=10.0,
                stop_loss_pips=10.0
            )
            
            # Determinar pip_size según el símbolo de forma más robusta
            if 'JPY' in symbol:
                pip_size = 0.01
            elif any(metal in symbol for metal in ['XAU', 'XAG', 'GOLD', 'SILVER']):
                pip_size = 0.1  # Metales tienen pip_size mayor
            else:
                pip_size = 0.0001  # Forex estándar
            
            # CRÍTICO: Garantizar que sl_distance y pip_size NUNCA sean 0
            if sl_distance <= 0:
                sl_distance = pip_size * 10  # Distancia mínima de emergencia
                logger.warning(f"[POSITION SIZE] sl_distance era 0, ajustado a {sl_distance}")
            
            if pip_size <= 0:
                pip_size = 0.0001  # Fallback seguro
                logger.warning(f"[POSITION SIZE] pip_size era 0, ajustado a {pip_size}")
            
            sl_pips = sl_distance / pip_size
            
            # Calcular pip_value de forma más robusta
            pip_value_per_lot = pip_size * contract_size
            
            # Usar tick_value si está disponible, sino usar cálculo estándar
            tick_value = symbol_info.get('tick_value', 0)
            if tick_value > 0:
                pip_value = tick_value
            else:
                pip_value = pip_value_per_lot
            
            # CRÍTICO: Garantizar que pip_value NUNCA sea 0
            if pip_value <= 0:
                # Fallback basado en categoría del símbolo
                if 'JPY' in symbol:
                    pip_value = 1000.0  # Valor típico para pares JPY
                elif any(metal in symbol for metal in ['XAU', 'XAG']):
                    pip_value = 100.0   # Valor típico para metales
                else:
                    pip_value = 10.0    # Valor típico para forex
                logger.warning(f"[POSITION SIZE] pip_value era 0, usando fallback: {pip_value}")

            # Validar que todos los valores sean positivos
            if sl_pips <= 0:
                sl_pips = 10.0  # Mínimo 10 pips de emergencia
                logger.warning(f"[POSITION SIZE] sl_pips ajustado a emergencia: {sl_pips}")

            # Volumen inicial sugerido para que el riesgo en SL sea <= risk_amount
            volume = risk_amount / (sl_pips * pip_value)

            # Ajuste por volumen mínimo/máximo del símbolo
            min_vol = symbol_info.get('volume_min', symbol_info.get('min_volume', 0.01))
            max_vol = symbol_info.get('volume_max', symbol_info.get('max_volume', 100.0))
            step_vol = symbol_info.get('volume_step', 0.01)
            
            # Garantizar que min_vol nunca sea 0
            if min_vol <= 0:
                min_vol = 0.01
                logger.warning(f"[POSITION SIZE] min_vol era 0, ajustado a {min_vol}")
            
            # Redondear al múltiplo permitido
            volume = max(min_vol, min(max_vol, round(volume / step_vol) * step_vol))

            # Si hay margen libre, ajustar para no excederlo
            margin_per_lot = symbol_info.get('margin_initial', 100.0)
            if margin_per_lot > 0:
                max_lots_by_margin = free_margin / margin_per_lot
                if volume > max_lots_by_margin:
                    logger.warning(f"[POSITION SIZE] Volumen ajustado por margen: {volume} → {max_lots_by_margin:.2f} para {symbol}")
                    volume = max(min_vol, min(max_vol, round(max_lots_by_margin / step_vol) * step_vol))

            # NUNCA descartar la señal - siempre devolver un volumen válido
            if volume < min_vol:
                logger.warning(f"[POSITION SIZE] Volumen muy bajo, usando mínimo: {min_vol} para {symbol}")
                volume = min_vol

            # Garantizar volumen final positivo
            if volume <= 0:
                volume = min_vol
                logger.warning(f"[POSITION SIZE] Volumen era 0, usando mínimo: {min_vol} para {symbol}")

            # Retornar el objeto de tamaño de posición
            return PositionSize(
                volume=volume,
                risk_amount=risk_amount,
                risk_percentage=(risk_amount / free_margin) * 100,
                pip_value=pip_value,
                stop_loss_pips=sl_pips
            )
        except Exception as e:
            logger.error(f"Error en cálculo de posición para {symbol}: {e}")
            # En lugar de retornar None, devolver valores mínimos seguros
            min_vol = symbol_info.get('volume_min', 0.01)
            return PositionSize(
                volume=min_vol,
                risk_amount=account_balance * 0.005,  # 0.5% como emergencia
                risk_percentage=0.5,
                pip_value=10.0,
                stop_loss_pips=10.0
            )

            # Si hay margen libre, ajustar para no excederlo
            margin_per_lot = symbol_info.get('margin_initial', 100.0)
            max_lots_by_margin = free_margin / margin_per_lot
            if volume > max_lots_by_margin:
                logger.warning(f"[POSITION SIZE] Volumen ajustado por margen: {volume} → {max_lots_by_margin:.2f} para {symbol}")
                volume = max(min_vol, min(max_vol, round(max_lots_by_margin / step_vol) * step_vol))

            # Nunca descartar la señal aquí, solo advertir si el volumen es muy bajo
            if volume < min_vol:
                logger.warning(f"[POSITION SIZE] Volumen calculado por debajo del mínimo permitido para {symbol}: {volume}")
                volume = min_vol

            # Validar volumen final
            if volume <= 0:
                logger.error(f"[POSITION SIZE] Volumen calculado <= 0 para {symbol}. Señal abortada.")
                return None

            # Retornar el objeto de tamaño de posición
            return PositionSize(
                volume=volume,
                risk_amount=risk_amount,
                risk_percentage=(risk_amount / free_margin) * 100,
                pip_value=pip_value,
                stop_loss_pips=sl_pips
            )
        except Exception as e:
            logger.error(f"Error en cálculo de posición para {symbol}: {e}")
            return None

    def validate_exposure_and_margin(self, symbol: str, volume: float, account_info: Dict, symbol_info: Dict) -> bool:
        """
        Valida exposición y margen de forma flexible: solo rechaza si la exposición supera 110% del máximo permitido.
        Si está cerca del límite, solo advierte y permite que MT5 decida. Nunca descarta señales por margen/exposición salvo casos extremos.
        """
        try:
            max_positions = self.risk_params.max_open_positions
            # Exposición actual y máxima
            current_exposure = account_info.get('current_exposure', 0.0)
            max_exposure = account_info.get('max_exposure', 1.0)

            # Calcular buffer dinámico basado en condiciones actuales
            buffer_percentage = 0.1  # 10% por defecto
            dynamic_buffer = max_exposure * (1 + buffer_percentage)

            # Si la exposición supera el límite dinámico, rechazar
            if current_exposure + volume > dynamic_buffer:
                logger.error(f"Exposición rechazada: {current_exposure + volume:.2f} > {dynamic_buffer:.2f} para {symbol}")
                return False

            # Si está por encima del máximo pero debajo del buffer, advertir
            if current_exposure + volume > max_exposure:
                logger.warning(f"Exposición alta: {current_exposure + volume:.2f} > {max_exposure:.2f} para {symbol}, se permite y MT5 decidirá.")

            # Validar número de posiciones abiertas
            open_positions = account_info.get('open_positions', 0)
            if open_positions >= max_positions:
                logger.warning(f"Máximo de posiciones abiertas alcanzado: {open_positions} >= {max_positions} para {symbol}, se permite y MT5 decidirá.")

            # Registrar detalles adicionales para diagnóstico
            logger.info(f"Validación completada: Exposición actual={current_exposure:.2f}, Máxima={max_exposure:.2f}, Buffer dinámico={dynamic_buffer:.2f}")

            return True
        except Exception as e:
            logger.error(f"Error en validación de exposición/margen para {symbol}: {e}")
            return True  # Permisivo por defecto
        """
        Calcula el tamaño de posición óptimo basado en gestión de riesgo,
        garantizando que el riesgo máximo sea 1% del free margin.
        """
        try:
            # Obtener el free margin de la cuenta
            if free_margin is None:
                free_margin = account_balance * 0.9  # Estimación conservadora

            # Enforce a strict maximum of 1% risk per trade (hard cap)
            max_risk_per_trade = min(self.risk_params.max_risk_per_trade, 0.01)

            # Calcular basado en el menor valor entre free margin y balance
            risk_reference = min(free_margin, account_balance)
            risk_amount = risk_reference * max_risk_per_trade

            # Calculate stop loss distance in price
            stop_loss_distance = abs(entry_price - stop_loss)
            if stop_loss_distance <= 0:
                logger.error(f"Stop loss distance inválida para {symbol}: {stop_loss_distance}")
                return None

            # Calcular pip value
            contract_size = symbol_info.get('contract_size', 100000.0)
            pip_value = contract_size * stop_loss_distance

            # Calcular volumen máximo permitido
            max_possible_volume = risk_amount / pip_value
            volume_step = symbol_info.get('volume_step', 0.01)
            adjusted_volume = math.floor(max_possible_volume / volume_step) * volume_step

            if adjusted_volume < symbol_info.get('min_volume', 0.01):
                logger.warning(f"Volumen ajustado ({adjusted_volume}) menor al mínimo permitido para {symbol}")
                return None

            return PositionSize(
                volume=adjusted_volume,
                risk_amount=risk_amount,
                risk_percentage=max_risk_per_trade,
                pip_value=pip_value,
                stop_loss_pips=stop_loss_distance
            )

        except Exception as e:
            logger.error(f"Error calculando tamaño de posición para {symbol}: {str(e)}")
            return None
    
    def validate_trade(self, signal_type: str, entry_price: float, stop_loss: float, 
                      take_profit: float, account_balance: float, symbol: str, symbol_info: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Validate if trade meets risk management criteria
        
        Args:
            signal_type: "BUY" or "SELL"
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            account_balance: Account balance
            symbol: Trading symbol
            symbol_info: Symbol information from MT5 (for stops_level)
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:


            # Ensure positions_count is updated correctly
            if self.positions_count < 0:
                logger.error("Invalid positions_count: cannot be negative.")
                self.positions_count = 0

            # Check daily loss limit
            if self.daily_pnl < 0:
                daily_loss_percentage = abs(self.daily_pnl) / account_balance
                if daily_loss_percentage >= self.risk_params.max_daily_loss:
                    return False, f"Daily loss limit ({self.risk_params.max_daily_loss*100:.1f}%) reached"
            
            # Calculate risk-reward ratio
            if signal_type == "BUY":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # SELL
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk <= 0:
                return False, "Invalid stop loss: risk must be positive."
            
            risk_reward_ratio = reward / risk
            if risk_reward_ratio < self.risk_params.min_risk_reward_ratio:
                logger.warning(f"Risk-reward ratio below minimum: {risk_reward_ratio:.2f} < {self.risk_params.min_risk_reward_ratio}")
                return False, f"Risk-reward ratio ({risk_reward_ratio:.2f}) below minimum ({self.risk_params.min_risk_reward_ratio})"

            # Check if stop loss is too close (use broker stops_level if available)
            if symbol_info is not None:
                point = symbol_info.get('point', 0.00001)
                stops_level = symbol_info.get('stops_level', 0)
                min_sl_distance = stops_level * point
            else:
                min_sl_distance = 5 * (0.01 if 'JPY' in symbol else 0.0001)
            if abs(entry_price - stop_loss) < min_sl_distance:
                return False, f"Stop loss distance {abs(entry_price - stop_loss)} is less than broker minimum {min_sl_distance} for {symbol}"

            # Enforce strict 1% risk per trade
            max_risk_per_trade = min(self.risk_params.max_risk_per_trade, 0.01)
            risk_amount = account_balance * max_risk_per_trade
            sl_distance = abs(entry_price - stop_loss)
            contract_size = symbol_info.get('contract_size', 100000) if symbol_info else 100000
            if symbol.endswith('JPY'):
                pip_size = 0.01
            else:
                pip_size = 0.0001
            sl_pips = sl_distance / pip_size
            pip_value_per_lot = pip_size * contract_size
            # Estimate volume for 1% risk
            if sl_pips > 0 and pip_value_per_lot > 0:
                volume = risk_amount / (sl_pips * pip_value_per_lot)
                min_volume = symbol_info.get('volume_min', 0.01) if symbol_info else 0.01
                max_volume = symbol_info.get('volume_max', 100.0) if symbol_info else 100.0
                volume_step = symbol_info.get('volume_step', 0.01) if symbol_info else 0.01
                volume = round(volume / volume_step) * volume_step
                volume = max(min_volume, min(volume, max_volume))
                actual_risk = volume * sl_pips * pip_value_per_lot
                risk_percentage = (actual_risk / account_balance) * 100
                if risk_percentage > 1.0:
                    logger.warning(f"Calculated risk exceeds 1% cap: {risk_percentage:.2f}%")
                    return False, f"Calculated risk {risk_percentage:.2f}% exceeds 1% cap."
            
            return True, "Trade validation passed"
            
        except Exception as e:
            logger.error(f"Error validating trade: {str(e)}")
            return False, f"Exception during validation: {str(e)}"
    
    def should_move_to_breakeven(self, signal_type: str, entry_price: float, 
                                current_price: float, atr_value: float) -> bool:
        """
        Check if position should be moved to breakeven
        
        Args:
            signal_type: "BUY" or "SELL"
            entry_price: Entry price
            current_price: Current price
            atr_value: ATR value
            
        Returns:
            True if should move to breakeven
        """
        try:
            breakeven_distance = atr_value * self.risk_params.breakeven_multiplier
            
            if signal_type == "BUY":
                return current_price >= entry_price + breakeven_distance
            else:  # SELL
                return current_price <= entry_price - breakeven_distance
                
        except Exception as e:
            logger.error(f"Error checking breakeven: {str(e)}")
            return False
    
    def calculate_trailing_stop(self, signal_type: str, entry_price: float, 
                               current_price: float, atr_value: float) -> Optional[float]:
        """
        Calculate trailing stop level
        
        Args:
            signal_type: "BUY" or "SELL"
            entry_price: Entry price
            current_price: Current price
            atr_value: ATR value
            
        Returns:
            New stop loss level or None
        """
        try:
            trailing_distance = atr_value * self.risk_params.trailing_stop_multiplier
            
            if signal_type == "BUY":
                new_sl = current_price - trailing_distance
                # Only move stop loss up
                return new_sl if new_sl > entry_price else None
            else:  # SELL
                new_sl = current_price + trailing_distance
                # Only move stop loss down
                return new_sl if new_sl < entry_price else None
                
        except Exception as e:
            logger.error(f"Error calculating trailing stop: {str(e)}")
            return None
    
    def update_daily_pnl(self, pnl: float) -> None:
        """
        Update daily P&L tracking
        
        Args:
            pnl: Profit/Loss amount
        """
        self.daily_pnl += pnl
        self.daily_trades += 1
        logger.info(f"Daily P&L updated: ${self.daily_pnl:.2f}, Trades: {self.daily_trades}")
    
    def increment_positions(self) -> None:
        """Increment open positions counter"""
        self.positions_count += 1
        logger.info(f"Open positions: {self.positions_count}")
    
    def decrement_positions(self) -> None:
        """Decrement open positions counter"""
        if self.positions_count > 0:
            self.positions_count -= 1
        logger.info(f"Open positions: {self.positions_count}")
    
    def reset_daily_stats(self) -> None:
        """Reset daily statistics (call at start of new trading day)"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        logger.info("Daily statistics reset")
    
    def get_risk_summary(self) -> Dict:
        """
        Get current risk summary
        
        Returns:
            Dictionary with risk statistics
        """
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'open_positions': self.positions_count,
            'max_risk_per_trade': self.risk_params.max_risk_per_trade,
            'max_daily_loss': self.risk_params.max_daily_loss,
            'max_open_positions': self.risk_params.max_open_positions
        }
    
    def is_trading_allowed(self, account_balance: float) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on current risk status
        
        Args:
            account_balance: Current account balance
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        try:
            # Check daily loss limit
            if self.daily_pnl < 0:
                daily_loss_percentage = abs(self.daily_pnl) / account_balance
                if daily_loss_percentage >= self.risk_params.max_daily_loss:
                    return False, f"Daily loss limit reached: {daily_loss_percentage*100:.1f}%"

            # Enforce max open positions (para compatibilidad con tests)
            if self.risk_params.max_open_positions > 0 and self.positions_count >= self.risk_params.max_open_positions:
                return False, f"Maximum positions limit reached: {self.positions_count} >= {self.risk_params.max_open_positions}"

            return True, "Trading allowed"
        except Exception as e:
            logger.error(f"Error checking trading status: {str(e)}")
            return False, f"Error checking trading status: {str(e)}"
    
    def calculate_position_size_dynamic(self, symbol: str, entry_price: float, 
                                       stop_loss: float, account_balance: float, 
                                       mt5_connector) -> Optional[PositionSize]:
        """
        Calculate position size using dynamic symbol specifications
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            account_balance: Current account balance
            mt5_connector: MT5Connector instance for dynamic specs
            
        Returns:
            PositionSize object or None if calculation fails
        """
        try:
            # Get dynamic symbol specifications
            symbol_specs = mt5_connector.get_dynamic_trading_params(symbol)
            if not symbol_specs or not isinstance(symbol_specs, dict):
                logger.error(f"Cannot get symbol specifications for {symbol}")
                return None
            # Unificación de claves para robustez
            def get_spec(key, fallback_keys, default):
                for k in [key] + fallback_keys:
                    if k in symbol_specs:
                        return symbol_specs[k]
                return default
            # Extracción robusta de parámetros
            point = get_spec('point', ['pt', 'pip_size'], 0.00001)
            contract_size = get_spec('contract_size', ['trade_contract_size'], 100000)
            digits = get_spec('digits', [], 5)
            min_volume = get_spec('min_volume', ['volume_min', 'min_lot'], 0.01)
            max_volume = get_spec('max_volume', ['volume_max', 'max_lot'], 100.0)
            volume_step = get_spec('volume_step', ['lot_step'], 0.01)
            pip_value_per_lot = get_spec('tick_value', ['pip_value'], 1.0)
            # Cálculo de riesgo
            risk_amount = account_balance * self.risk_params.max_risk_per_trade
            sl_distance = abs(entry_price - stop_loss)
            sl_distance_points = sl_distance / (point if point else 0.00001)
            if pip_value_per_lot > 0 and sl_distance_points > 0:
                required_volume = risk_amount / (sl_distance_points * pip_value_per_lot)
            else:
                logger.error(f"Invalid pip value or stop loss points for {symbol}")
                return None
            # Redondeo y límites
            volume_steps = round(required_volume / volume_step)
            final_volume = volume_steps * volume_step
            final_volume = max(min_volume, min(final_volume, max_volume))
            actual_risk = final_volume * sl_distance_points * pip_value_per_lot
            actual_risk_percentage = (actual_risk / account_balance) * 100
            # Cálculo de pips
            pip_size = 0.01 if symbol.endswith('JPY') else 0.0001
            sl_pips = sl_distance / pip_size if pip_size else sl_distance / 0.0001
            position_size = PositionSize(
                volume=final_volume,
                risk_amount=actual_risk,
                risk_percentage=actual_risk_percentage,
                pip_value=pip_value_per_lot,
                stop_loss_pips=sl_pips
            )
            logger.info(f"Dynamic position size for {symbol}: "
                        f"Volume={final_volume:.2f}, "
                        f"Risk=${actual_risk:.2f} ({actual_risk_percentage:.2f}%), "
                        f"SL={sl_pips:.1f} pips")
            return position_size
        except Exception as e:
            logger.error(f"Error calculating dynamic position size for {symbol}: {str(e)}")
            return None
            
            # Calculate actual risk with the calculated volume
            tick_value = symbol_specs['tick_value']
            actual_risk = sl_distance_points * tick_value * optimal_volume / symbol_specs['point']
            actual_risk_percentage = actual_risk / account_balance
            
            logger.info(f"Dynamic position size for {symbol}: {optimal_volume} lots, risk: ${actual_risk:.2f} ({actual_risk_percentage:.2%})")
            
            return PositionSize(
                volume=optimal_volume,
                risk_amount=actual_risk,
                risk_percentage=actual_risk_percentage,
                pip_value=tick_value,
                stop_loss_pips=sl_distance_points
            )
            
        except Exception as e:
            logger.error(f"Error calculating dynamic position size: {str(e)}")
            return None

    def validate_trade_dynamic(self, signal_type: str, entry_price: float, 
                             stop_loss: float, take_profit: float, 
                             account_balance: float, symbol: str, 
                             mt5_connector) -> Tuple[bool, str]:
        """
        Validate trade parameters using dynamic symbol specifications
        
        Args:
            signal_type: "BUY" or "SELL"
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            account_balance: Current account balance
            symbol: Trading symbol
            mt5_connector: MT5Connector instance
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Basic validation first
            is_valid, reason = self.validate_trade(
                signal_type, entry_price, stop_loss, take_profit, account_balance
            )
            
            if not is_valid:
                return is_valid, reason
            
            # Get symbol specifications for advanced validation
            symbol_specs = mt5_connector.get_symbol_specifications(symbol)
            if not symbol_specs:
                return False, f"Cannot get specifications for {symbol}"
            
            # Check if symbol is tradeable
            if not symbol_specs['tradeable']:
                return False, f"Symbol {symbol} is not tradeable"
            
            # Check market hours (simplified)
            market_hours = mt5_connector.get_market_hours(symbol)
            if market_hours and not market_hours.get('trade_allowed', True):
                return False, f"Trading not allowed for {symbol} at this time"
            
            # Validate against minimum stops level
            stops_level = symbol_specs['trade_stops_level']
            point = symbol_specs['point']
            min_distance = stops_level * point
            
            sl_distance = abs(entry_price - stop_loss)
            tp_distance = abs(take_profit - entry_price) if signal_type == "BUY" else abs(entry_price - take_profit)
            
            if sl_distance < min_distance:
                return False, f"SL distance {sl_distance:.6f} below minimum {min_distance:.6f}"
            
            if tp_distance < min_distance:
                return False, f"TP distance {tp_distance:.6f} below minimum {min_distance:.6f}"
            
            # Check spread impact
            current_spread = symbol_specs.get('current_spread_points', 0)
            if current_spread > 0:
                spread_cost = current_spread * symbol_specs['point']
                if spread_cost > sl_distance * 0.1:  # Spread shouldn't be more than 10% of SL
                    return False, f"Spread too wide: {current_spread} points"
            
            return True, "Dynamic validation passed"
            
        except Exception as e:
            logger.error(f"Error in dynamic trade validation: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def calculate_dynamic_breakeven(self, symbol: str, signal_type: str, 
                                  entry_price: float, current_price: float, 
                                  atr_value: float, mt5_connector) -> bool:
        """
        Calculate breakeven using dynamic parameters
        
        Args:
            symbol: Trading symbol
            signal_type: "BUY" or "SELL"
            entry_price: Original entry price
            current_price: Current market price
            atr_value: ATR value
            mt5_connector: MT5Connector instance
            
        Returns:
            True if position should move to breakeven
        """
        try:
            # Get symbol specifications
            symbol_specs = mt5_connector.get_symbol_specifications(symbol)
            if not symbol_specs:
                return False
            
            # Calculate dynamic breakeven threshold based on symbol volatility
            base_multiplier = self.risk_params.breakeven_multiplier
            
            # Adjust multiplier based on symbol type
            if 'XAU' in symbol:  # Gold - more volatile
                multiplier = base_multiplier * 1.5
            elif symbol.endswith('JPY'):  # JPY pairs
                multiplier = base_multiplier * 0.8
            else:
                multiplier = base_multiplier
            
            threshold = atr_value * multiplier
            
            if signal_type == "BUY":
                profit = current_price - entry_price
            else:
                profit = entry_price - current_price
            
            should_move = profit >= threshold
            
            if should_move:
                logger.info(f"Breakeven trigger for {symbol}: profit {profit:.6f} >= threshold {threshold:.6f}")
            
            return should_move
            
        except Exception as e:
            logger.error(f"Error calculating dynamic breakeven: {str(e)}")
            return False

    def calculate_dynamic_trailing_stop(self, symbol: str, signal_type: str, 
                                       entry_price: float, current_price: float, 
                                       atr_value: float, mt5_connector) -> Optional[float]:
        """
        Calculate trailing stop using dynamic parameters
        
        Args:
            symbol: Trading symbol
            signal_type: "BUY" or "SELL"
            entry_price: Original entry price
            current_price: Current market price
            atr_value: ATR value
            mt5_connector: MT5Connector instance
            
        Returns:
            New trailing stop level or None
        """
        try:
            # Get symbol specifications
            symbol_specs = mt5_connector.get_symbol_specifications(symbol)
            if not symbol_specs:
                return None
            
            # Calculate dynamic trailing distance
            base_multiplier = self.risk_params.trailing_stop_multiplier
            
            # Adjust based on symbol characteristics
            if 'XAU' in symbol:  # Gold
                multiplier = base_multiplier * 1.2
            elif symbol.endswith('JPY'):  # JPY pairs
                multiplier = base_multiplier * 0.9
            else:
                multiplier = base_multiplier
            
            trailing_distance = atr_value * multiplier
            
            # Ensure trailing distance meets minimum stops level
            min_distance = symbol_specs['trade_stops_level'] * symbol_specs['point']
            trailing_distance = max(trailing_distance, min_distance)
            
            if signal_type == "BUY":
                new_sl = current_price - trailing_distance
            else:
                new_sl = current_price + trailing_distance
            
            # Round to symbol digits
            new_sl = round(new_sl, symbol_specs['digits'])
            
            return new_sl
            
        except Exception as e:
            logger.error(f"Error calculating dynamic trailing stop: {str(e)}")
            return None

    def is_instrument_orderable(self, symbol: str, signal_type: str, 
                          entry_price: float, mt5_connector) -> Tuple[bool, str]:
        """
        Verifica si el instrumento permite ordenar con los parámetros actuales.
        
        Args:
            symbol: Símbolo de trading
            signal_type: "BUY" o "SELL"
            entry_price: Precio de entrada
            mt5_connector: Instancia de MT5Connector
            
        Returns:
            Tupla de (es_orderable, razón)
        """
        try:
            # Obtener especificaciones
            specs = mt5_connector.get_symbol_specifications(symbol)
            if not specs:
                return False, f"No se pueden obtener especificaciones para {symbol}"
                
            # Verificar si el mercado está abierto
            if not specs.get('tradeable', False):
                return False, f"El símbolo {symbol} no es operable actualmente"
                
            # Verificar si es un instrumento compatible
            category = self._determine_instrument_category(symbol, specs)
            if category == "unknown":
                return False, f"Tipo de instrumento desconocido o no soportado: {symbol}"
                
            return True, "Instrumento validado correctamente"
            
        except Exception as e:
            logger.error(f"Error verificando instrumento {symbol}: {str(e)}")
            return False, f"Error en validación: {str(e)}"
    
    def check_sufficient_funds(self, symbol: str, volume: float, price: float, mt5_connector, signal_type=None, symbol_info: dict = None) -> bool:
        """
        Verifica si hay fondos suficientes para abrir una posición, usando solo symbol_info proporcionado o recuperado.
        Si el volumen es el mínimo permitido y aún así no hay margen, solo advierte pero no rechaza la señal (deja que MT5 decida).
        """
        try:
            if symbol_info is None:
                symbol_info = mt5_connector.get_symbol_info(symbol)
            contract_size = symbol_info.get('contract_size', 100000)
            leverage = symbol_info.get('leverage')
            if leverage is None or leverage <= 0:
                logger.error(f"Leverage inválido para {symbol}. Usando valor predeterminado de 100.")
                leverage = 100
            min_volume = symbol_info.get('min_volume', 0.01)
            margin_requirement = (volume * contract_size * price) / leverage
            required_with_buffer = margin_requirement * 1.25
            free_margin = mt5_connector.get_account_info().get('margin_free', 0)
            if free_margin < required_with_buffer:
                if volume <= min_volume:
                    logger.warning(f"⚠️ Fondos insuficientes para {symbol} incluso con volumen mínimo ({min_volume}). Se deja a MT5 la decisión final. Requerido={required_with_buffer:.2f}, Disponible={free_margin:.2f}")
                    return True  # Permitir que MT5 decida
                logger.warning(f"❌ Fondos insuficientes para {symbol}: Requerido={required_with_buffer:.2f}, Disponible={free_margin:.2f}")
                return False
            logger.info(f"✅ Fondos suficientes para {symbol}: Requerido={required_with_buffer:.2f}, Disponible={free_margin:.2f}")
            return True
        except Exception as e:
            logger.error(f"Error verificando fondos para {symbol}: {str(e)}")
            return False

    def validate_exposure_and_margin(self, symbol: str, proposed_exposure: float, free_margin: float, max_exposure: float) -> Tuple[bool, str]:
        """
        Validación flexible: solo descarta si la exposición supera el 110% del máximo permitido.
        Si está cerca del límite, advierte pero permite la señal (deja la decisión a MT5).
        """
        try:
            if proposed_exposure > max_exposure * 1.1:
                logger.warning(f"❌ Exposición máxima excedida para {symbol}: Actual={proposed_exposure:.2f}, Máxima={max_exposure:.2f}")
                return False, f"Exposición máxima excedida: Actual={proposed_exposure:.2f}, Máxima={max_exposure:.2f}"
            elif proposed_exposure > max_exposure:
                logger.warning(f"⚠️ Exposición total cercana al límite para {symbol}: Actual={proposed_exposure:.2f}, Máxima={max_exposure:.2f}. Se deja a MT5 la decisión final.")
                return True, f"Exposición cercana al límite: Actual={proposed_exposure:.2f}, Máxima={max_exposure:.2f} (permitido, MT5 decide)"
            else:
                logger.info(f"✅ Exposición válida para {symbol}: Actual={proposed_exposure:.2f}, Máxima={max_exposure:.2f}")
                return True, "Exposición válida"
        except Exception as e:
            logger.error(f"Error validando exposición y margen para {symbol}: {str(e)}")
            return True, f"Error validando exposición y margen: {str(e)} (permitido, MT5 decide)"
    
    def _is_high_priority_symbol(self, symbol: str) -> bool:
        """
        Determina si un símbolo es de alta prioridad para el trading.
        
        Args:
            symbol: Símbolo a verificar
            
        Returns:
            True si es un símbolo prioritario, False en caso contrario
        """
        high_priority_symbols = [
            # Forex Majors
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
            # Metales
            "XAUUSD", "XAGUSD", "GOLD", "SILVER",
            # Índices principales
            "US30", "SPX500", "NAS100", "GER30", "UK100"
        ]
        
        return symbol in high_priority_symbols
    
    def _determine_instrument_category(self, symbol: str, symbol_info: dict) -> str:
        """
        Determina la categoría del instrumento basado en su símbolo y propiedades.
        Versión robusta que maneja diferentes tipos de entradas y casos extremos.
        
        Args:
            symbol: Símbolo del instrumento
            symbol_info: Información del símbolo (puede ser dict, objeto o None)
            
        Returns:
            Categoría del instrumento: "forex", "index", "stock", "metal", "crypto", "unknown"
        """
        try:
            # Si symbol_info es None o vacío, categorizar solo por nombre
            if not symbol_info:
                return self._categorize_by_symbol_name(symbol)
                
            # Manejar path según el tipo de objeto
            path = ''
            if isinstance(symbol_info, dict):
                path = str(symbol_info.get('path', '')).lower()
            else:
                # Intentar acceder a 'path' como atributo
                try:
                    if hasattr(symbol_info, 'path') and symbol_info.path:
                        path = str(symbol_info.path).lower()
                except (AttributeError, TypeError):
                    # Si falla, usar categorización por nombre
                    return self._categorize_by_symbol_name(symbol)
            
            # Determinar por path si está disponible
            if path:
                if any(keyword in path for keyword in ['forex', 'currencies', 'fx', 'major', 'minor']):
                    return "forex"
                elif any(keyword in path for keyword in ['indices', 'index', 'indice']):
                    return "index"
                elif any(keyword in path for keyword in ['stocks', 'shares', 'acciones', 'equities']):
                    return "stock"
                elif any(keyword in path for keyword in ['metals', 'metales', 'commodities', 'xau', 'gold', 'xag']):
                    return "metal"
                elif any(keyword in path for keyword in ['crypto', 'bitcoin', 'ethereum', 'btc', 'eth']):
                    return "crypto"
            
            # Si no se pudo determinar por path, intentar por descripción
            description = ''
            if isinstance(symbol_info, dict):
                description = str(symbol_info.get('description', '')).lower()
            else:
                try:
                    if hasattr(symbol_info, 'description') and symbol_info.description:
                        description = str(symbol_info.description).lower()
                except (AttributeError, TypeError):
                    pass
                    
            if description:
                if any(keyword in description for keyword in ['forex', 'currency', 'currencies', 'fx']):
                    return "forex"
                elif any(keyword in description for keyword in ['index', 'indice']):
                    return "index"
                elif any(keyword in description for keyword in ['stock', 'share', 'accion', 'equity']):
                    return "stock"
                elif any(keyword in description for keyword in ['metal', 'gold', 'silver', 'oro', 'plata']):
                    return "metal"
                elif any(keyword in description for keyword in ['crypto', 'bitcoin', 'ethereum']):
                    return "crypto"
            
            # Si todo lo anterior falla, intentar por nombre del símbolo
            return self._categorize_by_symbol_name(symbol)
            
        except Exception as e:
            logger.error(f"Error en _determine_instrument_category para {symbol}: {str(e)}")
            # En caso de error, intentar categorización por nombre como fallback
            return self._categorize_by_symbol_name(symbol)
            
    def _categorize_by_symbol_name(self, symbol: str) -> str:
        """
        Categoriza un instrumento basado solo en el nombre del símbolo.
        Versión mejorada con detección más robusta para todo tipo de instrumentos.
        
        Args:
            symbol: Nombre del símbolo
            
        Returns:
            Categoría del instrumento
        """
        if not symbol:
            return "unknown"
            
        symbol_upper = symbol.upper()
        
        # Detección específica para símbolos de acciones con formatos especiales (como AME, AMG, AMT)
        stock_patterns_strict = [
            # Acciones mencionadas en los errores
            'AME', 'AMG', 'AMT', 
            # Otras acciones populares
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'INTC', 'IBM'
        ]
        
        # Verificar coincidencia exacta con acciones conocidas
        if symbol_upper in stock_patterns_strict:
            return "stock"
            
        # Detección de patrones con guiones (típico en acciones preferentes)
        if '-' in symbol_upper and (len(symbol_upper) <= 8):
            # Símbolos como "AHT-PH" son típicamente acciones preferentes
            return "stock"
        
        # Detección de FOREX con lógica mejorada
        forex_currencies = [
            'USD', 'EUR', 'JPY', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF', 
            'CNY', 'MXN', 'SEK', 'NOK', 'DKK', 'HKD', 'SGD', 'TRY', 
            'ZAR', 'BRL', 'PLN', 'RUB', 'INR', 'THB'
        ]
        
        # Detección de FOREX - evaluar primero para priorizar
        if len(symbol_upper) <= 8:  # Típicamente los pares FOREX tienen 6-8 caracteres
            # Verificar que tenga al menos dos códigos de moneda
            currencies_present = sum(1 for curr in forex_currencies if curr in symbol_upper)
            if currencies_present >= 2:
                return "forex"
                
            # Verificar formatos alternativos de FOREX (con separadores)
            if any(sep in symbol_upper for sep in ['/', '.', '_']) and currencies_present >= 1:
                return "forex"
        
        # Detección de metales preciosos mejorada
        metal_patterns = [
            'XAU', 'GOLD', 'XAG', 'SILVER', 'PLAT', 'PLATINUM', 
            'COPPER', 'PALLADIUM', 'XPD', 'XPT', 'XAUUSD', 'XAGUSD'
        ]
        if any(pattern in symbol_upper for pattern in metal_patterns):
            return "metal"
            
        # Detección de índices expandida
        index_patterns = [
            'US30', 'DOW', 'SPX', 'SP500', 'S&P', 'NAS100', 'NASDAQ', 'NDX', 
            'DAX', 'UK100', 'FTSE', 'CAC', 'IBEX', 'N225', 'HSI', 'ASX', 
            'STOXX', 'EURO50', 'RUSSELL', 'VIX'
        ]
        if any(pattern in symbol_upper for pattern in index_patterns):
            return "index"
            
        # Detección de criptomonedas expandida
        crypto_patterns = [
            'BTC', 'ETH', 'LTC', 'XRP', 'DOGE', 'BCH', 'BNB', 'USDT', 
            'ADA', 'DOT', 'LINK', 'SOL', 'MATIC', 'AVAX', 'XLM', 'UNI',
            'BITCOIN', 'ETHEREUM'
        ]
        if any(pattern in symbol_upper for pattern in crypto_patterns):
            return "crypto"
        
        # Detección adicional para acciones por formato
        if len(symbol_upper) <= 5:
            # Tickers cortos son típicamente acciones, especialmente si son solo letras
            if symbol_upper.isalpha():
                return "stock"
        
        # Último recurso - clasificación por tipo de caracteres y longitud
        if len(symbol_upper) <= 8 and 'USD' in symbol_upper:
            return "forex"  # Probable par FOREX con USD
        elif len(symbol_upper) <= 5 and not any(c.isdigit() for c in symbol_upper):
            return "stock"  # Probable ticker de acción
        elif len(symbol_upper) >= 10 and any(c.isdigit() for c in symbol_upper):
            return "futures"  # Posible contrato de futuros
            
        # Si no podemos determinar, consideramos que es una acción
        # (ya que la mayoría de los errores reportados son en acciones)
        return "stock"

    def check_exposure_limit(self, symbol: str, volume: float, price: float, mt5_connector, symbol_info: dict = None) -> bool:
        """
        Verifica si la exposición total (incluyendo la nueva operación) excede el límite permitido.
        Si la nueva operación excede el límite, intenta reducir el volumen al mínimo permitido antes de rechazar.
        """
        try:
            if symbol_info is None:
                symbol_info = mt5_connector.get_symbol_info(symbol)
            contract_size = symbol_info.get('contract_size', 100000)
            min_volume = symbol_info.get('min_volume', 0.01)
            # Calcular exposición de la nueva operación
            new_exposure = volume * contract_size * price
            # Obtener exposición total actual
            current_exposure = mt5_connector.get_total_exposure()
            # Calcular límite máximo de exposición
            balance = mt5_connector.get_account_info().get('balance', 0)
            # Usar método de instancia para máxima compatibilidad
            if hasattr(self, 'calculate_dynamic_exposure_limit'):
                max_exposure = self.calculate_dynamic_exposure_limit(balance, symbol, self.risk_params)
            else:
                max_exposure = calculate_dynamic_exposure_limit(balance, symbol, self.risk_params)
            # Si la nueva operación excede el límite, intentar con volumen mínimo
            if (current_exposure + new_exposure) > max_exposure:
                min_exposure = min_volume * contract_size * price
                if (current_exposure + min_exposure) > max_exposure:
                    logger.warning(f"❌ Exposición total cercana al límite para {symbol}. Actual: {current_exposure}, Máxima: {max_exposure}")
                    return False
                else:
                    logger.warning(f"⚠️ Exposición excedida con volumen propuesto. Se intentará con volumen mínimo ({min_volume}).")
                    return True  # Permitir que MT5 decida con volumen mínimo
            logger.info(f"✅ Exposición total tras la operación: {current_exposure + new_exposure:.2f} / {max_exposure:.2f}")
            return True
        except Exception as e:
            logger.error(f"Error verificando exposición para {symbol}: {str(e)}")
            return False

def calculate_dynamic_exposure_limit(balance: float, symbol: str, strategy: dict, *args, **kwargs) -> float:
    """
    Calcula el límite dinámico de exposición TOTAL basado en balance, símbolo y estrategia.
    CORREGIDO: Retorna límite de exposición total, no per-trade.

    Args:
        balance: Balance de la cuenta.
        symbol: Símbolo de trading.
        strategy: Diccionario de parámetros de estrategia.
        *args: Argumentos adicionales ignorados para compatibilidad.
        **kwargs: Argumentos adicionales ignorados para compatibilidad.

    Returns:
        Límite dinámico de exposición TOTAL.
    """
    # Compatibilidad: si strategy es str, usar 30% del balance como límite total
    if isinstance(strategy, str):
        logger.error(f"[EXPOSURE LIMIT] strategy recibido como str: {strategy}. Se esperaba dict. Retornando 0.3 * balance.")
        return balance * 0.3
    
    # CORREGIDO: Límite para exposición TOTAL, no per-trade
    # Permitir hasta 30% del balance como exposición total máxima
    max_total_exposure_pct = 0.3  # 30% del balance
    
    # Ajustar según la liquidez del símbolo
    if any(major in symbol for major in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']):
        max_total_exposure_pct = 0.4  # 40% para pares majors
    elif any(metal in symbol for metal in ['XAU', 'XAG', 'GOLD', 'SILVER']):
        max_total_exposure_pct = 0.25  # 25% para metales
    elif any(exotic in symbol for exotic in ['MXN', 'ZAR', 'TRY']):
        max_total_exposure_pct = 0.2   # 20% para exóticos
    
    limit = balance * max_total_exposure_pct
    logger.info(f"[EXPOSURE LIMIT] Para {symbol}: balance={balance}, max_total_pct={max_total_exposure_pct} => limit_total={limit}")
    return limit


    def calculate_margin_buffer(self, volume: float, contract_size: float, price: float, leverage: float = 100.0, symbol: str = None, *args, **kwargs) -> float:
        """
        Calcula el margen requerido con un buffer dinámico basado en la volatilidad del símbolo.
        Admite entre 4 y 6 argumentos posicionales para máxima compatibilidad.

        Args:
            volume: Volumen de la posición.
            contract_size: Tamaño del contrato del símbolo.
            price: Precio actual del símbolo.
            leverage: Apalancamiento del símbolo (opcional, por compatibilidad)
            symbol: Símbolo de trading (opcional, por compatibilidad)
            *args: Argumentos adicionales ignorados para compatibilidad.
            **kwargs: Argumentos adicionales ignorados para compatibilidad.

        Returns:
            Margen requerido con buffer dinámico.
        """
        try:
            # Permitir llamada con 4, 5 o 6 argumentos posicionales
            # Si se llama con más de 4 argumentos, reasignar según orden esperado
            if len(args) >= 1 and symbol is None:
                symbol = args[0]
            if len(args) >= 2:
                # Si se pasa un sexto argumento, lo ignoramos (compatibilidad futura)
                pass
            # Si leverage no es válido, intentar obtenerlo por símbolo
            if (leverage is None or leverage <= 0) and hasattr(self, 'symbol_leverage') and symbol is not None:
                leverage = self.symbol_leverage.get(symbol, 100.0)
            if leverage is None or leverage <= 0:
                leverage = 100.0
            base_margin = (volume * contract_size * price) / leverage
            volatility = self._determine_volatility(symbol) if symbol is not None else 'low'
            buffer_factor = 1.1 if volatility == 'low' else 1.25
            return base_margin * buffer_factor
        except Exception as e:
            logger.error(f"Error calculando margen con buffer para {symbol}: {str(e)}")
            return 0.0

    def _determine_volatility(self, symbol: str) -> str:
        """
        Determina la volatilidad del símbolo basado en parámetros predefinidos.

        Args:
            symbol: Símbolo de trading.

        Returns:
            'low', 'medium', o 'high' dependiendo de la volatilidad.
        """
        if 'XAU' in symbol or 'XAG' in symbol:
            return 'high'
        elif symbol.endswith('JPY'):
            return 'medium'
        else:
            return 'low'
    
    def calculate_leverage(self, symbol: str) -> int:
        """
        Calcula el leverage según el tipo de instrumento.
        """
        category = self._categorize_by_symbol_name(symbol)
        leverage_map = {
            "forex": 500,
            "metal": 100,
            "index": 50,
            "other": 20
        }
        return leverage_map.get(category, 100)  # Default: 100

    def optimize_sl_tp(self, entry_price: float, atr: float) -> Tuple[float, float]:
        """
        Optimiza los niveles de SL y TP basados en ATR y volatilidad.
        """
        sl = entry_price - atr * 1.5
        tp = entry_price + atr * 2.5
        return sl, tp
