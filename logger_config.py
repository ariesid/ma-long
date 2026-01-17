"""
Logging Configuration
Setup logging for trading bot activity and trade execution
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class BotLogger:
    """Trading bot logger with separate files for trades and errors"""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        """
        Initialize logger
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Convert string log level to logging constant
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        self.log_level = level_map.get(log_level.upper(), logging.INFO)
        
        # Create loggers
        self.trade_logger = self._setup_logger("trade", "trading")
        self.error_logger = self._setup_logger("error", "errors")
        self.bot_logger = self._setup_logger("bot", "bot")
        self.strategy_logger = self._setup_logger("strategy", "strategy")
    
    def _setup_logger(self, name: str, file_prefix: str) -> logging.Logger:
        """
        Setup individual logger with file and console handlers
        
        Args:
            name: Logger name
            file_prefix: Prefix for log file
            
        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler
        log_file = self.log_dir / f"{file_prefix}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    # ==================== Trade Logging ====================
    
    def log_trade_entry(self, symbol: str, side: str, entry_price: float, 
                       size: float, stop_loss: float, take_profits: dict):
        """Log trade entry"""
        msg = (
            f"ENTRY | {symbol} | {side.upper()} | "
            f"Price: {entry_price:.4f} | Size: {size:.6f} | "
            f"SL: {stop_loss:.4f} | TP1: {take_profits.get('tp1', 0):.4f} | "
            f"TP2: {take_profits.get('tp2', 0):.4f}"
        )
        self.trade_logger.info(msg)
    
    def log_trade_exit(self, symbol: str, side: str, exit_price: float, 
                      size: float, pnl: float, reason: str):
        """Log trade exit"""
        pnl_sign = "+" if pnl >= 0 else ""
        msg = (
            f"EXIT | {symbol} | {side.upper()} | "
            f"Price: {exit_price:.4f} | Size: {size:.6f} | "
            f"PnL: {pnl_sign}{pnl:.4f} | Reason: {reason}"
        )
        self.trade_logger.info(msg)
    
    def log_partial_exit(self, symbol: str, side: str, exit_price: float, 
                        size: float, reason: str):
        """Log partial position exit"""
        msg = (
            f"PARTIAL EXIT | {symbol} | {side.upper()} | "
            f"Price: {exit_price:.4f} | Size: {size:.6f} | Reason: {reason}"
        )
        self.trade_logger.info(msg)
    
    def log_stop_loss_update(self, symbol: str, old_sl: float, new_sl: float, reason: str):
        """Log stop loss update"""
        msg = (
            f"SL UPDATE | {symbol} | "
            f"Old: {old_sl:.4f} -> New: {new_sl:.4f} | Reason: {reason}"
        )
        self.trade_logger.info(msg)
    
    def log_signal(self, symbol: str, signal_type: str, details: dict):
        """Log trading signal"""
        msg = f"SIGNAL | {symbol} | {signal_type} | {details}"
        self.trade_logger.info(msg)
    
    # ==================== Bot Activity Logging ====================
    
    def log_bot_start(self, config: dict):
        """Log bot startup"""
        msg = f"Bot started with config: {config}"
        self.bot_logger.info(msg)
    
    def log_bot_stop(self, reason: str = "User requested"):
        """Log bot shutdown"""
        msg = f"Bot stopped: {reason}"
        self.bot_logger.info(msg)
    
    def log_api_call(self, endpoint: str, status: str):
        """Log API call"""
        msg = f"API | {endpoint} | Status: {status}"
        self.bot_logger.debug(msg)
    
    def log_market_data_update(self, symbol: str, price: float, indicators: dict):
        """Log market data update"""
        msg = (
            f"MARKET | {symbol} | Price: {price:.4f} | "
            f"RSI: {indicators.get('rsi', 0):.1f} | "
            f"ADX: {indicators.get('adx', 0):.1f}"
        )
        self.bot_logger.debug(msg)
    
    def log_balance_update(self, asset: str, available: float, frozen: float):
        """Log balance update"""
        msg = f"BALANCE | {asset} | Available: {available:.4f} | Frozen: {frozen:.4f}"
        self.bot_logger.info(msg)
    
    # ==================== Error Logging ====================
    
    def log_error(self, error_type: str, message: str, details: str = ""):
        """Log error"""
        msg = f"{error_type} | {message}"
        if details:
            msg += f" | Details: {details}"
        self.error_logger.error(msg)
    
    def log_api_error(self, endpoint: str, error: Exception):
        """Log API error"""
        msg = f"API ERROR | {endpoint} | {str(error)}"
        self.error_logger.error(msg)
    
    def log_order_error(self, symbol: str, side: str, error: Exception):
        """Log order placement error"""
        msg = f"ORDER ERROR | {symbol} | {side} | {str(error)}"
        self.error_logger.error(msg)
    
    def log_exception(self, exception: Exception, context: str = ""):
        """Log exception with traceback"""
        msg = f"EXCEPTION | {context} | {str(exception)}"
        self.error_logger.exception(msg)
    
    # ==================== Info Logging ====================
    
    def info(self, message: str):
        """Log info message"""
        self.bot_logger.info(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.bot_logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.bot_logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.error_logger.error(message)
    
    # ==================== Performance Logging ====================
    
    def log_performance_summary(self, stats: dict):
        """Log trading performance summary"""
        msg = (
            f"\n{'='*60}\n"
            f"PERFORMANCE SUMMARY\n"
            f"{'='*60}\n"
            f"Total Trades: {stats.get('total_trades', 0)}\n"
            f"Wins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}\n"
            f"Win Rate: {stats.get('win_rate', 0):.2f}%\n"
            f"Total PnL: {stats.get('total_pnl', 0):.4f}\n"
            f"Average Win: {stats.get('avg_win', 0):.4f}\n"
            f"Average Loss: {stats.get('avg_loss', 0):.4f}\n"
            f"Best Trade: {stats.get('best_trade', 0):.4f}\n"
            f"Worst Trade: {stats.get('worst_trade', 0):.4f}\n"
            f"Average R:R: {stats.get('avg_rr', 0):.2f}\n"
            f"{'='*60}"
        )
        self.trade_logger.info(msg)
    
    def log_daily_summary(self, date: str, stats: dict):
        """Log daily trading summary"""
        msg = (
            f"\nDAILY SUMMARY - {date}\n"
            f"Trades: {stats.get('trades', 0)} | "
            f"PnL: {stats.get('pnl', 0):.4f} | "
            f"Win Rate: {stats.get('win_rate', 0):.2f}%"
        )
        self.trade_logger.info(msg)


def setup_logger(log_dir: str = "logs", log_level: str = "INFO") -> BotLogger:
    """
    Setup and return bot logger instance
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        
    Returns:
        BotLogger instance
    """
    return BotLogger(log_dir, log_level)


if __name__ == "__main__":
    # Test logger
    logger = setup_logger(log_level="DEBUG")
    
    logger.info("Logger test started")
    logger.log_bot_start({"symbol": "BTC_USDT", "timeframe": "1H"})
    
    logger.log_trade_entry(
        symbol="BTC_USDT",
        side="long",
        entry_price=50000,
        size=0.01,
        stop_loss=49000,
        take_profits={"tp1": 51000, "tp2": 52000}
    )
    
    logger.log_trade_exit(
        symbol="BTC_USDT",
        side="long",
        exit_price=51000,
        size=0.01,
        pnl=10.0,
        reason="TP1 hit"
    )
    
    logger.log_performance_summary({
        'total_trades': 10,
        'wins': 6,
        'losses': 4,
        'win_rate': 60.0,
        'total_pnl': 150.0,
        'avg_win': 35.0,
        'avg_loss': -15.0,
        'best_trade': 50.0,
        'worst_trade': -25.0,
        'avg_rr': 1.8
    })
    
    print("\nLogger test completed. Check 'logs' directory for output.")
