"""
Technical Indicators Calculator
Calculate EMA, RSI, ADX, ATR for trading strategy
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


class Indicators:
    """Technical indicators calculator"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        Args:
            data: Price data series
            period: EMA period
            
        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average
        
        Args:
            data: Price data series
            period: SMA period
            
        Returns:
            SMA series
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index
        
        Args:
            data: Price data series
            period: RSI period (default 14)
            
        Returns:
            RSI series
        """
        # Calculate price changes
        delta = data.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR period (default 14)
            
        Returns:
            ATR series
        """
        # Calculate True Range components
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()
        
        # True Range is the maximum of the three
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Calculate ATR as moving average of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return atr
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Average Directional Index (ADX), +DI, -DI
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ADX period (default 14)
            
        Returns:
            Tuple of (ADX, +DI, -DI) series
        """
        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # Calculate ATR
        atr = Indicators.calculate_atr(high, low, close, period)
        
        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
        
        # Calculate DX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        
        # Calculate ADX
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def calculate_volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
        """
        Calculate Volume Moving Average
        
        Args:
            volume: Volume data series
            period: MA period (default 20)
            
        Returns:
            Volume MA series
        """
        return volume.rolling(window=period).mean()
    
    @staticmethod
    def check_ema_crossover(ema_short: pd.Series, ema_long: pd.Series, lookback: int = 2) -> Tuple[bool, bool]:
        """
        Check for EMA crossover (bullish or bearish)
        
        Args:
            ema_short: Short EMA series
            ema_long: Long EMA series
            lookback: How many candles back to check (default 2)
            
        Returns:
            Tuple of (bullish_crossover, bearish_crossover)
        """
        if len(ema_short) < lookback + 1 or len(ema_long) < lookback + 1:
            return False, False
        
        # Current: short > long
        current_bullish = ema_short.iloc[-1] > ema_long.iloc[-1]
        # Previous: short < long
        previous_bearish = ema_short.iloc[-lookback] < ema_long.iloc[-lookback]
        
        bullish_crossover = current_bullish and previous_bearish
        
        # Current: short < long
        current_bearish = ema_short.iloc[-1] < ema_long.iloc[-1]
        # Previous: short > long
        previous_bullish = ema_short.iloc[-lookback] > ema_long.iloc[-lookback]
        
        bearish_crossover = current_bearish and previous_bullish
        
        return bullish_crossover, bearish_crossover
    
    @staticmethod
    def is_trend_aligned(close: pd.Series, ema_short: pd.Series, ema_long: pd.Series, trend: str = "bullish") -> bool:
        """
        Check if price and EMAs are aligned with trend
        
        Args:
            close: Close price series
            ema_short: Short EMA series
            ema_long: Long EMA series
            trend: "bullish" or "bearish"
            
        Returns:
            True if aligned, False otherwise
        """
        if len(close) == 0 or len(ema_short) == 0 or len(ema_long) == 0:
            return False
        
        current_price = close.iloc[-1]
        current_short = ema_short.iloc[-1]
        current_long = ema_long.iloc[-1]
        
        if trend == "bullish":
            # Price > Short EMA > Long EMA
            return current_price > current_short and current_short > current_long
        elif trend == "bearish":
            # Price < Short EMA < Long EMA
            return current_price < current_short and current_short < current_long
        
        return False
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame, ema_short: int = 9, ema_long: int = 21,
                                 rsi_period: int = 14, atr_period: int = 14,
                                 adx_period: int = 14, volume_ma_period: int = 20) -> pd.DataFrame:
        """
        Calculate all technical indicators for a dataframe
        
        Args:
            df: DataFrame with OHLCV data
            ema_short: Short EMA period
            ema_long: Long EMA period
            rsi_period: RSI period
            atr_period: ATR period
            adx_period: ADX period
            volume_ma_period: Volume MA period
            
        Returns:
            DataFrame with all indicators added
        """
        df = df.copy()
        
        # Calculate EMAs
        df['ema_short'] = Indicators.calculate_ema(df['close'], ema_short)
        df['ema_long'] = Indicators.calculate_ema(df['close'], ema_long)
        
        # Calculate RSI
        df['rsi'] = Indicators.calculate_rsi(df['close'], rsi_period)
        
        # Calculate ATR
        df['atr'] = Indicators.calculate_atr(df['high'], df['low'], df['close'], atr_period)
        
        # Calculate ADX, +DI, -DI
        adx, plus_di, minus_di = Indicators.calculate_adx(df['high'], df['low'], df['close'], adx_period)
        df['adx'] = adx
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        
        # Calculate Volume MA
        if 'volume' in df.columns:
            df['volume_ma'] = Indicators.calculate_volume_ma(df['volume'], volume_ma_period)
        
        return df
    
    @staticmethod
    def get_latest_indicators(df: pd.DataFrame) -> dict:
        """
        Get latest indicator values from dataframe
        
        Args:
            df: DataFrame with indicators
            
        Returns:
            Dictionary with latest indicator values
        """
        if len(df) == 0:
            return {}
        
        latest = df.iloc[-1]
        indicators = {
            'price': latest.get('close', 0),
            'ema_short': latest.get('ema_short', 0),
            'ema_long': latest.get('ema_long', 0),
            'rsi': latest.get('rsi', 0),
            'atr': latest.get('atr', 0),
            'adx': latest.get('adx', 0),
            'plus_di': latest.get('plus_di', 0),
            'minus_di': latest.get('minus_di', 0),
            'volume': latest.get('volume', 0),
            'volume_ma': latest.get('volume_ma', 0)
        }
        
        return indicators
    
    @staticmethod
    def format_indicators_for_display(indicators: dict) -> str:
        """
        Format indicators for terminal display
        
        Args:
            indicators: Dictionary with indicator values
            
        Returns:
            Formatted string
        """
        output = []
        output.append(f"Price: {indicators.get('price', 0):.2f}")
        output.append(f"EMA Short: {indicators.get('ema_short', 0):.2f}")
        output.append(f"EMA Long: {indicators.get('ema_long', 0):.2f}")
        output.append(f"RSI: {indicators.get('rsi', 0):.2f}")
        output.append(f"ADX: {indicators.get('adx', 0):.2f}")
        output.append(f"ATR: {indicators.get('atr', 0):.4f}")
        output.append(f"Volume: {indicators.get('volume', 0):.2f}")
        
        return " | ".join(output)


if __name__ == "__main__":
    # Test with sample data
    print("Indicators module loaded successfully")
    print("Available indicators: EMA, RSI, ADX, ATR, Volume MA")
    
    # Example usage
    sample_data = pd.DataFrame({
        'close': [100, 101, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 115],
        'high': [101, 102, 103, 102, 104, 106, 105, 107, 109, 108, 110, 112, 111, 113, 116],
        'low': [99, 100, 101, 100, 102, 104, 103, 105, 107, 106, 108, 110, 109, 111, 114],
        'volume': [1000, 1100, 950, 1200, 1300, 1400, 1100, 1500, 1600, 1200, 1700, 1800, 1300, 1900, 2000]
    })
    
    result = Indicators.calculate_all_indicators(sample_data)
    print("\nSample calculation:")
    print(result[['close', 'ema_short', 'ema_long', 'rsi', 'atr', 'adx']].tail())
