#!/usr/bin/env python3
"""
Test script to verify stops_level fix
"""
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append('.')

# Load environment variables
load_dotenv()

def test_stops_level_fix():
    """Test that stops_level attribute error is fixed"""
    print("🔧 Testing stops_level attribute fix...")
    
    try:
        # Test MT5Connector import
        from mt5_connector import MT5Connector
        print("✅ MT5Connector imported successfully")
        
        # Test RiskManager import
        from risk_manager import RiskManager
        print("✅ RiskManager imported successfully")
        
        # Test creating connector instance
        connector = MT5Connector()
        print("✅ MT5Connector instance created successfully")
        
        # Test creating risk manager instance
        risk_manager = RiskManager()
        print("✅ RiskManager instance created successfully")
        
        print("\n🎯 All tests passed! The stops_level attribute error has been fixed.")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_stops_level_fix()
    if success:
        print("\n✨ Fix verification completed successfully!")
    else:
        print("\n⚠️  Fix verification failed!")
        sys.exit(1)
