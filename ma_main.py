"""
BitMart Trading Bot - MA Method 2
Main script with Interactive Terminal UI
"""

import os
import sys
import time
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
from bitmart_api import BitMartAPI
from indicators import Indicators
from strategy import TradingStrategy
from risk_manager import RiskManager
from logger_config import setup_logger

# Load environment variables
load_dotenv()


class TradingBot:
    """Main Trading Bot Class"""
    
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
        
        # Initialize API
        self.api = BitMartAPI(
            api_key=self.config['api_key'],
            secret_key=self.config['secret_key'],
            memo=self.config['memo']
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
        config = {
            # API credentials
            'api_key': os.getenv('BITMART_API_KEY', ''),
            'secret_key': os.getenv('BITMART_SECRET_KEY', ''),
            'memo': os.getenv('BITMART_MEMO', ''),
            
            # Trading settings
            'trading_pair': os.getenv('TRADING_PAIR', 'BTC_USDT'),
            'timeframe': os.getenv('TIMEFRAME', '1H'),
            
            # Strategy parameters
            'ema_short': int(os.getenv('EMA_SHORT', 9)),
            'ema_long': int(os.getenv('EMA_LONG', 21)),
            'rsi_length': int(os.getenv('RSI_LENGTH', 14)),
            'rsi_min': float(os.getenv('RSI_MIN', 40)),
            'rsi_max': float(os.getenv('RSI_MAX', 70)),
            'adx_period': int(os.getenv('ADX_PERIOD', 14)),
            'adx_threshold': float(os.getenv('ADX_THRESHOLD', 25)),
            'atr_period': int(os.getenv('ATR_PERIOD', 14)),
            
            # Risk management
            'max_usdt_per_trade': float(os.getenv('MAX_USDT_PER_TRADE', 100)),
            'entry_1_percent': float(os.getenv('ENTRY_1_PERCENT', 30)),
            'entry_2_percent': float(os.getenv('ENTRY_2_PERCENT', 70)),
            'sl_atr_multiplier': float(os.getenv('STOP_LOSS_ATR_MULTIPLIER', 1.5)),
            'trailing_atr_multiplier': float(os.getenv('TRAILING_STOP_ATR_MULTIPLIER', 1.0)),
            'tp1_rr': float(os.getenv('TP1_RR', 1.0)),
            'tp1_percent': float(os.getenv('TP1_PERCENT', 30)),
            'tp2_rr': float(os.getenv('TP2_RR', 2.0)),
            'tp2_percent': float(os.getenv('TP2_PERCENT', 40)),
            'max_candles_hold': int(os.getenv('MAX_CANDLES_HOLD', 20)),
            
            # Bot settings
            'dry_run': os.getenv('DRY_RUN', 'true').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            
            # Volume filter
            'use_volume_filter': True,
            'volume_ma_period': 20
        }
        
        return config
    
    def _print_startup_info(self):
        """Print clean startup information"""
        print(f"{Fore.CYAN}{'='*60}")
        print(f"BitMart Trading Bot - MA Method 2")
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⚠️  SPOT TRADING - LONG ONLY (BUY & SELL){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    Tidak ada SHORT SELLING atau LEVERAGE{Style.RESET_ALL}\n")
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
            '1m': 60, '3m': 180, '5m': 300, '15m': 900, '30m': 1800,
            '1H': 3600, '2H': 7200, '4H': 14400,
            '1D': 86400, '1W': 604800, '1M': 2592000
        }
        return timeframe_map.get(self.config['timeframe'], 3600)
    
    def _get_bitmart_step(self) -> int:
        """Convert timeframe to BitMart step parameter"""
        step_map = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1H': 60, '2H': 120, '4H': 240,
            '1D': 1440, '1W': 10080, '1M': 43200
        }
        return step_map.get(self.config['timeframe'], 60)
    
    def fetch_market_data(self, limit: int = 200) -> bool:
        """
        Fetch market data from BitMart
        
        Args:
            limit: Number of candles to fetch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = self.config['trading_pair']
            step = self._get_bitmart_step()
            
            # Calculate time range
            now = int(time.time())
            timeframe_seconds = self._get_timeframe_seconds()
            from_time = now - (limit * timeframe_seconds)
            
            # Fetch kline data
            response = self.api.get_kline(symbol, from_time, now, step)
            
            if response.get('code') != 1000:
                error_msg = response.get('message') or response.get('msg', 'Unknown error')
                self.logger.error(f"Failed to fetch market data: {error_msg}")
                return False
            
            # Parse kline data - V3 API returns data as array directly
            klines = response.get('data', [])
            
            if not klines:
                self.logger.error("No kline data received")
                return False
            
            # Convert to DataFrame
            # V3 API format: [timestamp, open, high, low, close, volume, quote_volume]
            df_data = []
            for kline in klines:
                df_data.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
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
            # Use existing get_current_price() method which correctly parses ticker response
            live_price = self.api.get_current_price(symbol)
            
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
            # Get USDT balance
            available, frozen = self.api.get_balance_for_asset('USDT')
            self.equity = available + frozen
            
            self.logger.log_balance_update('USDT', available, frozen)
            return True
            
        except Exception as e:
            self.logger.log_exception(e, "update_equity")
            return False
    
    def check_entry_signal(self):
        """Check for entry signals and execute trade (SPOT LONG ONLY)"""
        if self.current_position is not None:
            return  # Already in position
        
        # Check long entry (SPOT BUY only, not futures short)
        # Get live current price for accurate decision
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
            
            # Get symbol info for formatting
            symbol_info = self.api.get_symbol_detail(symbol)
            if not symbol_info:
                self.logger.error(f"Could not get symbol info for {symbol}")
                return
            
            # Execute Entry 1
            size_1_str = self.api.format_quantity(symbol, entry_1['position_size'])
            price_1_str = self.api.format_price(symbol, entry_1['price'])
            
            result_1 = self.api.place_order(
                symbol=symbol,
                side='buy' if side == 'long' else 'sell',
                type='limit',
                size=size_1_str,
                price=price_1_str
            )
            
            if result_1.get('code') == 1000:
                order_id_1 = result_1.get('data', {}).get('order_id')
                print(f"{Fore.GREEN}✓ Entry 1 placed: {entry_1['position_size']:.6f} @ {entry_1['price']:.4f} ({self.config['entry_1_percent']}%){Style.RESET_ALL}")
                
                # Execute Entry 2
                size_2_str = self.api.format_quantity(symbol, entry_2['position_size'])
                price_2_str = self.api.format_price(symbol, entry_2['price'])
                
                result_2 = self.api.place_order(
                    symbol=symbol,
                    side='buy' if side == 'long' else 'sell',
                    type='limit',
                    size=size_2_str,
                    price=price_2_str
                )
                
                if result_2.get('code') == 1000:
                    order_id_2 = result_2.get('data', {}).get('order_id')
                    print(f"{Fore.GREEN}✓ Entry 2 placed: {entry_2['position_size']:.6f} @ {entry_2['price']:.4f} ({self.config['entry_2_percent']}%){Style.RESET_ALL}")
                    
                    # Store position details
                    self.current_position = {
                        'side': side,
                        'entry_time': datetime.now(),
                        'entry_1': {
                            'order_id': order_id_1,
                            'price': entry_1['price'],
                            'size': entry_1['position_size'],
                            'stop_loss': entry_1['stop_loss'],
                            'take_profit': entry_1['take_profit']
                        },
                        'entry_2': {
                            'order_id': order_id_2,
                            'price': entry_2['price'],
                            'size': entry_2['position_size'],
                            'stop_loss': entry_2['stop_loss'],
                            'take_profit': entry_2['take_profit']
                        }
                    }
                    
                    # Calculate weighted average entry price
                    total_size = entry_1['position_size'] + entry_2['position_size']
                    if total_size > 0:
                        avg_entry = (entry_1['price'] * entry_1['position_size'] + entry_2['price'] * entry_2['position_size']) / total_size
                    else:
                        avg_entry = (entry_1['price'] + entry_2['price']) / 2
                    
                    self.logger.log_trade_entry(
                        symbol=symbol,
                        side=side,
                        entry_price=avg_entry,
                        size=total_size,
                        stop_loss=entry_1['stop_loss'],
                        take_profits={'tp1': entry_1['take_profit'], 'tp2': entry_2['take_profit']}
                    )
                else:
                    self.logger.log_order_error(symbol, side, Exception(result_2.get('message')))
            else:
                self.logger.log_order_error(symbol, side, Exception(result_1.get('message')))
                
        except Exception as e:
            self.logger.log_exception(e, "execute_entry")
    
    def simulate_entry(self, side: str, details: Dict):
        """Simulate entry trade (DRY RUN mode) with 2 entries"""
        try:
            # Check if entry details are available
            if 'entry_1' not in details or 'entry_2' not in details:
                self.logger.error("Entry details not available in signal")
                return
            
            entry_1 = details['entry_1']
            entry_2 = details['entry_2']
            
            # Store simulated position
            self.current_position = {
                'side': side,
                'entry_time': datetime.now(),
                'simulated': True,
                'entry_1': {
                    'price': entry_1['price'],
                    'size': entry_1['position_size'],
                    'stop_loss': entry_1['stop_loss'],
                    'take_profit': entry_1['take_profit']
                },
                'entry_2': {
                    'price': entry_2['price'],
                    'size': entry_2['position_size'],
                    'stop_loss': entry_2['stop_loss'],
                    'take_profit': entry_2['take_profit']
                }
            }
            
            # Calculate weighted average entry price
            total_size = entry_1['position_size'] + entry_2['position_size']
            if total_size > 0:
                avg_entry = (entry_1['price'] * entry_1['position_size'] + entry_2['price'] * entry_2['position_size']) / total_size
            else:
                avg_entry = (entry_1['price'] + entry_2['price']) / 2
            
            self.logger.log_trade_entry(
                symbol=self.config['trading_pair'],
                side=side,
                entry_price=avg_entry,
                size=total_size,
                stop_loss=entry_1['stop_loss'],
                take_profits={'tp1': entry_1['take_profit'], 'tp2': entry_2['take_profit']}
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
            print(f"{Fore.GREEN}✓ TP1 hit at {current_price:.4f}")
            self.logger.log_partial_exit(
                self.config['trading_pair'],
                self.current_position['side'],
                current_price,
                self.current_position['position_size'] * (self.current_position.get('tp1_percent', 30) / 100),
                "TP1"
            )
        elif action == "tp2":
            print(f"{Fore.GREEN}✓ TP2 hit at {current_price:.4f}")
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
            print(f"{pnl_color}✓ Position closed: {reason} | PnL: {pnl_info['pnl']:.4f} ({pnl_info['pnl_percent']:.2f}%)")
            
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
        print(f"{Fore.GREEN}{'='*60}\n")
        
        update_interval = self._get_timeframe_seconds()
        
        while self.is_running:
            try:
                self.run_once()
                
                # Wait for next candle
                print(f"\nWaiting for next update... (Press Ctrl+C to stop)")
                time.sleep(update_interval)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Bot stopped by user")
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
        print(f"{Fore.YELLOW}Bot stopped")
    
    def screen_all_assets(self):
        """Screen all BitMart USDT pairs for trading signals"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"ASSET SCREENING - MA METHOD 2 STRATEGY")
        print(f"{'='*80}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Fetching all USDT trading pairs...{Style.RESET_ALL}")
        
        try:
            # Get all trading pairs
            result = self.api.get_symbols_details()
            if not result or result.get('code') != 1000:
                print(f"{Fore.RED}✗ Failed to fetch trading pairs: {result.get('message') if result else 'No response'}")
                return
            
            symbols = result.get('data', {}).get('symbols', [])
            
            # Filter only USDT pairs and active symbols
            usdt_pairs = [
                s for s in symbols 
                if s.get('quote_currency') == 'USDT' 
                and s.get('trade_status') == 'trading'
            ]
            
            if not usdt_pairs:
                print(f"{Fore.RED}✗ No USDT trading pairs found")
                return
            
            print(f"{Fore.GREEN}✓ Found {len(usdt_pairs)} USDT trading pairs")
            
            # Optional: Limit scanning for testing (remove in production)
            # Uncomment below to scan only first 50 pairs for quick test:
            # usdt_pairs = usdt_pairs[:50]
            # print(f"{Fore.YELLOW}[TEST MODE] Limiting to first 50 pairs{Style.RESET_ALL}")
            
            total = len(usdt_pairs)
            estimated_time = (total * 0.2) / 60  # ~0.2s per pair with rate limiting
            print(f"{Fore.YELLOW}Scanning {total} pairs... (Estimated time: ~{estimated_time:.1f} minutes)")
            print(f"{Fore.YELLOW}Rate limiting: 200ms per request to avoid API errors{Style.RESET_ALL}")
            
            # Results storage
            signals_yes = []
            signals_no = []
            errors = []
            
            # Progress tracking
            start_time = time.time()
            
            for idx, symbol_info in enumerate(usdt_pairs, 1):
                symbol = symbol_info.get('symbol')
                
                # Progress indicator every 10 symbols
                if idx % 10 == 0 or idx == 1:
                    elapsed = time.time() - start_time
                    if idx > 1:
                        avg_time_per_pair = elapsed / idx
                        remaining = (total - idx) * avg_time_per_pair
                        eta_min = remaining / 60
                        print(f"{Fore.CYAN}Progress: {idx}/{total} ({(idx/total*100):.1f}%) | "
                              f"Signals: {len(signals_yes)} | ETA: {eta_min:.1f}m{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}Progress: {idx}/{total} ({(idx/total*100):.1f}%){Style.RESET_ALL}")
                
                try:
                    # Calculate time range for klines
                    now = int(time.time())
                    timeframe_seconds = self._get_timeframe_seconds()
                    from_time = now - (200 * timeframe_seconds)  # 200 candles back
                    
                    # Fetch klines with rate limiting handled by API
                    response = self.api.get_kline(
                        symbol=symbol,
                        from_time=from_time,
                        to_time=now,
                        step=self._get_bitmart_step()
                    )
                    
                    # Parse response
                    if not response or response.get('code') != 1000:
                        errors.append(f"{symbol}: API error - {response.get('message', 'Unknown')}")
                        continue
                    
                    klines = response.get('data', [])
                    
                    if not klines or len(klines) < 50:
                        errors.append(f"{symbol}: Insufficient data (got {len(klines) if klines else 0} candles)")
                        continue
                    
                    # Convert to DataFrame
                    # V3 API format: [timestamp, open, high, low, close, volume, quote_volume]
                    df_data = []
                    for kline in klines:
                        df_data.append({
                            'timestamp': int(kline[0]),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    
                    df = pd.DataFrame(df_data)
                    
                    # Remove any NaN or zero values that might cause issues
                    if df[['open', 'high', 'low', 'close']].isnull().any().any():
                        errors.append(f"{symbol}: Invalid price data (NaN values)")
                        continue
                    
                    # Calculate indicators using Indicators module
                    df = Indicators.calculate_all_indicators(
                        df,
                        ema_short=self.config['ema_short'],
                        ema_long=self.config['ema_long'],
                        rsi_period=self.config['rsi_length'],
                        atr_period=self.config['atr_period'],
                        adx_period=self.config['adx_period'],
                        volume_ma_period=20
                    )
                    
                    # Validate indicators (check for NaN in last row)
                    last_row = df.iloc[-1]
                    required_indicators = ['ema_short', 'ema_long', 'rsi', 'adx', 'atr']
                    if any(pd.isna(last_row[ind]) for ind in required_indicators):
                        errors.append(f"{symbol}: Incomplete indicators (NaN)")
                        continue
                    
                    # Check signal using strategy (returns tuple: bool, dict)
                    signal, details = self.strategy.check_long_entry(df)
                    
                    current_price = df.iloc[-1]['close']
                    
                    result = {
                        'symbol': symbol,
                        'price': current_price,
                        'ema_short': df.iloc[-1]['ema_short'],
                        'ema_long': df.iloc[-1]['ema_long'],
                        'rsi': df.iloc[-1]['rsi'],
                        'adx': df.iloc[-1]['adx'],
                        'volume': df.iloc[-1]['volume'],
                        'volume_ma': df.iloc[-1].get('volume_ma', 0),
                        'signal': signal,
                        'reason': details.get('reason', '')
                    }
                    
                    if signal:
                        signals_yes.append(result)
                    else:
                        signals_no.append(result)
                
                except Exception as e:
                    errors.append(f"{symbol}: {str(e)[:50]}")
                    continue
            
            # Display results
            elapsed_total = time.time() - start_time
            print(f"\n{Fore.CYAN}{'='*80}")
            print(f"SCREENING RESULTS (Completed in {elapsed_total/60:.1f} minutes)")
            print(f"{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Total Scanned: {total}")
            print(f"{Fore.GREEN}Signal YES: {len(signals_yes)} ({len(signals_yes)/total*100:.1f}%)")
            print(f"{Fore.YELLOW}Signal NO: {len(signals_no)} ({len(signals_no)/total*100:.1f}%)")
            print(f"{Fore.RED}Errors: {len(errors)} ({len(errors)/total*100:.1f}%)")
            
            # Display assets with signal YES
            if signals_yes:
                print(f"\n{Fore.GREEN}{'='*90}")
                print(f"ASSETS WITH SIGNAL YES ({len(signals_yes)} pairs)")
                print(f"{'='*90}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'Symbol':<15} {'Price':<14} {'RSI':<8} {'ADX':<8} {'Volume/MA':<12} {'EMA':<10}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'-'*90}{Style.RESET_ALL}")
                
                for result in signals_yes:
                    ema_status = "Bullish" if result['ema_short'] > result['ema_long'] else "Bearish"
                    vol_ratio = result['volume'] / result['volume_ma'] if result['volume_ma'] > 0 else 0
                    print(f"{Fore.WHITE}{result['symbol']:<15} "
                          f"{result['price']:<14.8f} "
                          f"{result['rsi']:<8.2f} "
                          f"{result['adx']:<8.2f} "
                          f"{vol_ratio:<12.2f} "
                          f"{Fore.GREEN}{ema_status:<10}{Style.RESET_ALL}")
                
                print(f"\n{Fore.CYAN}Note: Volume/MA ratio shows volume strength (>1.0 = above average){Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}No assets with signal YES found")
                print(f"{Fore.YELLOW}Tip: Try during volatile market conditions or different timeframe{Style.RESET_ALL}")
            
            # Show first 10 errors if any
            if errors:
                print(f"\n{Fore.RED}{'='*80}")
                print(f"ERRORS (showing first 10 of {len(errors)})")
                print(f"{'='*80}{Style.RESET_ALL}")
                for error in errors[:10]:
                    print(f"{Fore.RED}  • {error}")
            
            print(f"\n{Fore.GREEN}✓ Screening complete!")
            
        except Exception as e:
            print(f"{Fore.RED}✗ Screening failed: {e}")
            self.logger.error(f"Asset screening error: {e}")


def print_header():
    """Print bot header"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}║{' '*58}║")
    print(f"{Fore.CYAN}║{' '*10}BitMart Trading Bot - MA Method 2{' '*16}║")
    print(f"{Fore.CYAN}║{' '*58}║")
    print(f"{Fore.CYAN}{'='*60}\n")


def print_menu():
    """Print main menu"""
    print(f"\n{Fore.CYAN}{'─'*60}")
    print(f"{Fore.CYAN}MAIN MENU")
    print(f"{Fore.CYAN}{'─'*60}")
    print(f"{Fore.WHITE}1. Start Trading Bot")
    print(f"{Fore.WHITE}2. View Current Position")
    print(f"{Fore.WHITE}3. View Strategy Status")
    print(f"{Fore.WHITE}4. View Account Balance")
    print(f"{Fore.WHITE}5. View Configuration")
    print(f"{Fore.WHITE}6. View Trade History")
    print(f"{Fore.WHITE}7. Test API Connection")
    print(f"{Fore.WHITE}8. Emergency Stop All")
    print(f"{Fore.WHITE}9. Screen All Assets (Find Signal YES)")
    print(f"{Fore.WHITE}10. Exit")
    print(f"{Fore.CYAN}{'─'*60}")


def main():
    """Main function"""
    print_header()
    
    # Initialize bot
    try:
        bot = TradingBot()
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to initialize bot: {e}")
        print(f"{Fore.YELLOW}Please check your .env configuration")
        return
    
    while True:
        print_menu()
        choice = input(f"\n{Fore.GREEN}Select option (1-10): {Style.RESET_ALL}").strip()
        
        if choice == '1':
            # Start bot - Monitoring loop yang akan:
            # 1. Fetch market data setiap interval
            # 2. Calculate indicators (EMA, RSI, ADX, ATR)
            # 3. Check entry signals (LONG jika kondisi terpenuhi)
            # 4. Manage position (trailing stop, take profit)
            # 5. Check exit signals
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"START TRADING BOT")
            print(f"{'='*60}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Bot akan:{Style.RESET_ALL}")
            print(f"  • Monitor market setiap {bot.config['timeframe']}")
            print(f"  • Cari entry signal (EMA crossover + RSI + ADX + Volume)")
            print(f"  • Execute trade {'(SIMULASI SAJA)' if bot.config['dry_run'] else '(REAL TRADE)'}")
            print(f"  • Manage position dengan trailing stop & take profit")
            print(f"\n{Fore.GREEN}Symbol:{Style.RESET_ALL} {bot.config['trading_pair']}")
            print(f"{Fore.GREEN}Timeframe:{Style.RESET_ALL} {bot.config['timeframe']}")
            print(f"{Fore.GREEN}Mode:{Style.RESET_ALL} {'DRY RUN (Simulation)' if bot.config['dry_run'] else 'LIVE TRADING'}")
            
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
                print(f"\n{Fore.YELLOW}No open position")
        
        elif choice == '3':
            # View strategy status
            print(f"\n{Fore.YELLOW}Fetching market data...")
            if bot.fetch_market_data():
                # Get live price for accurate status
                print(f"{Fore.YELLOW}Fetching live price...")
                live_price = bot.get_live_price()
                if live_price:
                    print(f"{Fore.GREEN}Live price fetched: ${live_price:.4f}")
                else:
                    print(f"{Fore.YELLOW}Warning: Could not fetch live price, using candle close price only")
                status = bot.strategy.get_strategy_status(bot.df, live_price)
                print(bot.strategy.format_status_for_display(status))
            else:
                print(f"{Fore.RED}Failed to fetch market data")
        
        elif choice == '4':
            # View balance
            print(f"\n{Fore.YELLOW}Fetching account balance...")
            if bot.update_equity():
                print(f"\n{Fore.GREEN}Total Equity (USDT): {bot.equity:.2f}")
            else:
                print(f"{Fore.RED}Failed to fetch balance")
        
        elif choice == '5':
            # View configuration
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"CONFIGURATION")
            print(f"{'='*60}")
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
                print(f"{'='*60}")
                
                for i, trade in enumerate(bot.trade_history[-10:], 1):  # Show last 10
                    pnl_color = Fore.GREEN if trade['pnl'] >= 0 else Fore.RED
                    print(f"{i}. {trade['side'].upper()} | Entry: {trade['entry_price']:.4f} | "
                          f"Exit: {trade['exit_price']:.4f} | "
                          f"{pnl_color}PnL: {trade['pnl']:.4f} ({trade['pnl_percent']:.2f}%){Style.RESET_ALL} | "
                          f"Reason: {trade['reason']}")
            else:
                print(f"\n{Fore.YELLOW}No trade history")
        
        elif choice == '7':
            # Test API connection
            print(f"\n{Fore.YELLOW}Testing API connection...")
            try:
                ticker = bot.api.get_ticker(bot.config['trading_pair'])
                if ticker.get('code') == 1000:
                    print(f"{Fore.GREEN}✓ API connection successful")
                    price = bot.api.get_current_price(bot.config['trading_pair'])
                    print(f"{Fore.GREEN}Current price: {price:.4f}")
                else:
                    print(f"{Fore.RED}✗ API error: {ticker.get('message')}")
            except Exception as e:
                print(f"{Fore.RED}✗ API connection failed: {e}")
        
        elif choice == '8':
            # Emergency stop
            print(f"\n{Fore.RED}{'='*60}")
            print(f"EMERGENCY STOP")
            print(f"{'='*60}")
            confirm = input(f"{Fore.RED}Close all positions and stop bot? (yes/no): {Style.RESET_ALL}").lower()
            if confirm == 'yes':
                bot.stop()
                print(f"{Fore.GREEN}✓ All operations stopped")
        
        elif choice == '9':
            # Screen all assets
            print(f"\n{Fore.CYAN}{'='*60}")
            print(f"ASSET SCREENING")
            print(f"{'='*60}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Bot akan scan SEMUA trading pairs USDT di BitMart:{Style.RESET_ALL}")
            print(f"  • Fetch market data untuk setiap pair")
            print(f"  • Calculate indicators (EMA, RSI, ADX)")
            print(f"  • Check entry signal dengan strategy MA Method 2")
            print(f"  • Tampilkan pairs dengan signal YES")
            print(f"\n{Fore.YELLOW}⚠️  Proses ini memerlukan waktu beberapa menit (rate limiting){Style.RESET_ALL}")
            
            confirm = input(f"\n{Fore.GREEN}Mulai screening? (yes/no): {Style.RESET_ALL}").lower()
            if confirm == 'yes':
                bot.screen_all_assets()
            else:
                print(f"{Fore.YELLOW}Cancelled{Style.RESET_ALL}")
        
        elif choice == '10':
            # Exit
            print(f"\n{Fore.YELLOW}Exiting...")
            if bot.is_running:
                bot.stop()
            print(f"{Fore.GREEN}Goodbye!")
            break
        
        else:
            print(f"{Fore.RED}Invalid option. Please select 1-10.")
        
        input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Fatal error: {e}")
        sys.exit(1)
