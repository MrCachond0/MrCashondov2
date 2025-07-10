"""
Test script for Mr. Cashondo Bot - Dynamic Parameters
Tests dynamic symbol and parameter retrieval functionality
"""
import logging
import os
from dotenv import load_dotenv
from mt5_connector import MT5Connector
from signal_generator import SignalGenerator
from risk_manager import RiskManager, RiskParameters

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dynamic_functionality():
    """Test the dynamic parameter functionality"""
    
    # Initialize MT5 connector
    mt5_connector = MT5Connector()
    
    # Try to connect
    if not mt5_connector.connect():
        logger.error("Failed to connect to MT5 - Demo/Live trading account required")
        return False
    
    logger.info("[SUCCESS] Successfully connected to MT5")
    
    # Test dynamic symbol retrieval
    logger.info("\n=== Testing Dynamic Symbol Retrieval ===")
    
    # Get available symbols
    forex_symbols = mt5_connector.get_available_symbols("forex")
    logger.info(f"Found {len(forex_symbols)} FOREX symbols: {forex_symbols[:5]}...")
    
    metals_symbols = mt5_connector.get_available_symbols("metals") 
    logger.info(f"Found {len(metals_symbols)} Metals symbols: {metals_symbols}")
    
    # Test dynamic symbol information
    if forex_symbols:
        test_symbol = forex_symbols[0]
        logger.info(f"\n=== Testing Symbol Info for {test_symbol} ===")
        
        # Get symbol info
        symbol_info = mt5_connector.get_symbol_info(test_symbol)
        if symbol_info:
            logger.info(f"[SUCCESS] Symbol info retrieved: {len(symbol_info)} parameters")
            logger.info(f"  - Digits: {symbol_info.get('digits', 'N/A')}")
            logger.info(f"  - Point: {symbol_info.get('point', 'N/A')}")
            logger.info(f"  - Spread: {symbol_info.get('spread', 'N/A')}")
            logger.info(f"  - Min Volume: {symbol_info.get('min_volume', 'N/A')}")
            logger.info(f"  - Max Volume: {symbol_info.get('max_volume', 'N/A')}")
            logger.info(f"  - Contract Size: {symbol_info.get('contract_size', 'N/A')}")
            # filling_mode eliminado: la lógica de filling_mode se gestiona internamente en mt5_connector
        else:
            logger.error(f"[ERROR] Failed to get symbol info for {test_symbol}")
        
        # Get trading parameters
        trading_params = mt5_connector.get_dynamic_trading_params(test_symbol)
        if trading_params:
            logger.info(f"[SUCCESS] Trading params retrieved: {len(trading_params)} parameters")
            logger.info(f"  - Current Bid: {trading_params.get('current_bid', 'N/A')}")
            logger.info(f"  - Current Ask: {trading_params.get('current_ask', 'N/A')}")
            logger.info(f"  - Current Spread: {trading_params.get('current_spread', 'N/A')}")
            logger.info(f"  - Min Stop Distance: {trading_params.get('min_stop_distance', 'N/A')}")
        else:
            logger.error(f"[ERROR] Failed to get trading params for {test_symbol}")
    
    # Test signal generator with dynamic symbols
    logger.info("\n=== Testing Signal Generator with Dynamic Symbols ===")
    
    signal_generator = SignalGenerator()
    
    # Initialize symbols dynamically
    if signal_generator.initialize_symbols(mt5_connector):
        logger.info(f"[SUCCESS] Signal generator initialized with {len(signal_generator.symbols)} symbols")
        logger.info(f"  - Active symbols: {', '.join(signal_generator.symbols)}")
        
        # Test symbol specifications
        for symbol in signal_generator.symbols[:2]:  # Test first 2 symbols
            specs = signal_generator.symbol_specs.get(symbol, {})
            if specs:
                logger.info(f"  - {symbol}: Min ATR threshold = {signal_generator.get_symbol_atr_threshold(symbol):.6f}")
                multipliers = signal_generator.get_symbol_multipliers(symbol)
                logger.info(f"  - {symbol}: SL/TP multipliers = {multipliers['sl_multiplier']:.1f}/{multipliers['tp_multiplier']:.1f}")
    else:
        logger.error("[ERROR] Failed to initialize signal generator with dynamic symbols")
    
    # Test risk manager with dynamic parameters
    logger.info("\n=== Testing Risk Manager with Dynamic Parameters ===")
    
    risk_params = RiskParameters(
        max_risk_per_trade=0.01,
        max_daily_loss=0.05,
        max_open_positions=3,
        min_risk_reward_ratio=1.5
    )
    risk_manager = RiskManager(risk_params)
    
    # Test position size calculation
    if forex_symbols:
        test_symbol = forex_symbols[0]
        test_entry = 1.10000
        test_sl = 1.09500
        test_balance = 10000.0
        
        position_size = risk_manager.calculate_position_size_dynamic(
            test_symbol, test_entry, test_sl, test_balance, mt5_connector
        )
        
        if position_size:
            logger.info(f"[SUCCESS] Dynamic position size calculated for {test_symbol}:")
            logger.info(f"  - Volume: {position_size.volume:.2f}")
            logger.info(f"  - Risk Amount: ${position_size.risk_amount:.2f}")
            logger.info(f"  - Risk Percentage: {position_size.risk_percentage:.2f}%")
            logger.info(f"  - Stop Loss Pips: {position_size.stop_loss_pips:.1f}")
        else:
            logger.error(f"[ERROR] Failed to calculate position size for {test_symbol}")
    
    # Disconnect
    mt5_connector.disconnect()
    logger.info("\n[SUCCESS] Test completed successfully!")
    return True

if __name__ == "__main__":
    logger.info("=== Mr. Cashondo Bot - Dynamic Parameters Test ===")
    test_dynamic_functionality()
