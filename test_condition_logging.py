"""
Test script to verify condition check logging
Run this to see the new detailed logging format
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategy import TradingStrategy

def create_test_data(scenario="all_pass"):
    """Create test data for different scenarios"""
    
    # Base data
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1H')
    data = {
        'timestamp': dates,
        'open': np.random.uniform(140, 145, 100),
        'high': np.random.uniform(145, 150, 100),
        'low': np.random.uniform(135, 140, 100),
        'close': np.random.uniform(140, 145, 100),
        'volume': np.random.uniform(10000, 30000, 100)
    }
    
    df = pd.DataFrame(data)
    
    if scenario == "all_pass":
        # Scenario where all conditions pass
        # Strong uptrend: Price > EMA9 > EMA21
        df['close'] = np.linspace(130, 150, 100)  # Uptrend
        df['ema_short'] = df['close'] - 2  # EMA9 slightly below price
        df['ema_long'] = df['ema_short'] - 3  # EMA21 below EMA9
        df['rsi'] = 55  # In valid range (40-70)
        df['adx'] = 30  # Above threshold (25)
        df['atr'] = 2.5
        df['volume_ma'] = 20000
        df.loc[df.index[-1], 'volume'] = 25000  # Current volume above MA
        
    elif scenario == "rsi_fail":
        # RSI out of range
        df['close'] = np.linspace(130, 150, 100)
        df['ema_short'] = df['close'] - 2
        df['ema_long'] = df['ema_short'] - 3
        df['rsi'] = 75  # Too high (above 70)
        df['adx'] = 30
        df['atr'] = 2.5
        df['volume_ma'] = 20000
        df.loc[df.index[-1], 'volume'] = 25000
        
    elif scenario == "ema_fail":
        # EMA alignment fails
        df['close'] = 140
        df['ema_short'] = 142  # Price below EMA9 (wrong)
        df['ema_long'] = 145  # EMA9 below EMA21 (wrong)
        df['rsi'] = 55
        df['adx'] = 30
        df['atr'] = 2.5
        df['volume_ma'] = 20000
        df.loc[df.index[-1], 'volume'] = 25000
        
    elif scenario == "volume_fail":
        # Volume too low
        df['close'] = np.linspace(130, 150, 100)
        df['ema_short'] = df['close'] - 2
        df['ema_long'] = df['ema_short'] - 3
        df['rsi'] = 55
        df['adx'] = 30
        df['atr'] = 2.5
        df['volume_ma'] = 30000
        df.loc[df.index[-1], 'volume'] = 15000  # Below MA
        
    elif scenario == "adx_fail":
        # ADX too low (weak trend)
        df['close'] = np.linspace(130, 150, 100)
        df['ema_short'] = df['close'] - 2
        df['ema_long'] = df['ema_short'] - 3
        df['rsi'] = 55
        df['adx'] = 20  # Below threshold (25)
        df['atr'] = 2.5
        df['volume_ma'] = 20000
        df.loc[df.index[-1], 'volume'] = 25000
    
    return df


def test_logging():
    """Test the condition logging with different scenarios"""
    
    config = {
        'ema_short': 9,
        'ema_long': 21,
        'rsi_length': 14,
        'rsi_min': 40,
        'rsi_max': 70,
        'adx_period': 14,
        'adx_threshold': 25,
        'atr_period': 14,
        'use_volume_filter': True,
        'volume_ma_period': 20,
        'max_usdt_per_trade': 100,
        'sl_atr_multiplier': 1.5,
        'tp1_rr': 1.0,
        'tp2_rr': 2.0,
        'entry_1_percent': 30,
        'entry_2_percent': 70
    }
    
    strategy = TradingStrategy(config)
    
    scenarios = [
        ("All Conditions Pass", "all_pass"),
        ("RSI Out of Range", "rsi_fail"),
        ("EMA Alignment Failed", "ema_fail"),
        ("Volume Too Low", "volume_fail"),
        ("ADX Too Weak", "adx_fail")
    ]
    
    print("\n" + "="*80)
    print("TESTING CONDITION CHECK LOGGING")
    print("="*80 + "\n")
    
    for scenario_name, scenario_key in scenarios:
        print(f"\n{'*'*80}")
        print(f"TEST SCENARIO: {scenario_name}")
        print(f"{'*'*80}\n")
        
        df = create_test_data(scenario_key)
        signal, details = strategy.check_long_entry(df)
        
        print(f"\nResult: {'✅ SIGNAL TRIGGERED' if signal else '❌ NO SIGNAL'}")
        print(f"{'*'*80}\n")
        
        # Small delay for readability
        import time
        time.sleep(1)


if __name__ == "__main__":
    test_logging()
