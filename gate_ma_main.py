"""
Gate.io Trading Bot - MA Method 2
Main script with Interactive Terminal UI
Same strategy as BitMart version, using Gate.io API
"""

import os
import sys
import time
import argparse
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

# Try to import colorama for colored output (optional)
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    # Fallback to no colors if colorama not installed
    class Fore:
        GREEN = RED = YELLOW = CYAN = WHITE = ''
    class Style:
        RESET_ALL = ''
    COLORAMA_AVAILABLE = False

# Import bot modules
from gate_api import GateAPI
from indicators import Indicators
from strategy import TradingStrategy
from risk_manager import RiskManager
from logger_config import setup_logger

# Load environment variables
load_dotenv()


class TradingBot:
    """Main Trading Bot Class for Gate.io"""
    
    def __init__(self):
        """Initialize trading bot"""
        # Load configuration
        self.config = self._load_config()
        
        # Initialize logger
        self.logger = setup_logger(
            log_level=self.config['log_level']
        )
        
        # Print clean startup info
        self._print_startup_info()
        
        # Initialize Gate.io API
        self.api = GateAPI(
            api_key=self.config['api_key'],
            secret_key=self.config['secret_key'],
            testnet=self.config['use_testnet']
        )
        
        # Initialize strategy
        self.strategy = TradingStrategy(self.config)
        
        # Initialize risk manager
        self.risk_manager = RiskManager(self.config)
        
        # Bot state
        self.is_running = False
        self.current_position = None
        self.trade_history = []
        self.equity = 0.0
        
        # Data
        self.df = None
        self.last_update = None
        
        self.logger.info("Trading bot initialized successfully")
    
    def _load_config(self) -> Dict:
        """Load configuration from environment variables"""
        # Convert Gate.io symbol format (BTC_USDT) to internal format if needed
        trading_pair = os.getenv('TRADING_PAIR', 'BTC_USDT')
        # Ensure underscore format for Gate.io
        if '/' in trading_pair:
            trading_pair = trading_pair.replace('/', '_')
        
        config = {
            # API credentials
            'api_key': os.getenv('GATE_API_KEY', ''),
            'secret_key': os.getenv('GATE_API_SECRET', ''),
            'use_testnet': os.getenv('USE_TESTNET', '1') == '1',
            'account': os.getenv('GATE_ACCOUNT', 'spot'),
            
            # Trading settings
            'trading_pair': trading_pair,
            'timeframe': os.getenv('TIMEFRAME', '4H'),
            
            # Strategy parameters
            'ema_short': int(os.getenv('EMA_SHORT', 12)),
            'ema_long': int(os.getenv('EMA_LONG', 26)),
            'rsi_length': int(os.getenv('RSI_LENGTH', 14)),
            'rsi_min': float(os.getenv('RSI_MIN', 40)),
            'rsi_max': float(os.getenv('RSI_MAX', 70)),
            'adx_period': int(os.getenv('ADX_PERIOD', 14)),
            'adx_threshold': float(os.getenv('ADX_THRESHOLD', 25)),
            'atr_period': int(os.getenv('ATR_PERIOD', 14)),
            
            # Risk management
            'max_usdt_per_trade': float(os.getenv('MAX_USDT_PER_TRADE', 500)),
            'entry_1_percent': float(os.getenv('ENTRY_1_PERCENT', 30)),
            'entry_2_percent': float(os.getenv('ENTRY_2_PERCENT', 70)),
            'sl_atr_multiplier': float(os.getenv('STOP_LOSS_ATR_MULTIPLIER', 2.5)),
            'trailing_atr_multiplier': float(os.getenv('TRAILING_STOP_ATR_MULTIPLIER', 2.0)),
            'tp1_rr': float(os.getenv('TP1_RR', 1.0)),
            'tp1_percent': float(os.getenv('TP1_PERCENT', 30)),
            'tp2_rr': float(os.getenv('TP2_RR', 2.0)),
            'tp2_percent': float(os.getenv('TP2_PERCENT', 50)),
            'max_candles_hold': int(os.getenv('MAX_CANDLES_HOLD', 5)),
            
            # Bot settings
            'dry_run': os.getenv('DRY_RUN', 'false').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            
            # Volume filter
            'use_volume_filter': True,
            'volume_ma_period': 20
        }
        
        return config
    
    def _print_startup_info(self):
        """Print clean startup information"""
        mode = "[TESTNET]" if self.config.get('use_testnet', False) else "[MAINNET - LIVE]"
        mode_color = Fore.YELLOW if self.config.get('use_testnet', False) else Fore.RED
        print(f"{Fore.CYAN}{'='*60}")
        print(f"Gate.io Trading Bot - MA Method 2")
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}WARNING: SPOT TRADING - LONG ONLY (BUY & SELL){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}         No SHORT SELLING or LEVERAGE{Style.RESET_ALL}\n")
        print(f"{Fore.GREEN}Exchange:{Style.RESET_ALL} Gate.io {mode_color}{mode}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Trading Pair:{Style.RESET_ALL} {self.config['trading_pair']}")
        print(f"{Fore.GREEN}Timeframe:{Style.RESET_ALL} {self.config['timeframe']}")
        print(f"{Fore.GREEN}Strategy:{Style.RESET_ALL} EMA {self.config['ema_short']}/{self.config['ema_long']} + RSI({self.config['rsi_length']}) + ADX({self.config['adx_threshold']})")
        if self.config['max_usdt_per_trade'] > 0:
            print(f"{Fore.GREEN}Max USDT per Trade:{Style.RESET_ALL} {self.config['max_usdt_per_trade']:.2f} USDT")
        else:
            print(f"{Fore.GREEN}Max USDT per Trade:{Style.RESET_ALL} Unlimited (based on risk %)")
        print(f"{Fore.GREEN}Entry Split:{Style.RESET_ALL} Entry 1 ({self.config['entry_1_percent']}%) | Entry 2 ({self.config['entry_2_percent']}%)")
        print(f"{Fore.GREEN}Mode:{Style.RESET_ALL} {'DRY RUN (Simulation)' if self.config['dry_run'] else 'LIVE TRADING'}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    def _get_timeframe_seconds(self) -> int:
        """Convert timeframe string to seconds"""
        timeframe_map = {
            '10s': 10, '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
            '1h': 3600, '1H': 3600, '4h': 14400, '4H': 14400, '8h': 28800, '8H': 28800,
            '1d': 86400, '1D': 86400, '7d': 604800, '7D': 604800, '30d': 2592000, '30D': 2592000
        }
        return timeframe_map.get(self.config['timeframe'], 14400)  # Default 4H
    
    def _get_gate_interval(self) -> str:
        """Convert timeframe to Gate.io interval parameter"""
        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1H': '1h', '1h': '1h', '4H': '4h', '4h': '4h', '8H': '8h', '8h': '8h',
            '1D': '1d', '1d': '1d', '7D': '7d', '7d': '7d', '30D': '30d', '30d': '30d'
        }
        return interval_map.get(self.config['timeframe'], '4h')  # Default 4h
    
    def fetch_market_data(self, limit: int = 200) -> bool:
        """
        Fetch market data from Gate.io
        
        Args:
            limit: Number of candles to fetch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = self.config['trading_pair']
            interval = self._get_gate_interval()
            
            # Calculate time range
            now = int(time.time())
            timeframe_seconds = self._get_timeframe_seconds()
            from_time = now - (limit * timeframe_seconds)
            
            # Fetch kline data from Gate.io
            klines = self.api.get_klines(symbol, interval, limit, from_time, now)
            
            if not klines:
                self.logger.error("No kline data received from Gate.io")
                return False
            
            # Convert to DataFrame
            # Gate.io format: [timestamp, volume, close, high, low, open, amount]
            df_data = []
            for kline in klines:
                df_data.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[5]),
                    'high': float(kline[3]),
                    'low': float(kline[4]),
                    'close': float(kline[2]),
                    'volume': float(kline[6])  # Use amount (base currency volume)
                })
            
            self.df = pd.DataFrame(df_data)
            
            # Calculate indicators
            self.df = self.strategy.calculate_indicators(self.df)
            
            self.last_update = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.log_exception(e, "fetch_market_data")
            return False
    
    def get_live_price(self) -> Optional[float]:
        """Get current live price from ticker (real-time)"""
        try:
            symbol = self.config['trading_pair']
            live_price = self.api.get_last_price(symbol)
            
            if live_price and live_price > 0:
                return live_price
            else:
                self.logger.warning(f"Invalid live price received: {live_price}")
                return None
                
        except Exception as e:
            self.logger.log_exception(e, "get_live_price")
            return None
    
    def update_equity(self) -> bool:
        """Update equity from account balance"""
        try:
            # Get USDT balance from Gate.io
            balance = self.api.get_balance('USDT')
            self.equity = balance['available'] + balance['locked']
            
            self.logger.log_balance_update('USDT', balance['available'], balance['locked'])
            return True
            
        except Exception as e:
            self.logger.log_exception(e, "update_equity")
            return False
    
    def check_entry_signal(self):
        """Check for entry signals and execute trade (SPOT LONG ONLY)"""
        if self.current_position is not None:
            return  # Already in position
        
        # Check long entry (SPOT BUY only)
        live_price = self.get_live_price()
        if live_price is None:
            print(f"{Fore.RED}✗ Failed to get live price, skipping signal check{Style.RESET_ALL}")
            return
        
        # Bot HANYA akan place order jika SEMUA kondisi terpenuhi (Signal = YES)
        long_signal, details = self.strategy.check_long_entry(self.df)
        
        if long_signal:
            # Update details with live price for accurate calculation
            candle_price = details['price']
            price_change = ((live_price - candle_price) / candle_price) * 100
            
            # ✓ SIGNAL YES - Semua kondisi terpenuhi, siap place order!
            print(f"{Fore.GREEN}✓ ENTRY SIGNAL FOUND! All conditions met.{Style.RESET_ALL}")
            print(f"{Fore.GREEN}  Last Candle: {candle_price:.4f} | Live: {live_price:.4f} ({price_change:+.2f}%){Style.RESET_ALL}")
            print(f"{Fore.GREEN}  RSI: {details['rsi']:.1f} | ADX: {details['adx']:.1f}{Style.RESET_ALL}")
            
            # Recalculate entry prices with live price awareness
            details = self.strategy.recalculate_with_live_price(self.df, details, live_price)
            
            # Warn if price moved significantly
            if 'warning' in details:
                print(f"{Fore.YELLOW}⚠  {details['warning']}{Style.RESET_ALL}")
            
            if 'entry_status' in details:
                status_color = Fore.GREEN if '✓' in details['entry_status'] else Fore.YELLOW
                print(f"{status_color}  Entry Status: {details['entry_status']}{Style.RESET_ALL}")
            
            self.logger.log_signal(
                self.config['trading_pair'],
                "LONG ENTRY",
                details
            )
            
            if not self.config['dry_run']:
                self.execute_entry("long", details)
            else:
                self.simulate_entry("long", details)
        else:
            # ✗ SIGNAL NO - Ada kondisi yang tidak terpenuhi, skip order
            print(f"{Fore.YELLOW}✗ No entry signal.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Live: {live_price:.4f} | Last Candle: {details['price']:.4f}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Reason: {details.get('reason', 'N/A')}{Style.RESET_ALL}")
    
    def _format_order_params(self, symbol: str, price: float, amount: float):
        """Format order parameters according to Gate.io requirements"""
        try:
            # Get pair details for precision
            pair = self.api.get_pair_detail(symbol)
            price_precision = int(pair['precision'])
            amount_precision = int(pair['amount_precision'])
            
            # Format with proper precision
            from decimal import Decimal, ROUND_DOWN
            
            # Price
            price_str = format(
                Decimal(str(price)).quantize(
                    Decimal(f"1e-{price_precision}"),
                    rounding=ROUND_DOWN
                ),
                f".{price_precision}f"
            )
            
            # Amount
            amount_str = format(
                Decimal(str(amount)).quantize(
                    Decimal(f"1e-{amount_precision}"),
                    rounding=ROUND_DOWN
                ),
                f".{amount_precision}f"
            )
            
            return price_str, amount_str
            
        except Exception as e:
            self.logger.error(f"Error formatting order params: {e}")
            # Fallback to simple string conversion
            return f"{price:.8f}", f"{amount:.8f}"
    
    def execute_entry(self, side: str, details: Dict):
        """Execute real entry trade with 2 entries"""
        try:
            symbol = self.config['trading_pair']
            
            # Check if entry details are available (from strategy)
            if 'entry_1' not in details or 'entry_2' not in details:
                self.logger.error("Entry details not available in signal")
                return
            
            entry_1 = details['entry_1']
            entry_2 = details['entry_2']
            
            # Execute Entry 1
            price_1_str, amount_1_str = self._format_order_params(
                symbol, entry_1['price'], entry_1['position_size']
            )
            
            result_1 = self.api.create_limit_order(
                symbol=symbol,
                side='buy' if side == 'long' else 'sell',
                price=float(price_1_str),
                amount=float(amount_1_str),
                time_in_force='gtc',  # Good till cancelled
                account=self.config['account'],
                text=f"t-entry1-{int(time.time())}"
            )
            
            if result_1.get('status') in ['open', 'closed']:
                order_id_1 = result_1.get('id')
                print(f"{Fore.GREEN}✓ Entry 1 placed: {entry_1['position_size']:.6f} @ {entry_1['price']:.4f} ({self.config['entry_1_percent']}%){Style.RESET_ALL}")
                
                # Execute Entry 2
                price_2_str, amount_2_str = self._format_order_params(
                    symbol, entry_2['price'], entry_2['position_size']
                )
                
                result_2 = self.api.create_limit_order(
                    symbol=symbol,
                    side='buy' if side == 'long' else 'sell',
                    price=float(price_2_str),
                    amount=float(amount_2_str),
                    time_in_force='gtc',
                    account=self.config['account'],
                    text=f"t-entry2-{int(time.time())}"
                )
                
                if result_2.get('status') in ['open', 'closed']:
                    order_id_2 = result_2.get('id')
                    print(f"{Fore.GREEN}✓ Entry 2 placed: {entry_2['position_size']:.6f} @ {entry_2['price']:.4f} ({self.config['entry_2_percent']}%){Style.RESET_ALL}")
                    
                    # Calculate weighted averages
                    total_size = entry_1['position_size'] + entry_2['position_size']
                    if total_size > 0:
                        avg_entry = (entry_1['price'] * entry_1['position_size'] + entry_2['price'] * entry_2['position_size']) / total_size
                        avg_sl = (entry_1['stop_loss'] * entry_1['position_size'] + entry_2['stop_loss'] * entry_2['position_size']) / total_size
                        avg_tp = (entry_1['take_profit'] * entry_1['position_size'] + entry_2['take_profit'] * entry_2['position_size']) / total_size
                    else:
                        avg_entry = (entry_1['price'] + entry_2['price']) / 2
                        avg_sl = (entry_1['stop_loss'] + entry_2['stop_loss']) / 2
                        avg_tp = (entry_1['take_profit'] + entry_2['take_profit']) / 2
                    
                    # Store position details in flat structure for risk_manager
                    self.current_position = {
                        'side': side,
                        'entry_time': datetime.now(),
                        'entry_price': avg_entry,
                        'stop_loss': avg_sl,
                        'position_size': total_size,
                        'remaining_size': total_size,
                        'tp1': avg_tp,
                        'tp1_percent': self.config.get('tp1_percent', 30),
                        'tp2': None,
                        'tp2_percent': 0,
                        'trailing_stop': None,
                        'order_ids': [order_id_1, order_id_2]
                    }
                    
                    self.logger.log_trade_entry(
                        symbol=symbol,
                        side=side,
                        entry_price=avg_entry,
                        size=total_size,
                        stop_loss=avg_sl,
                        take_profits={'tp1': avg_tp}
                    )
                else:
                    error_msg = result_2.get('message', 'Unknown error')
                    self.logger.log_order_error(symbol, side, Exception(error_msg))
                    print(f"{Fore.RED}✗ Entry 2 failed: {error_msg}{Style.RESET_ALL}")
            else:
                error_msg = result_1.get('message', 'Unknown error')
                self.logger.log_order_error(symbol, side, Exception(error_msg))
                print(f"{Fore.RED}✗ Entry 1 failed: {error_msg}{Style.RESET_ALL}")
                
        except Exception as e:
            self.logger.log_exception(e, "execute_entry")
            print(f"{Fore.RED}✗ Execute entry error: {e}{Style.RESET_ALL}")
    
    def simulate_entry(self, side: str, details: Dict):
        """Simulate entry trade (DRY RUN mode) with 2 entries"""
        try:
            # Check if entry details are available
            if 'entry_1' not in details or 'entry_2' not in details:
                self.logger.error("Entry details not available in signal")
                return
            
            entry_1 = details['entry_1']
            entry_2 = details['entry_2']
            
            # Calculate weighted averages
            total_size = entry_1['position_size'] + entry_2['position_size']
            if total_size > 0:
                avg_entry = (entry_1['price'] * entry_1['position_size'] + entry_2['price'] * entry_2['position_size']) / total_size
                avg_sl = (entry_1['stop_loss'] * entry_1['position_size'] + entry_2['stop_loss'] * entry_2['position_size']) / total_size
                avg_tp = (entry_1['take_profit'] * entry_1['position_size'] + entry_2['take_profit'] * entry_2['position_size']) / total_size
            else:
                avg_entry = (entry_1['price'] + entry_2['price']) / 2
                avg_sl = (entry_1['stop_loss'] + entry_2['stop_loss']) / 2
                avg_tp = (entry_1['take_profit'] + entry_2['take_profit']) / 2
            
            # Store simulated position in flat structure for risk_manager
            self.current_position = {
                'side': side,
                'entry_time': datetime.now(),
                'simulated': True,
                'entry_price': avg_entry,
                'stop_loss': avg_sl,
                'position_size': total_size,
                'remaining_size': total_size,
                'tp1': avg_tp,
                'tp1_percent': self.config.get('tp1_percent', 30),
                'tp2': None,
                'tp2_percent': 0,
                'trailing_stop': None
            }
            
            # Log simulated entry
            self.logger.log_trade_entry(
                symbol=self.config['trading_pair'],
                side=side,
                entry_price=avg_entry,
                size=total_size,
                stop_loss=avg_sl,
                take_profits={'tp1': avg_tp}
            )
            
            print(f"{Fore.YELLOW}[DRY RUN] Entry 1: {entry_1['position_size']:.6f} @ {entry_1['price']:.4f} ({self.config['entry_1_percent']}%){Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[DRY RUN] Entry 2: {entry_2['position_size']:.6f} @ {entry_2['price']:.4f} ({self.config['entry_2_percent']}%){Style.RESET_ALL}")
            
        except Exception as e:
            self.logger.log_exception(e, "simulate_entry")
    
    def manage_position(self):
        """Manage open position - check SL/TP and update trailing stop"""
        if self.current_position is None or len(self.df) == 0:
            return
        
        current_price = self.df.iloc[-1]['close']
        current_atr = self.df.iloc[-1]['atr']
        
        # Update position with current market data
        updated_position, action = self.risk_manager.update_position(
            self.current_position,
            current_price,
            current_atr
        )
        
        self.current_position = updated_position
        
        # Handle actions
        if action == "stop_loss":
            self.close_position("Stop loss hit", current_price)
        elif action == "tp1":
            print(f"{Fore.GREEN}✓ TP1 hit at {current_price:.4f}{Style.RESET_ALL}")
            self.logger.log_partial_exit(
                self.config['trading_pair'],
                self.current_position['side'],
                current_price,
                self.current_position['position_size'] * (self.current_position.get('tp1_percent', 30) / 100),
                "TP1"
            )
        elif action == "tp2":
            print(f"{Fore.GREEN}✓ TP2 hit at {current_price:.4f}{Style.RESET_ALL}")
            self.logger.log_partial_exit(
                self.config['trading_pair'],
                self.current_position['side'],
                current_price,
                self.current_position['position_size'] * (self.current_position.get('tp2_percent', 40) / 100),
                "TP2"
            )
        elif action == "trailing_stop":
            self.close_position("Trailing stop hit", current_price)
    
    def close_position(self, reason: str, exit_price: float):
        """Close current position"""
        if self.current_position is None:
            return
        
        try:
            pnl_info = self.risk_manager.calculate_pnl(self.current_position, exit_price)
            
            # Log trade exit
            self.logger.log_trade_exit(
                symbol=self.config['trading_pair'],
                side=self.current_position['side'],
                exit_price=exit_price,
                size=self.current_position['remaining_size'],
                pnl=pnl_info['pnl'],
                reason=reason
            )
            
            # Record trade
            trade_record = {
                'entry_time': self.current_position.get('entry_time'),
                'exit_time': datetime.now(),
                'side': self.current_position['side'],
                'entry_price': self.current_position['entry_price'],
                'exit_price': exit_price,
                'size': self.current_position['position_size'],
                'pnl': pnl_info['pnl'],
                'pnl_percent': pnl_info['pnl_percent'],
                'rr_achieved': pnl_info['rr_achieved'],
                'reason': reason
            }
            self.trade_history.append(trade_record)
            
            # Print result
            pnl_color = Fore.GREEN if pnl_info['pnl'] >= 0 else Fore.RED
            print(f"{pnl_color}✓ Position closed: {reason} | PnL: {pnl_info['pnl']:.4f} ({pnl_info['pnl_percent']:.2f}%){Style.RESET_ALL}")
            
            # Clear position
            self.current_position = None
            
        except Exception as e:
            self.logger.log_exception(e, "close_position")
    
    def run_once(self):
        """Run one iteration of the bot"""
        try:
            print(f"\n{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Checking market...{Style.RESET_ALL}")
            
            # Fetch market data
            if not self.fetch_market_data():
                print(f"{Fore.RED}Failed to fetch market data{Style.RESET_ALL}")
                return
            
            current_price = self.df.iloc[-1]['close']
            print(f"{Fore.WHITE}Current Price: {current_price:.4f}{Style.RESET_ALL}")
            
            # Update equity
            if not self.config['dry_run']:
                self.update_equity()
                print(f"{Fore.WHITE}Equity: {self.equity:.2f} USDT{Style.RESET_ALL}")
            
            # Manage existing position
            if self.current_position:
                print(f"{Fore.YELLOW}Managing open position...{Style.RESET_ALL}")
                self.manage_position()
            else:
                print(f"{Fore.WHITE}Scanning for entry signals...{Style.RESET_ALL}")
                # Check for entry signals
                self.check_entry_signal()
            
        except Exception as e:
            self.logger.log_exception(e, "run_once")
    
    def start(self):
        """Start trading bot"""
        self.is_running = True
        self.logger.log_bot_start(self.config)
        
        print(f"{Fore.GREEN}{'='*60}")
        print(f"{Fore.GREEN}Bot started in {'DRY RUN' if self.config['dry_run'] else 'LIVE'} mode")
        print(f"{Fore.GREEN}{'='*60}\n{Style.RESET_ALL}")
        
        update_interval = self._get_timeframe_seconds()
        
        while self.is_running:
            try:
                self.run_once()
                
                # Wait for next candle
                print(f"\nWaiting for next update... (Press Ctrl+C to stop)")
                time.sleep(update_interval)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Bot stopped by user{Style.RESET_ALL}")
                self.stop()
                break
            except Exception as e:
                self.logger.log_exception(e, "Bot main loop")
                time.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop trading bot"""
        self.is_running = False
        
        # Close any open positions
        if self.current_position and not self.config['dry_run']:
            current_price = self.df.iloc[-1]['close'] if self.df is not None else 0
            self.close_position("Bot stopped", current_price)
        
        self.logger.log_bot_stop()
        print(f"{Fore.YELLOW}Bot stopped{Style.RESET_ALL}")


def print_header():
    """Print bot header"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}          Gate.io Trading Bot - MA Method 2")
    print(f"{Fore.CYAN}{'='*60}\n{Style.RESET_ALL}")


def print_menu():
    """Print main menu"""
    print(f"\n{Fore.CYAN}{'─'*60}")
    print(f"{Fore.CYAN}MAIN MENU")
    print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Start Trading Bot")
    print(f"{Fore.WHITE}2. View Current Position")
    print(f"{Fore.WHITE}3. View Strategy Status")
    print(f"{Fore.WHITE}4. View Account Balance")
    print(f"{Fore.WHITE}5. View Configuration")
    print(f"{Fore.WHITE}6. View Trade History")
    print(f"{Fore.WHITE}7. Test API Connection")
    print(f"{Fore.WHITE}8. Emergency Stop All")
    print(f"{Fore.WHITE}9. Exit{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─'*60}{Style.RESET_ALL}")


def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Gate.io MA Trading Bot')
    parser.add_argument('--start', action='store_true', help='Start trading bot directly without menu')
    parser.add_argument('--status', action='store_true', help='Show strategy status and exit')
    parser.add_argument('--balance', action='store_true', help='Show account balance and exit')
    args = parser.parse_args()
    
    print_header()
    
    # Initialize bot
    try:
        bot = TradingBot()
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to initialize bot: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please check your .env configuration{Style.RESET_ALL}")
        return
    
    # Handle command line arguments
    if args.start:
        # Start bot directly
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"START TRADING BOT")
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Bot akan:{Style.RESET_ALL}")
        print(f"  • Monitor market setiap {bot.config['timeframe']}")
        print(f"  • Cari entry signal (EMA crossover + RSI + ADX + Volume)")
        print(f"  • Execute trade {'(SIMULASI SAJA)' if bot.config['dry_run'] else '(REAL TRADE)'}")
        print(f"  • Manage position dengan trailing stop & take profit")
        
        is_testnet = bot.config.get('use_testnet', False)
        mode_label = "[TESTNET]" if is_testnet else "[MAINNET - LIVE]"
        mode_color = Fore.YELLOW if is_testnet else Fore.RED
        trading_mode = "DRY RUN (Simulation)" if bot.config['dry_run'] else "LIVE TRADING"
        
        print(f"\n{Fore.GREEN}Symbol:{Style.RESET_ALL} {bot.config['trading_pair']}")
        print(f"{Fore.GREEN}Timeframe:{Style.RESET_ALL} {bot.config['timeframe']}")
        print(f"{Fore.GREEN}Mode:{Style.RESET_ALL} {trading_mode} {mode_color}{mode_label}{Style.RESET_ALL}")
        print(f"\n{Fore.GREEN}Starting bot... Tekan Ctrl+C untuk stop.{Style.RESET_ALL}\n")
        bot.start()
        return
    
    if args.status:
        # Show status and exit
        print(f"\n{Fore.YELLOW}Fetching market data...{Style.RESET_ALL}")
        if bot.fetch_market_data():
            print(f"{Fore.YELLOW}Fetching live price...{Style.RESET_ALL}")
            live_price = bot.get_live_price()
            if live_price:
                print(f"{Fore.GREEN}Live price fetched: ${live_price:.4f}{Style.RESET_ALL}")
            status = bot.strategy.get_strategy_status(bot.df, live_price)
            print(bot.strategy.format_status_for_display(status))
        else:
            print(f"{Fore.RED}Failed to fetch market data{Style.RESET_ALL}")
        return
    
    if args.balance:
        # Show balance and exit
        bot.view_balance()
        return
    
    while True:
        print_menu()
        choice = input(f"\n{Fore.GREEN}Select option (1-9): {Style.RESET_ALL}").strip()
        
        if choice == '1':
            # Start bot
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"START TRADING BOT")
            print(f"{'='*60}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Bot akan:{Style.RESET_ALL}")
            print(f"  • Monitor market setiap {bot.config['timeframe']}")
            print(f"  • Cari entry signal (EMA crossover + RSI + ADX + Volume)")
            print(f"  • Execute trade {'(SIMULASI SAJA)' if bot.config['dry_run'] else '(REAL TRADE)'}")
            print(f"  • Manage position dengan trailing stop & take profit")
            
            # Show testnet/mainnet mode
            is_testnet = bot.config.get('use_testnet', False)
            mode_label = "[TESTNET]" if is_testnet else "[MAINNET - LIVE]"
            mode_color = Fore.YELLOW if is_testnet else Fore.RED
            trading_mode = "DRY RUN (Simulation)" if bot.config['dry_run'] else "LIVE TRADING"
            
            print(f"\n{Fore.GREEN}Symbol:{Style.RESET_ALL} {bot.config['trading_pair']}")
            print(f"{Fore.GREEN}Timeframe:{Style.RESET_ALL} {bot.config['timeframe']}")
            print(f"{Fore.GREEN}Mode:{Style.RESET_ALL} {trading_mode} {mode_color}{mode_label}{Style.RESET_ALL}")
            
            confirm = input(f"\n{Fore.YELLOW}Mulai bot? (yes/no): {Style.RESET_ALL}").lower()
            if confirm == 'yes':
                print(f"\n{Fore.GREEN}Bot started! Tekan Ctrl+C untuk stop.{Style.RESET_ALL}\n")
                bot.start()
            else:
                print(f"{Fore.YELLOW}Cancelled{Style.RESET_ALL}")
        
        elif choice == '2':
            # View position
            if bot.current_position:
                current_price = bot.df.iloc[-1]['close'] if bot.df is not None else 0
                print(bot.risk_manager.format_position_for_display(bot.current_position, current_price))
            else:
                print(f"\n{Fore.YELLOW}No open position{Style.RESET_ALL}")
        
        elif choice == '3':
            # View strategy status
            print(f"\n{Fore.YELLOW}Fetching market data...{Style.RESET_ALL}")
            if bot.fetch_market_data():
                # Get live price for accurate status
                print(f"{Fore.YELLOW}Fetching live price...{Style.RESET_ALL}")
                live_price = bot.get_live_price()
                if live_price:
                    print(f"{Fore.GREEN}Live price fetched: ${live_price:.4f}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Warning: Could not fetch live price{Style.RESET_ALL}")
                status = bot.strategy.get_strategy_status(bot.df, live_price)
                print(bot.strategy.format_status_for_display(status))
            else:
                print(f"{Fore.RED}Failed to fetch market data{Style.RESET_ALL}")
        
        elif choice == '4':
            # View balance
            print(f"\n{Fore.YELLOW}Fetching account balance...{Style.RESET_ALL}")
            if bot.update_equity():
                print(f"\n{Fore.GREEN}Total Equity (USDT): {bot.equity:.2f}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to fetch balance{Style.RESET_ALL}")
        
        elif choice == '5':
            # View configuration
            mode = "[TESTNET]" if bot.config.get('use_testnet', False) else "[MAINNET - LIVE]"
            mode_color = Fore.YELLOW if bot.config.get('use_testnet', False) else Fore.RED
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"CONFIGURATION")
            print(f"{'='*60}{Style.RESET_ALL}")
            print(f"Exchange: Gate.io {mode_color}{mode}{Style.RESET_ALL}")
            print(f"Trading Pair: {bot.config['trading_pair']}")
            print(f"Timeframe: {bot.config['timeframe']}")
            print(f"EMA: {bot.config['ema_short']}/{bot.config['ema_long']}")
            print(f"RSI: {bot.config['rsi_length']} (range: {bot.config['rsi_min']}-{bot.config['rsi_max']})")
            print(f"ADX Threshold: {bot.config['adx_threshold']}")
            print(f"Max USDT per Trade: {bot.config['max_usdt_per_trade']:.2f} USDT")
            print(f"Entry Split: Entry 1 ({bot.config['entry_1_percent']}%) | Entry 2 ({bot.config['entry_2_percent']}%)")
            print(f"SL ATR Multiplier: {bot.config['sl_atr_multiplier']}")
            print(f"TP1: {bot.config['tp1_rr']}R ({bot.config['tp1_percent']}%)")
            print(f"TP2: {bot.config['tp2_rr']}R ({bot.config['tp2_percent']}%)")
            print(f"Mode: {'DRY RUN' if bot.config['dry_run'] else 'LIVE'}")
        
        elif choice == '6':
            # View trade history
            if bot.trade_history:
                print(f"\n{Fore.CYAN}{'='*60}")
                print(f"TRADE HISTORY ({len(bot.trade_history)} trades)")
                print(f"{'='*60}{Style.RESET_ALL}")
                
                for i, trade in enumerate(bot.trade_history[-10:], 1):  # Show last 10
                    pnl_color = Fore.GREEN if trade['pnl'] >= 0 else Fore.RED
                    print(f"{i}. {trade['side'].upper()} | Entry: {trade['entry_price']:.4f} | "
                          f"Exit: {trade['exit_price']:.4f} | "
                          f"{pnl_color}PnL: {trade['pnl']:.4f} ({trade['pnl_percent']:.2f}%){Style.RESET_ALL} | "
                          f"Reason: {trade['reason']}")
            else:
                print(f"\n{Fore.YELLOW}No trade history{Style.RESET_ALL}")
        
        elif choice == '7':
            # Test API connection
            print(f"\n{Fore.YELLOW}Testing Gate.io API connection...{Style.RESET_ALL}")
            try:
                if bot.api.test_connection():
                    print(f"{Fore.GREEN}✓ API connection successful{Style.RESET_ALL}")
                    if bot.api.test_auth():
                        print(f"{Fore.GREEN}✓ Authentication successful{Style.RESET_ALL}")
                        price = bot.api.get_last_price(bot.config['trading_pair'])
                        print(f"{Fore.GREEN}Current price: {price:.4f}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}✗ Authentication failed{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ API connection failed{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ API test failed: {e}{Style.RESET_ALL}")
        
        elif choice == '8':
            # Emergency stop
            print(f"\n{Fore.RED}{'='*60}")
            print(f"EMERGENCY STOP")
            print(f"{'='*60}{Style.RESET_ALL}")
            confirm = input(f"{Fore.RED}Close all positions and stop bot? (yes/no): {Style.RESET_ALL}").lower()
            if confirm == 'yes':
                bot.stop()
                print(f"{Fore.GREEN}✓ All operations stopped{Style.RESET_ALL}")
        
        elif choice == '9':
            # Exit
            print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
            if bot.is_running:
                bot.stop()
            print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
            break
        
        else:
            print(f"{Fore.RED}Invalid option. Please select 1-9.{Style.RESET_ALL}")
        
        input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program interrupted by user{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
        sys.exit(1)
