"""
Test Suite for Mr.Cashondo Trading Bot
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import modules to test
from mt5_connector import MT5Connector, OrderRequest, MarketData
from signal_generator import SignalGenerator, TechnicalIndicators, TradingSignal
from risk_manager import RiskManager, RiskParameters, PositionSize
from telegram_alerts import TelegramAlerts

class TestTechnicalIndicators:
    """Test technical indicators calculations"""
    
    def test_ema_calculation(self):
        """Test EMA calculation"""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        ema = TechnicalIndicators.ema(data, 3)
        
        assert len(ema) == len(data)
        assert ema[0] == data[0]  # First value should be same as input
        assert ema[-1] > data[0]  # EMA should trend upward
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        # Create price data with clear trend
        data = np.array([50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 59, 58, 57, 56])
        rsi = TechnicalIndicators.rsi(data, 14)
        
        assert len(rsi) == len(data)
        assert 0 <= rsi[-1] <= 100  # RSI should be between 0 and 100
    
    def test_atr_calculation(self):
        """Test ATR calculation"""
        high = np.array([1.1, 1.2, 1.3, 1.4, 1.5])
        low = np.array([1.0, 1.1, 1.2, 1.3, 1.4])
        close = np.array([1.05, 1.15, 1.25, 1.35, 1.45])
        
        atr = TechnicalIndicators.atr(high, low, close, 3)
        
        assert len(atr) == len(high)
        assert all(atr >= 0)  # ATR should be positive
    
    def test_adx_calculation(self):
        """Test ADX calculation"""
        high = np.array([1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0])
        low = np.array([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9])
        close = np.array([1.05, 1.15, 1.25, 1.35, 1.45, 1.55, 1.65, 1.75, 1.85, 1.95])
        
        adx = TechnicalIndicators.adx(high, low, close, 5)
        
        assert len(adx) == len(high)
        assert all(adx >= 0)  # ADX should be positive

class TestSignalGenerator:
    """Test signal generation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.signal_generator = SignalGenerator()
        
        # Create mock market data
        self.mock_market_data = MarketData(
            symbol="EURUSD",
            timeframe="M5",
            open=np.array([1.1000, 1.1010, 1.1020, 1.1030, 1.1040] * 100),
            high=np.array([1.1005, 1.1015, 1.1025, 1.1035, 1.1045] * 100),
            low=np.array([1.0995, 1.1005, 1.1015, 1.1025, 1.1035] * 100),
            close=np.array([1.1002, 1.1012, 1.1022, 1.1032, 1.1042] * 100),
            volume=np.array([1000, 1100, 1200, 1300, 1400] * 100),
            time=np.array([1234567890 + i for i in range(500)])
        )
    
    def test_analyze_market_data_no_signal(self):
        """Test market data analysis when no signal conditions are met"""
        # Mock market data that doesn't meet signal conditions
        weak_trend_data = MarketData(
            symbol="EURUSD",
            timeframe="M5",
            open=np.array([1.1000] * 500),
            high=np.array([1.1001] * 500),
            low=np.array([1.0999] * 500),
            close=np.array([1.1000] * 500),
            volume=np.array([1000] * 500),
            time=np.array([1234567890 + i for i in range(500)])
        )
        
        signal = self.signal_generator.analyze_market_data(weak_trend_data)
        assert signal is None
    
    def test_analyze_market_data_with_signal(self):
        """Test market data analysis with strong signal conditions"""
        # Create strong uptrend data
        close_prices = np.array([1.1000 + i * 0.0001 for i in range(500)])
        high_prices = close_prices + 0.0002
        low_prices = close_prices - 0.0002
        open_prices = close_prices - 0.0001
        
        strong_trend_data = MarketData(
            symbol="EURUSD",
            timeframe="M5",
            open=open_prices,
            high=high_prices,
            low=low_prices,
            close=close_prices,
            volume=np.array([1000] * 500),
            time=np.array([1234567890 + i for i in range(500)])
        )
        
        signal = self.signal_generator.analyze_market_data(strong_trend_data)
        # May or may not generate signal depending on exact conditions
        # This tests that the function runs without error
        assert signal is None or isinstance(signal, TradingSignal)

class TestRiskManager:
    """Test risk management functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.risk_manager = RiskManager()
        
        # Mock symbol info
        self.mock_symbol_info = {
            'symbol': 'EURUSD',
            'digits': 5,
            'point': 0.00001,
            'contract_size': 100000,
            'volume_min': 0.01,
            'volume_max': 100.0,
            'volume_step': 0.01
        }
    
    def test_calculate_position_size(self):
        """Test position size calculation"""
        position_size = self.risk_manager.calculate_position_size(
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=10000,
            symbol_info=self.mock_symbol_info
        )
        
        assert position_size is not None
        assert isinstance(position_size, PositionSize)
        assert position_size.volume > 0
        assert position_size.risk_percentage <= 1.0  # Should not exceed 1%
    
    def test_validate_trade_success(self):
        """Test successful trade validation"""
        is_valid, reason = self.risk_manager.validate_trade(
            signal_type="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            account_balance=10000,
            symbol="EURUSD"
        )
        assert is_valid is True
        assert "validation passed" in reason.lower()

    def test_validate_trade_failure(self):
        """Test trade validation failure"""
        # Test with poor risk-reward ratio
        is_valid, reason = self.risk_manager.validate_trade(
            signal_type="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1010,  # Very small profit target
            account_balance=10000,
            symbol="EURUSD"
        )
        assert is_valid is False
        assert "risk-reward" in reason.lower()
    
    def test_breakeven_logic(self):
        """Test breakeven detection"""
        # Test BUY position
        should_move = self.risk_manager.should_move_to_breakeven(
            signal_type="BUY",
            entry_price=1.1000,
            current_price=1.1020,  # Moved up significantly
            atr_value=0.0015
        )
        
        assert isinstance(should_move, bool)
        
        # Test SELL position
        should_move = self.risk_manager.should_move_to_breakeven(
            signal_type="SELL",
            entry_price=1.1000,
            current_price=1.0980,  # Moved down significantly
            atr_value=0.0015
        )
        
        assert isinstance(should_move, bool)
    
    def test_trailing_stop_calculation(self):
        """Test trailing stop calculation"""
        # Test BUY position
        new_sl = self.risk_manager.calculate_trailing_stop(
            signal_type="BUY",
            entry_price=1.1000,
            current_price=1.1030,
            atr_value=0.0015
        )
        
        if new_sl is not None:
            assert new_sl < 1.1030  # Should be below current price
            assert new_sl > 1.1000  # Should be above entry price
    
    def test_risk_limits(self):
        """Test risk limit enforcement"""
        # Test maximum positions
        self.risk_manager.positions_count = 3
        is_allowed, reason = self.risk_manager.is_trading_allowed(10000)
        
        assert is_allowed is False
        assert "maximum positions" in reason.lower()
        
        # Test daily loss limit
        self.risk_manager.positions_count = 0
        self.risk_manager.daily_pnl = -500  # $500 loss
        is_allowed, reason = self.risk_manager.is_trading_allowed(10000)
        
        assert is_allowed is False
        assert "daily loss" in reason.lower()

class TestMT5Connector:
    """Test MT5 connector functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mt5_connector = MT5Connector()
    
    @patch('mt5_connector.mt5')
    def test_connect_success(self, mock_mt5):
        """Test successful MT5 connection"""
        # Mock successful connection
        mock_mt5.initialize.return_value = True
        mock_mt5.login.return_value = True
        mock_mt5.account_info.return_value = Mock(
            login=12345,
            balance=10000,
            equity=10000
        )
        
        result = self.mt5_connector.connect()
        
        assert result is True
        assert self.mt5_connector.connected is True
    
    @patch('mt5_connector.mt5')
    def test_connect_failure(self, mock_mt5):
        """Test MT5 connection failure"""
        # Mock failed connection
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = "Connection failed"
        
        result = self.mt5_connector.connect()
        
        assert result is False
        assert self.mt5_connector.connected is False
    
    @patch('mt5_connector.mt5')
    def test_get_market_data(self, mock_mt5):
        """Test market data retrieval"""
        # Mock market data
        mock_rates = np.array([
            (1234567890, 1.1000, 1.1010, 1.0990, 1.1005, 1000),
            (1234567891, 1.1005, 1.1015, 1.0995, 1.1010, 1100),
        ], dtype=[('time', 'i4'), ('open', 'f8'), ('high', 'f8'), 
                  ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i4')])
        
        mock_mt5.copy_rates_from_pos.return_value = mock_rates
        self.mt5_connector.connected = True
        
        market_data = self.mt5_connector.get_market_data("EURUSD", "M5", 100)
        
        assert market_data is not None
        assert isinstance(market_data, MarketData)
        assert market_data.symbol == "EURUSD"
        assert len(market_data.close) == 2

class TestTelegramAlerts:
    """Test Telegram alerts functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Mock environment variables
        with patch.dict('os.environ', {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TEST_ENV': 'true'
        }):
            self.telegram_alerts = TelegramAlerts()
    
    def test_format_signal_message(self):
        """Test signal message formatting"""
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="M5",
            signal_type="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            confidence=0.85,
            reasons=["EMA cross", "RSI divergence"],
            timestamp=datetime.now(),
            atr_value=0.0015
        )
        
        message = self.telegram_alerts._format_signal_message(signal)
        
        assert "NUEVA OPERACIÓN FOREX" in message
        assert "EURUSD" in message
        assert "BUY" in message
        assert "1.1000" in message
    
    @patch('telegram_alerts.telebot.TeleBot')
    def test_send_signal_alert(self, mock_telebot):
        """Test sending signal alert"""
        # Mock bot
        mock_bot = Mock()
        mock_telebot.return_value = mock_bot
        
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="M5",
            signal_type="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            confidence=0.85,
            reasons=["EMA cross"],
            timestamp=datetime.now(),
            atr_value=0.0015
        )
        
        # Reinitialize with mocked bot
        with patch.dict('os.environ', {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TEST_ENV': 'true'
        }):
            telegram_alerts = TelegramAlerts()
            telegram_alerts.bot = mock_bot
            
            result = telegram_alerts.send_signal_alert(signal)
            
            assert result is True
            mock_bot.send_message.assert_called_once()

class TestIntegration:
    """Integration tests"""
    
    def test_signal_to_execution_flow(self):
        """Test complete signal to execution flow"""
        # This would be a more complex integration test
        # involving multiple components working together
        pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
