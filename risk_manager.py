"""
Risk Management Module
Handle position sizing, stop loss, take profit, and trailing stops
"""

from typing import Dict, Optional, Tuple
import pandas as pd


class RiskManager:
    """
    Risk Management System
    - Volatility-based position sizing
    - ATR-based stop loss
    - Multi-tier take profit
    - Trailing stop
    """
    
    def __init__(self, config: Dict):
        """
        Initialize risk manager
        
        Args:
            config: Risk management configuration
        """
        # Stop loss settings
        self.sl_atr_multiplier = config.get('sl_atr_multiplier', 1.5)
        
        # Take profit settings
        self.tp1_rr = config.get('tp1_rr', 1.0)  # Risk:Reward ratio for TP1
        self.tp1_percent = config.get('tp1_percent', 30)  # % of position to close at TP1
        
        self.tp2_rr = config.get('tp2_rr', 2.0)  # Risk:Reward ratio for TP2
        self.tp2_percent = config.get('tp2_percent', 40)  # % of position to close at TP2
        
        # Trailing stop settings
        self.trailing_atr_multiplier = config.get('trailing_atr_multiplier', 1.0)
        
        # Time-based exit
        self.max_candles_hold = config.get('max_candles_hold', 20)
    
    def calculate_position_size(self, equity: float, entry_price: float, 
                                stop_loss: float, min_size: float = 0.0001,
                                max_usdt_allocation: Optional[float] = None) -> float:
        """
        Calculate position size based on max USDT allocation
        
        Args:
            equity: Total equity in quote currency (e.g., USDT) - NOT USED in allocation-based
            entry_price: Entry price
            stop_loss: Stop loss price
            min_size: Minimum position size allowed
            max_usdt_allocation: Maximum USDT to allocate per trade (REQUIRED)
            
        Returns:
            Position size in base currency units
        """
        if not max_usdt_allocation or max_usdt_allocation <= 0:
            return min_size
        
        # Calculate position size from USDT allocation
        position_size = max_usdt_allocation / entry_price
        
        # Ensure minimum size
        position_size = max(position_size, min_size)
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, atr: float, side: str = "long") -> float:
        """
        Calculate ATR-based stop loss
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            side: Position side ("long" or "short")
            
        Returns:
            Stop loss price
        """
        sl_distance = atr * self.sl_atr_multiplier
        
        if side == "long":
            stop_loss = entry_price - sl_distance
        else:  # short
            stop_loss = entry_price + sl_distance
        
        return stop_loss
    
    def calculate_take_profits(self, entry_price: float, stop_loss: float, 
                              side: str = "long") -> Dict[str, float]:
        """
        Calculate multi-tier take profit levels
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: Position side ("long" or "short")
            
        Returns:
            Dictionary with TP levels
        """
        # Calculate risk (SL distance)
        risk_distance = abs(entry_price - stop_loss)
        
        if side == "long":
            tp1 = entry_price + (risk_distance * self.tp1_rr)
            tp2 = entry_price + (risk_distance * self.tp2_rr)
        else:  # short
            tp1 = entry_price - (risk_distance * self.tp1_rr)
            tp2 = entry_price - (risk_distance * self.tp2_rr)
        
        return {
            "tp1": tp1,
            "tp1_percent": self.tp1_percent,
            "tp2": tp2,
            "tp2_percent": self.tp2_percent,
            "risk_distance": risk_distance
        }
    
    def calculate_trailing_stop(self, entry_price: float, current_price: float, 
                                atr: float, side: str = "long", 
                                current_trailing_stop: Optional[float] = None) -> float:
        """
        Calculate trailing stop based on ATR
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            atr: Current ATR value
            side: Position side ("long" or "short")
            current_trailing_stop: Current trailing stop (if exists)
            
        Returns:
            Updated trailing stop price
        """
        trailing_distance = atr * self.trailing_atr_multiplier
        
        if side == "long":
            new_trailing_stop = current_price - trailing_distance
            
            # Only move trailing stop up, never down
            if current_trailing_stop is None:
                # First time: only set if in profit
                if current_price > entry_price:
                    return max(new_trailing_stop, entry_price)  # At least breakeven
                else:
                    return entry_price  # Breakeven
            else:
                return max(new_trailing_stop, current_trailing_stop)
        
        else:  # short
            new_trailing_stop = current_price + trailing_distance
            
            # Only move trailing stop down, never up
            if current_trailing_stop is None:
                # First time: only set if in profit
                if current_price < entry_price:
                    return min(new_trailing_stop, entry_price)  # At least breakeven
                else:
                    return entry_price  # Breakeven
            else:
                return min(new_trailing_stop, current_trailing_stop)
    
    def check_stop_loss_hit(self, current_price: float, stop_loss: float, 
                           side: str = "long") -> bool:
        """
        Check if stop loss is hit
        
        Args:
            current_price: Current market price
            stop_loss: Stop loss price
            side: Position side
            
        Returns:
            True if stop loss hit, False otherwise
        """
        if side == "long":
            return current_price <= stop_loss
        else:  # short
            return current_price >= stop_loss
    
    def check_take_profit_hit(self, current_price: float, take_profit: float, 
                             side: str = "long") -> bool:
        """
        Check if take profit is hit
        
        Args:
            current_price: Current market price
            take_profit: Take profit price
            side: Position side
            
        Returns:
            True if take profit hit, False otherwise
        """
        if side == "long":
            return current_price >= take_profit
        else:  # short
            return current_price <= take_profit
    
    def create_position(self, entry_price: float, atr: float, equity: float, 
                       side: str = "long", min_size: float = 0.0001,
                       max_usdt_allocation: Optional[float] = None) -> Dict:
        """
        Create a complete position with SL, TP, and position size
        
        DEPRECATED: This method is no longer used. Entry positions are now
        calculated directly in strategy.py using EMA-based entry prices.
        Kept for backward compatibility only.
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            equity: Total equity
            side: Position side
            min_size: Minimum position size
            max_usdt_allocation: Maximum USDT to allocate per trade
            
        Returns:
            Position dictionary with all details
        """
        # Calculate stop loss
        stop_loss = self.calculate_stop_loss(entry_price, atr, side)
        
        # Calculate position size
        position_size = self.calculate_position_size(equity, entry_price, stop_loss, min_size, max_usdt_allocation)
        
        # Calculate take profits
        take_profits = self.calculate_take_profits(entry_price, stop_loss, side)
        
        # Create position object
        position = {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "position_size": position_size,
            "side": side,
            "tp1": take_profits["tp1"],
            "tp1_percent": take_profits["tp1_percent"],
            "tp2": take_profits["tp2"],
            "tp2_percent": take_profits["tp2_percent"],
            "trailing_stop": None,
            "remaining_size": position_size,
            "atr": atr,
            "risk_distance": take_profits["risk_distance"]
        }
        
        return position
    
    def update_position(self, position: Dict, current_price: float, atr: float) -> Tuple[Dict, Optional[str]]:
        """
        Update position with current market data
        Check for SL/TP hits and update trailing stop
        
        Args:
            position: Position dictionary
            current_price: Current market price
            atr: Current ATR value
            
        Returns:
            Tuple of (updated_position, action)
            action can be: None, "stop_loss", "tp1", "tp2", "trailing_stop"
        """
        side = position["side"]
        action = None
        
        # Check stop loss
        if self.check_stop_loss_hit(current_price, position["stop_loss"], side):
            return position, "stop_loss"
        
        # Check TP1
        if position["tp1"] and position["tp1_percent"] > 0:
            if self.check_take_profit_hit(current_price, position["tp1"], side):
                # Close TP1 portion
                close_size = position["position_size"] * (position["tp1_percent"] / 100)
                position["remaining_size"] -= close_size
                position["tp1"] = None  # Mark as hit
                position["tp1_percent"] = 0
                action = "tp1"
                
                # Move stop loss to breakeven after TP1
                position["stop_loss"] = position["entry_price"]
        
        # Check TP2
        if position["tp2"] and position["tp2_percent"] > 0:
            if self.check_take_profit_hit(current_price, position["tp2"], side):
                # Close TP2 portion
                close_size = position["position_size"] * (position["tp2_percent"] / 100)
                position["remaining_size"] -= close_size
                position["tp2"] = None  # Mark as hit
                position["tp2_percent"] = 0
                if action is None:
                    action = "tp2"
        
        # Update trailing stop for remaining position
        if position["remaining_size"] > 0:
            trailing_stop = self.calculate_trailing_stop(
                position["entry_price"],
                current_price,
                atr,
                side,
                position["trailing_stop"]
            )
            position["trailing_stop"] = trailing_stop
            
            # Check if trailing stop is hit
            if self.check_stop_loss_hit(current_price, trailing_stop, side):
                if action is None:
                    action = "trailing_stop"
        
        return position, action
    
    def calculate_pnl(self, position: Dict, current_price: float) -> Dict:
        """
        Calculate current PnL for position
        
        Args:
            position: Position dictionary
            current_price: Current market price
            
        Returns:
            Dictionary with PnL details
        """
        entry_price = position["entry_price"]
        remaining_size = position["remaining_size"]
        side = position["side"]
        
        if side == "long":
            pnl = (current_price - entry_price) * remaining_size
        else:  # short
            pnl = (entry_price - current_price) * remaining_size
        
        pnl_percent = (pnl / position["risk_amount"]) * 100 if position["risk_amount"] > 0 else 0
        
        # Calculate R:R achieved
        risk = abs(entry_price - position["stop_loss"])
        reward = abs(current_price - entry_price)
        rr_achieved = reward / risk if risk > 0 else 0
        
        return {
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "rr_achieved": rr_achieved,
            "remaining_size": remaining_size
        }
    
    def format_position_for_display(self, position: Dict, current_price: float) -> str:
        """
        Format position details for terminal display
        
        Args:
            position: Position dictionary
            current_price: Current market price
            
        Returns:
            Formatted string
        """
        pnl_info = self.calculate_pnl(position, current_price)
        
        output = []
        output.append("\n" + "="*60)
        output.append("POSITION DETAILS")
        output.append("="*60)
        
        output.append(f"Side: {position['side'].upper()}")
        output.append(f"Entry Price: {position['entry_price']:.4f}")
        output.append(f"Current Price: {current_price:.4f}")
        output.append(f"Position Size: {position['position_size']:.6f}")
        output.append(f"Remaining Size: {position['remaining_size']:.6f}")
        
        output.append("\n" + "-"*60)
        output.append("RISK MANAGEMENT")
        output.append("-"*60)
        
        output.append(f"Stop Loss: {position['stop_loss']:.4f}")
        if position['tp1']:
            output.append(f"TP1 ({position['tp1_percent']}%): {position['tp1']:.4f}")
        else:
            output.append(f"TP1: ✓ HIT")
        
        if position['tp2']:
            output.append(f"TP2 ({position['tp2_percent']}%): {position['tp2']:.4f}")
        else:
            output.append(f"TP2: ✓ HIT")
        
        if position['trailing_stop']:
            output.append(f"Trailing Stop: {position['trailing_stop']:.4f}")
        
        output.append("\n" + "-"*60)
        output.append("PROFIT & LOSS")
        output.append("-"*60)
        
        output.append(f"PnL: {pnl_info['pnl']:.4f} ({pnl_info['pnl_percent']:.2f}%)")
        output.append(f"R:R Achieved: {pnl_info['rr_achieved']:.2f}")
        
        return "\n".join(output)


if __name__ == "__main__":
    print("Risk Management Module")
    print("Features: Position Sizing, ATR-based SL/TP, Trailing Stop")
    
    # Example configuration
    config = {
        'sl_atr_multiplier': 1.5,
        'tp1_rr': 1.0,
        'tp1_percent': 30,
        'tp2_rr': 2.0,
        'tp2_percent': 40,
        'trailing_atr_multiplier': 1.0,
        'max_candles_hold': 20
    }
    
    rm = RiskManager(config)
    
    # Example position
    equity = 1000  # $1000 USDT
    entry_price = 50000
    atr = 500
    
    position = rm.create_position(entry_price, atr, equity, side="long")
    
    print("\nExample Position:")
    print(f"Entry: {position['entry_price']}")
    print(f"Stop Loss: {position['stop_loss']:.2f}")
    print(f"TP1: {position['tp1']:.2f}")
    print(f"TP2: {position['tp2']:.2f}")
    print(f"Position Size: {position['position_size']:.6f}")
