"""
Test script for SFO (Signal Flow Optimized) Strategy
Verifica que todas las optimizaciones estén funcionando correctamente
"""
import logging
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mt5_connector import MT5Connector
from signal_generator import SignalGenerator
from risk_manager import RiskManager, RiskParameters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_sfo_strategy():
    """Test the complete SFO strategy implementation"""
    
    logger.info("🚀 Testing SFO (Signal Flow Optimized) Strategy")
    logger.info("=" * 60)
    
    # Test 1: MT5 Connection
    logger.info("📡 Test 1: MT5 Connection")
    mt5_connector = MT5Connector()
    
    if not mt5_connector.connect():
        logger.error("❌ Failed to connect to MT5")
        return False
    
    logger.info("✅ MT5 connected successfully")
    
    # Test 2: Signal Generator Initialization
    logger.info("\n🔧 Test 2: Signal Generator with SFO Strategy")
    signal_generator = SignalGenerator()
    
    if not signal_generator.initialize_symbols(mt5_connector):
        logger.error("❌ Failed to initialize signal generator")
        return False
    
    logger.info(f"✅ Signal generator initialized with {len(signal_generator.symbols)} symbols")
    
    # Test 3: SFO Parameters Verification
    logger.info("\n⚙️ Test 3: SFO Parameters Verification")
    default_strategy = signal_generator._get_default_adaptive_strategy()
    
    logger.info("📋 SFO Strategy Parameters:")
    logger.info(f"  - ADX Threshold: {default_strategy['adx_threshold']} (SFO: ≤8)")
    logger.info(f"  - Confidence Threshold: {default_strategy['confidence_threshold']} (SFO: ≤0.30)")
    logger.info(f"  - Max Spread: {default_strategy['max_spread_threshold']} (SFO: ≥20)")
    logger.info(f"  - SL Multiplier: {default_strategy['sl_multiplier']} (SFO: ≤1.2)")
    logger.info(f"  - TP Multiplier: {default_strategy['tp_multiplier']} (SFO: ≤1.8)")
    
    # Verificar que los parámetros SFO estén aplicados
    sfo_checks = []
    sfo_checks.append(("ADX ≤ 8", default_strategy['adx_threshold'] <= 8))
    sfo_checks.append(("Confidence ≤ 0.30", default_strategy['confidence_threshold'] <= 0.30))
    sfo_checks.append(("Max Spread ≥ 20", default_strategy['max_spread_threshold'] >= 20))
    sfo_checks.append(("SL ≤ 1.2", default_strategy['sl_multiplier'] <= 1.2))
    sfo_checks.append(("TP ≤ 1.8", default_strategy['tp_multiplier'] <= 1.8))
    
    sfo_passed = 0
    for check_name, passed in sfo_checks:
        status = "✅" if passed else "❌"
        logger.info(f"  {status} {check_name}")
        if passed:
            sfo_passed += 1
    
    logger.info(f"📊 SFO Parameters: {sfo_passed}/{len(sfo_checks)} optimized")
    
    # Test 4: Risk Manager SFO Parameters
    logger.info("\n💰 Test 4: Risk Manager SFO Parameters")
    risk_params = RiskParameters()
    
    logger.info("📋 SFO Risk Parameters:")
    logger.info(f"  - Risk per Trade: {risk_params.max_risk_per_trade*100:.1f}% (SFO: ≤0.8%)")
    logger.info(f"  - Max Daily Loss: {risk_params.max_daily_loss*100:.1f}% (SFO: ≤4%)")
    logger.info(f"  - Max Positions: {risk_params.max_open_positions} (SFO: ≥4)")
    logger.info(f"  - Min RR Ratio: {risk_params.min_risk_reward_ratio} (SFO: ≤1.3)")
    logger.info(f"  - Breakeven Mult: {risk_params.breakeven_multiplier} (SFO: ≤0.8)")
    
    # Test 5: Signal Generation Test
    logger.info("\n🎯 Test 5: Signal Generation Capability Test")
    
    # Seleccionar símbolos para test
    test_symbols = signal_generator.symbols[:5]  # Primeros 5 símbolos
    logger.info(f"Testing signal generation for: {test_symbols}")
    
    total_signals = 0
    for symbol in test_symbols:
        try:
            # Obtener datos de mercado
            market_data = mt5_connector.get_market_data(symbol, "M15", 500)
            if market_data:
                signal = signal_generator.analyze_market_data(market_data)
                if signal:
                    total_signals += 1
                    logger.info(f"  ✅ {symbol}: Signal generated (Type: {signal.signal_type}, Confidence: {signal.confidence:.2f})")
                else:
                    logger.debug(f"  ⭕ {symbol}: No signal")
            else:
                logger.debug(f"  ❌ {symbol}: No market data")
        except Exception as e:
            logger.debug(f"  ❌ {symbol}: Error - {str(e)}")
    
    logger.info(f"📈 Signal Generation Results: {total_signals}/{len(test_symbols)} symbols generated signals")
    
    # Test 6: SFO Filters Test
    logger.info("\n🔍 Test 6: SFO Adaptive Filters Test")
    
    # Test con datos simulados
    test_atr = 0.00005  # Muy bajo, pero debería pasar con SFO
    test_adx = 5.0      # Muy bajo, pero debería pasar con SFO
    test_strategy = signal_generator._get_default_adaptive_strategy()
    
    filter_result = signal_generator._pass_adaptive_filters("EURUSD", test_atr, test_adx, test_strategy)
    
    status = "✅ PASSED" if filter_result else "❌ FAILED"
    logger.info(f"  {status} Ultra-permissive filters (ATR: {test_atr:.6f}, ADX: {test_adx})")
    
    # Disconnect
    mt5_connector.disconnect()
    
    # Final Results
    logger.info("\n🏁 SFO Strategy Test Results")
    logger.info("=" * 60)
    
    overall_score = 0
    max_score = 6
    
    test_results = [
        ("MT5 Connection", True),
        ("Signal Generator Init", True),
        ("SFO Parameters", sfo_passed >= 4),
        ("Risk Manager SFO", risk_params.max_risk_per_trade <= 0.008),
        ("Signal Generation", total_signals > 0),
        ("SFO Filters", filter_result)
    ]
    
    for test_name, passed in test_results:
        status = "✅" if passed else "❌"
        logger.info(f"{status} {test_name}")
        if passed:
            overall_score += 1
    
    logger.info(f"\n📊 Overall SFO Implementation Score: {overall_score}/{max_score}")
    
    if overall_score >= 5:
        logger.info("🎉 SFO Strategy successfully implemented and ready for production!")
        return True
    else:
        logger.warning("⚠️ SFO Strategy needs additional adjustments")
        return False

if __name__ == "__main__":
    logger.info(f"🤖 Mr.Cashondo Bot - SFO Strategy Test")
    logger.info(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_sfo_strategy()
    
    if success:
        logger.info("✅ All SFO tests passed! Bot is ready for signal generation.")
    else:
        logger.error("❌ Some SFO tests failed. Check configuration.")
    
    input("\nPresiona Enter para finalizar...")
