"""
Trading Strategy Implementation
MA Method 2: Trend Following + Momentum Confluence
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from indicators import Indicators
import logging
from datetime import datetime


class TradingStrategy:
    """
    MA Method 2 Trading Strategy
    
    ⚠️ SPOT TRADING - LONG ONLY (BUY & SELL)
    Bot ini BUKAN futures trading, hanya bisa BUY (long) dan SELL (exit)
    Tidak ada SHORT SELLING atau LEVERAGE
    
    Entry Criteria (LONG ONLY):
    1. Price > EMA_short and EMA_short > EMA_long
    2. RSI between min_rsi and max_rsi (e.g., 40-70)
    3. ADX >= threshold (e.g., 25)
    4. Volume >= Volume MA (optional)
    
    Exit Criteria:
    - Take Profit 1 (TP1): 1R (30% position)
    - Take Profit 2 (TP2): 2R (40% position)
    - Trailing Stop: 1.0x ATR (30% position)
    - Stop Loss: 1.5x ATR
    """
    
    def __init__(self, config: Dict):
        """
        Initialize strategy with configuration
        
        Args:
            config: Strategy configuration dict
        """
        # Simpan config yang diterima
        self.config = config  # Pastikan config ada
        
        # Setup logger for condition checks
        self.logger = logging.getLogger('strategy')
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            
            # Console handler with colors for terminal
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(message)s'  # Simple format for console
            )
            console_handler.setFormatter(console_formatter)
            
            # File handler for detailed logs
            from pathlib import Path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"strategy_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
        
        # EMA settings
        self.ema_short = config.get('ema_short', 9)
        self.ema_long = config.get('ema_long', 21)
        
        # RSI settings
        self.rsi_length = config.get('rsi_length', 14)
        self.rsi_min = config.get('rsi_min', 40)
        self.rsi_max = config.get('rsi_max', 70)

        # ADX periodgs
        self.adx_period = config.get('adx_period', 14)

        # ADX threshold
        self.adx_threshold = config.get('adx_threshold', 25)
        
        # ATR settings
        self.atr_period = config.get('atr_period', 14)
        
        # Volume filter
        self.use_volume_filter = config.get('use_volume_filter', True)
        self.volume_ma_period = config.get('volume_ma_period', 20)
        
        # Lookback for crossover detection
        self.crossover_lookback = config.get('crossover_lookback', 2)

        # Risk management settings
        self.max_usdt_per_trade = config.get('max_usdt_per_trade', 0)
        self.sl_atr_multiplier = config.get('sl_atr_multiplier', 1.5)
        self.tp1_rr = config.get('tp1_rr', 1.0)
        self.tp2_rr = config.get('tp2_rr', 2.0)
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with indicators
        """
        return Indicators.calculate_all_indicators(
            df,
            ema_short=self.ema_short,
            ema_long=self.ema_long,
            rsi_period=self.rsi_length,
            atr_period=self.atr_period,
            adx_period=self.adx_period,
            volume_ma_period=self.volume_ma_period
        )
    
    def check_long_entry(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Check if long entry conditions are met
        
        Args:
            df: DataFrame with indicators
            
        Returns:
            Tuple of (entry_signal, details_dict)
        """
        if len(df) < max(self.ema_long, self.rsi_length, self.atr_period, self.volume_ma_period):
            return False, {"reason": "Insufficient data"}
        
        latest = df.iloc[-1]
        details = {
            "price": latest['close'],
            "ema_short": latest['ema_short'],
            "ema_long": latest['ema_long'],
            "rsi": latest['rsi'],
            "adx": latest['adx'],
            "atr": latest['atr'],
            "volume": latest.get('volume', 0),
            "volume_ma": latest.get('volume_ma', 0)
        }
        
        # Condition 1: EMA alignment (Price > EMA_short > EMA_long)
        ema_condition = (
            latest['close'] > latest['ema_short'] and
            latest['ema_short'] > latest['ema_long']
        )
        details['ema_aligned'] = ema_condition
        
        # Condition 2: RSI in range
        rsi_condition = self.rsi_min <= latest['rsi'] <= self.rsi_max
        details['rsi_valid'] = rsi_condition
        
        # Condition 3: ADX above threshold
        adx_condition = latest['adx'] >= self.adx_threshold
        details['adx_valid'] = adx_condition
        
        # Condition 4: Volume filter (optional)
        volume_condition = True
        volume_ratio = 0.0
        if self.use_volume_filter and 'volume' in df.columns:
            volume_ma = latest.get('volume_ma', 1)
            volume_ratio = latest.get('volume', 0) / volume_ma if volume_ma > 0 else 0
            volume_condition = latest.get('volume', 0) >= volume_ma
        details['volume_valid'] = volume_condition
        details['volume_ratio'] = volume_ratio
        
        # Log detailed condition checks
        # Condition 1: EMA Trend Alignment
        price_above_short = latest['close'] > latest['ema_short']
        short_above_long = latest['ema_short'] > latest['ema_long']
        self.logger.info(
            f"{'✓' if ema_condition else '✗'} Condition 1: EMA Trend - "
            f"Price>{self.ema_short}EMA: {price_above_short}, "
            f"{self.ema_short}EMA>{self.ema_long}EMA: {short_above_long} "
            f"(Price: {latest['close']:.4f}, EMA{self.ema_short}: {latest['ema_short']:.4f}, "
            f"EMA{self.ema_long}: {latest['ema_long']:.4f})"
        )
        
        # Condition 2: RSI Range
        self.logger.info(
            f"{'✓' if rsi_condition else '✗'} Condition 2: RSI in range - "
            f"RSI: {latest['rsi']:.2f} (Target: {self.rsi_min}-{self.rsi_max})"
        )
        
        # Condition 3: ADX Strength
        self.logger.info(
            f"{'✓' if adx_condition else '✗'} Condition 3: ADX strength - "
            f"ADX: {latest['adx']:.2f} (Threshold: >={self.adx_threshold})"
        )
        
        # Condition 4: Volume
        if self.use_volume_filter:
            self.logger.info(
                f"{'✓' if volume_condition else '✗'} Condition 4: Volume - "
                f"{latest.get('volume', 0):.2f} vs MA: {latest.get('volume_ma', 0):.2f} "
                f"(Ratio: {volume_ratio:.2f}x)"
            )
        else:
            self.logger.info(
                f"⊘ Condition 4: Volume filter disabled"
            )
        
        # Market State Summary
        self.logger.info(
            f"Market State - Price: {latest['close']:.4f}, "
            f"RSI: {latest['rsi']:.2f}, ADX: {latest['adx']:.2f}, "
            f"EMA{self.ema_short}: {latest['ema_short']:.4f}, "
            f"EMA{self.ema_long}: {latest['ema_long']:.4f}, "
            f"Volume: {volume_ratio:.2f}x" if self.use_volume_filter else 
            f"Market State - Price: {latest['close']:.4f}, "
            f"RSI: {latest['rsi']:.2f}, ADX: {latest['adx']:.2f}, "
            f"EMA{self.ema_short}: {latest['ema_short']:.4f}, "
            f"EMA{self.ema_long}: {latest['ema_long']:.4f}"
        )
        
        # ⚠️ ALL CONDITIONS MUST BE MET (AND logic)
        # Signal = YES hanya jika EMA ✓ AND RSI ✓ AND ADX ✓ AND Volume ✓
        # Jika salah satu ✗, maka Signal = NO (tidak akan place order)
        entry_signal = ema_condition and rsi_condition and adx_condition and volume_condition
        
        # Final signal status
        self.logger.info(
            # f"{'=' * 60}\n"
            f"{'🟢 ENTRY SIGNAL: YES - All conditions met!' if entry_signal else '🔴 ENTRY SIGNAL: NO - One or more conditions failed'}\n"
            # f"{'=' * 60}"
        )
        
        details['signal'] = entry_signal

        # If entry signal is True, calculate entry positions
        if entry_signal:
            # Validate MAX_USDT_PER_TRADE is set
            if self.max_usdt_per_trade <= 0:
                details['reason'] = "MAX_USDT_PER_TRADE must be > 0 in .env file"
                return False, details
            
            max_position_size = self.max_usdt_per_trade / latest['close']  # Convert USDT to position size
            
            # Get percentage from config
            entry_1_percent = self.config.get('entry_1_percent', 30) / 100  # Convert to decimal
            entry_2_percent = self.config.get('entry_2_percent', 70) / 100
            
            # Calculate entry prices for scale-in strategy
            # Entry based on EMA support levels, NOT current price
            current_price = latest['close']
            atr = latest['atr']
            ema_short = latest['ema_short']
            ema_long = latest['ema_long']
            
            # Entry 1: At EMA Short (first support level for pullback entry)
            # This is the primary entry point when price retraces to EMA short
            entry_1_price = ema_short
            
            # Entry 2: At EMA Long (deeper support level for scale-in)
            # This provides better average price if pullback continues
            entry_2_price = ema_long
            
            # Calculate stop loss below EMA Long (below both entry points)
            # Use sl_atr_multiplier from config
            stop_loss = ema_long - (atr * self.sl_atr_multiplier)
            
            # First entry (at EMA Short - first support)
            risk_1 = entry_1_price - stop_loss
            details['entry_1'] = {
                "price": entry_1_price,
                "position_size": max_position_size * entry_1_percent,
                "stop_loss": stop_loss,
                "take_profit": entry_1_price + (risk_1 * self.tp1_rr),  # Use tp1_rr from config
                "risk_reward": self.tp1_rr
            }

            # Second entry (at EMA Long - deeper support for scale-in)
            risk_2 = entry_2_price - stop_loss
            details['entry_2'] = {
                "price": entry_2_price,
                "position_size": max_position_size * entry_2_percent,
                "stop_loss": stop_loss,
                "take_profit": entry_2_price + (risk_2 * self.tp2_rr),  # Use tp2_rr from config
                "risk_reward": self.tp2_rr
            }

            details['reason'] = "All entry conditions met"
        else:
            # If entry_signal is False, show message and don't calculate entries
            details['entry_1'] = {"price": 0, "position_size": 0, "stop_loss": 0, "take_profit": 0, "risk_reward": 0}
            details['entry_2'] = {"price": 0, "position_size": 0, "stop_loss": 0, "take_profit": 0, "risk_reward": 0}
            details['reason'] = f"Trade analysis not available: Failed: EMA alignment, RSI ({latest['rsi']}), Volume"
        
        return entry_signal, details


    
    def check_short_entry(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Check if short entry conditions are met (inverse of long)
        
        Args:
            df: DataFrame with indicators
            
        Returns:
            Tuple of (entry_signal, details_dict)
        """
        if len(df) < max(self.ema_long, self.rsi_length, self.atr_period, self.volume_ma_period):
            return False, {"reason": "Insufficient data"}
        
        latest = df.iloc[-1]
        details = {
            "price": latest['close'],
            "ema_short": latest['ema_short'],
            "ema_long": latest['ema_long'],
            "rsi": latest['rsi'],
            "adx": latest['adx'],
            "atr": latest['atr']
        }
        
        # Condition 1: EMA alignment (Price < EMA_short < EMA_long)
        ema_condition = (
            latest['close'] < latest['ema_short'] and
            latest['ema_short'] < latest['ema_long']
        )
        details['ema_aligned'] = ema_condition
        
        # Condition 2: RSI in range (for short, use inverted range)
        rsi_min_short = 100 - self.rsi_max # e.g., if max=70, min_short=30
        rsi_max_short = 100 - self.rsi_min # e.g., if min=40, max_short=60
        rsi_condition = rsi_min_short <= latest['rsi'] <= rsi_max_short
        details['rsi_valid'] = rsi_condition
        
        # Condition 3: ADX above threshold
        adx_condition = latest['adx'] >= self.adx_threshold
        details['adx_valid'] = adx_condition
        
        # Condition 4: Volume filter (optional)
        volume_condition = True
        if self.use_volume_filter and 'volume' in df.columns:
            volume_condition = latest.get('volume', 0) >= latest.get('volume_ma', 0)
        details['volume_valid'] = volume_condition
        
        # All conditions must be met
        entry_signal = ema_condition and rsi_condition and adx_condition and volume_condition
        
        details['entry_signal'] = entry_signal
        details['reason'] = "All entry conditions met" if entry_signal else "Conditions not met"
        
        return entry_signal, details
    
    def check_exit_by_ema(self, df: pd.DataFrame, position_side: str) -> Tuple[bool, str]:
        """
        Check if exit condition by EMA crossover is met
        
        Args:
            df: DataFrame with indicators
            position_side: "long" or "short"
            
        Returns:
            Tuple of (should_exit, reason)
        """
        if len(df) < 2:
            return False, ""
        
        latest = df.iloc[-1]
        
        if position_side == "long":
            # Exit long if price closes below EMA_short
            if latest['close'] < latest['ema_short']:
                return True, "Price closed below EMA short"
        
        elif position_side == "short":
            # Exit short if price closes above EMA_short
            if latest['close'] > latest['ema_short']:
                return True, "Price closed above EMA short"
        
        return False, ""
    
    def check_exit_by_time(self, entry_candle_index: int, current_candle_index: int, 
                          max_candles: int) -> Tuple[bool, str]:
        """
        Check if time-based exit condition is met
        
        Args:
            entry_candle_index: Index when position was opened
            current_candle_index: Current candle index
            max_candles: Maximum candles to hold position
            
        Returns:
            Tuple of (should_exit, reason)
        """
        candles_held = current_candle_index - entry_candle_index
        
        if candles_held >= max_candles:
            return True, f"Time-based exit: held for {candles_held} candles"
        
        return False, ""
    
    def recalculate_with_live_price(self, df: pd.DataFrame, details: Dict, live_price: float) -> Dict:
        """
        Recalculate entry/SL/TP using live current price
        
        Important: Indicators (EMA, RSI, ADX) stay from closed candles
        Only validate entry prices against current market condition
        
        Args:
            df: DataFrame with indicators
            details: Original signal details from check_long_entry
            live_price: Current live market price
            
        Returns:
            Updated details dict with live price info
        """
        latest = df.iloc[-1]
        
        # Validate live price movement since last candle
        price_change_pct = ((live_price - latest['close']) / latest['close']) * 100
        
        # Warn if price moved significantly (>5%)
        if abs(price_change_pct) > 5:
            details['warning'] = f"Price moved {price_change_pct:+.2f}% since last candle. High volatility!"
        
        # Get EMA levels (these are our entry targets)
        ema_short = latest['ema_short']
        # ema_long = latest['ema_long']
        
        # Check if live price is in good entry zone
        if live_price < ema_short:
            details['entry_status'] = "✓ In entry zone (pullback to support)"
        elif live_price < ema_short * 1.02:  # Within 2% above EMA
            details['entry_status'] = "⚠ Near entry zone (slight premium)"
        else:
            details['entry_status'] = "⚠ Above entry zone (chasing risk - consider waiting)"
        
        # Keep entry prices from original calculation (EMA-based)
        # These are already set in check_long_entry
        # Just add live price info for monitoring
        details['live_price'] = live_price
        details['last_candle_price'] = latest['close']
        details['price_change_pct'] = price_change_pct
        
        return details
    
    def get_strategy_status(self, df: pd.DataFrame, live_price: Optional[float] = None) -> Dict:
        """Get current strategy status and signals (SPOT LONG ONLY)"""
        if len(df) == 0:
            return {"error": "No data available"}

        # Check signals (LONG ONLY - no short for spot trading)
        long_signal, long_details = self.check_long_entry(df)

        # Get latest indicators
        latest_indicators = Indicators.get_latest_indicators(df)

        # Prepare base status dictionary
        status = {
            "timestamp": df.iloc[-1].get('timestamp', ''),
            "indicators": latest_indicators,
            "long_signal": long_signal,
            "long_details": long_details
        }
        
        # Add live price if provided
        if live_price:
            status['live_price'] = live_price
            candle_price = latest_indicators['price']
            status['price_change_pct'] = ((live_price - candle_price) / candle_price) * 100

        # Only add entry details if signal is YES
        if long_signal and 'entry_1' in long_details and 'entry_2' in long_details:
            status['entry_1'] = long_details['entry_1']
            status['entry_2'] = long_details['entry_2']
            
            # If live price provided, add entry zone status
            if live_price:
                ema_short = latest_indicators['ema_short']
                if live_price < ema_short:
                    status['entry_zone_status'] = "✓ In entry zone"
                elif live_price < ema_short * 1.02:
                    status['entry_zone_status'] = "⚠ Near entry zone"
                else:
                    status['entry_zone_status'] = "⚠ Above entry zone"

        return status

    
    def format_status_for_display(self, status: Dict) -> str:
        """Format strategy status for terminal display"""
        if "error" in status:
            return f"Error: {status['error']}"

        indicators = status['indicators']
        output = []

        output.append("\n" + "="*60)
        output.append("STRATEGY STATUS")
        output.append("="*60)

        # Show both candle and live price with emphasis on live
        if 'live_price' in status and status['live_price']:
            output.append(f"\n🔴 LIVE CURRENT PRICE: ${status['live_price']:.4f}")
            change_pct = status.get('price_change_pct', 0)
            if change_pct != 0:
                direction = "🔼" if change_pct > 0 else "🔽"
                output.append(f"   {direction} Change from last candle: {change_pct:+.2f}%")
            if 'entry_zone_status' in status:
                output.append(f"   Entry Zone: {status['entry_zone_status']}")
            output.append(f"\nLast Candle Close: ${indicators['price']:.4f} (Historical)")
        else:
            output.append(f"\n⚠️  Price: ${indicators['price']:.4f} (Last Candle Close - No Live Price)")
            
        output.append(f"EMA Short ({self.ema_short}): {indicators['ema_short']:.4f}")
        output.append(f"EMA Long ({self.ema_long}): {indicators['ema_long']:.4f}")
        output.append(f"RSI ({self.rsi_length}): {indicators['rsi']:.2f}")
        output.append(f"ADX: {indicators['adx']:.2f}")
        output.append(f"ATR: {indicators['atr']:.6f}")

        output.append("\n" + "-"*60)
        output.append("LONG ENTRY ANALYSIS")
        output.append("-"*60)

        long_details = status['long_details']
        output.append(f"Signal: {'✓ YES' if status['long_signal'] else '✗ NO'}")
        output.append(f"EMA Aligned: {'✓' if long_details.get('ema_aligned') else '✗'}")
        output.append(f"RSI Valid ({self.rsi_min}-{self.rsi_max}): {'✓' if long_details.get('rsi_valid') else '✗'}")
        output.append(f"ADX >= {self.adx_threshold}: {'✓' if long_details.get('adx_valid') else '✗'}")
        output.append(f"Volume Valid: {'✓' if long_details.get('volume_valid') else '✗'}")
        output.append(f"Reason: {long_details.get('reason', 'N/A')}")

        # Only show TRADE DETAILS if signal is YES and entry details exist
        if status['long_signal'] and 'entry_1' in status and 'entry_2' in status:
            output.append("\n" + "-"*60)
            output.append("TRADE DETAILS")
            output.append("-"*60)
            
            # Get percentages from config
            entry_1_pct = self.config.get('entry_1_percent', 30)
            entry_2_pct = self.config.get('entry_2_percent', 70)
            
            output.append(f"Entry 1 Price: {status['entry_1']['price']:.4f}")
            output.append(f"Stop Loss 1:   {status['entry_1']['stop_loss']:.4f} (-{((status['entry_1']['price'] - status['entry_1']['stop_loss']) / status['entry_1']['price'] * 100):.2f}%)")
            output.append(f"Take Profit 1: {status['entry_1']['take_profit']:.4f} (+{((status['entry_1']['take_profit'] - status['entry_1']['price']) / status['entry_1']['price'] * 100):.2f}%) [{entry_1_pct}% position]")
            output.append(f"Risk/Reward 1: 1:{status['entry_1']['risk_reward']}")

            output.append(f"\nEntry 2 Price: {status['entry_2']['price']:.4f}")
            output.append(f"Stop Loss 2:   {status['entry_2']['stop_loss']:.4f} (-{((status['entry_2']['price'] - status['entry_2']['stop_loss']) / status['entry_2']['price'] * 100):.2f}%)")
            output.append(f"Take Profit 2: {status['entry_2']['take_profit']:.4f} (+{((status['entry_2']['take_profit'] - status['entry_2']['price']) / status['entry_2']['price'] * 100):.2f}%) [{entry_2_pct}% position]")
            output.append(f"Risk/Reward 2: 1:{status['entry_2']['risk_reward']}")

        return "\n".join(output)





if __name__ == "__main__":
    print("Trading Strategy Module")
    print("MA Method 2: Trend Following + Momentum Confluence")
    
    # Example configuration
    config = {
        'ema_short': 9,
        'ema_long': 21,
        'rsi_length': 14,
        'rsi_min': 40,
        'rsi_max': 70,
        'adx_threshold': 25,
        'atr_period': 14,
        'use_volume_filter': True
    }
    
    strategy = TradingStrategy(config)
    print(f"\nStrategy initialized with config:")
    print(f"EMA: {config['ema_short']}/{config['ema_long']}")
    print(f"RSI: {config['rsi_length']} (range: {config['rsi_min']}-{config['rsi_max']})")
    print(f"ADX threshold: {config['adx_threshold']}")
