"""
BitMart API Client
Wrapper for BitMart Spot API v1
Documentation: https://developer-pro.bitmart.com/en/spot/
"""

import requests
import hmac
import hashlib
import time
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class BitMartAPI:
    """BitMart Spot API Client"""
    
    def __init__(self, api_key: str, secret_key: str, memo: str, testnet: bool = False):
        """
        Initialize BitMart API client
        
        Args:
            api_key: BitMart API key
            secret_key: BitMart secret key
            memo: BitMart memo
            testnet: Use testnet (not supported by BitMart, kept for compatibility)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.memo = memo
        self.base_url = "https://api-cloud.bitmart.com"
        self.session = requests.Session()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.2  # 200ms between requests (max 5 req/sec)
        
    def _generate_signature(self, timestamp: str, body: str) -> str:
        """Generate HMAC SHA256 signature"""
        message = f"{timestamp}#{self.memo}#{body}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self, method: str = "GET", body: str = "") -> Dict:
        """Get request headers with signature"""
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, body)
        
        headers = {
            "Content-Type": "application/json",
            "X-BM-KEY": self.api_key,
            "X-BM-SIGN": signature,
            "X-BM-TIMESTAMP": timestamp
        }
        return headers
    
    def _rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                 data: Optional[Dict] = None, signed: bool = False, max_retries: int = 3) -> Dict:
        """
        Make HTTP request to BitMart API with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body
            signed: Whether request requires signature
            max_retries: Maximum number of retries for rate limit errors
            
        Returns:
            API response as dict
        """
        url = f"{self.base_url}{endpoint}"
        
        if signed:
            body = json.dumps(data) if data else ""
            headers = self._get_headers(method, body)
        else:
            headers = {"Content-Type": "application/json"}
            body = None
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                self._rate_limit()
                
                if method == "GET":
                    response = self.session.get(url, params=params, headers=headers, timeout=10)
                elif method == "POST":
                    response = self.session.post(url, json=data, headers=headers, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Handle rate limit (429)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit, waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} retries")
                
                response.raise_for_status()
                result = response.json()
                
                # Check BitMart API response code
                if result.get("code") != 1000:
                    # BitMart uses 'msg' or 'message' for error messages
                    error_msg = result.get('message') or result.get('msg', 'Unknown error')
                    raise Exception(f"BitMart API Error: Code={result.get('code')}, Message={error_msg}, Data={result.get('data')}")
                
                return result
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1 and "429" in str(e):
                    # Retry on rate limit
                    wait_time = 2 ** attempt
                    print(f"Rate limit error, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Request failed: {str(e)}")
        
        raise Exception(f"Request failed after {max_retries} retries")
    
    # ==================== Public Market Data ====================
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker information for a symbol
        
        Args:
            symbol: Trading pair (e.g., BTC_USDT)
            
        Returns:
            Ticker data
        """
        endpoint = "/spot/v1/ticker"
        params = {"symbol": symbol}
        return self._request("GET", endpoint, params=params)
    
    def get_kline(self, symbol: str, from_time: int, to_time: int, step: int = 60) -> Dict:
        """
        Get candlestick/kline data using V3 API
        
        Args:
            symbol: Trading pair (e.g., BTC_USDT)
            from_time: Start time (unix timestamp in seconds)
            to_time: End time (unix timestamp in seconds)
            step: Kline step (1, 5, 15, 30, 60, 120, 240, 1440, 10080, 43200)
                  1=1min, 60=1hour, 240=4hour, 1440=1day
                  
        Returns:
            Kline data
        """
        endpoint = "/spot/quotation/v3/klines"
        params = {
            "symbol": symbol,
            "before": to_time,
            "after": from_time,
            "step": step,
            "limit": 200
        }
        return self._request("GET", endpoint, params=params)
    
    def get_symbols_details(self) -> Dict:
        """Get all trading pairs details"""
        endpoint = "/spot/v1/symbols/details"
        return self._request("GET", endpoint)
    
    def get_symbol_detail(self, symbol: str) -> Optional[Dict]:
        """
        Get specific symbol details
        
        Args:
            symbol: Trading pair (e.g., BTC_USDT)
            
        Returns:
            Symbol details or None if not found
        """
        result = self.get_symbols_details()
        symbols = result.get("data", {}).get("symbols", [])
        
        for sym in symbols:
            if sym.get("symbol") == symbol:
                return sym
        return None
    
    # ==================== Account & Wallet ====================
    
    def get_wallet_balance(self) -> Dict:
        """Get spot wallet balance"""
        endpoint = "/spot/v1/wallet"
        return self._request("GET", endpoint, signed=True)
    
    def get_account_balance(self, currency: Optional[str] = None) -> Dict:
        """
        Get account balance
        
        Args:
            currency: Specific currency (optional, e.g., BTC, USDT)
            
        Returns:
            Account balance
        """
        endpoint = "/account/v1/wallet"
        params = {"currency": currency} if currency else None
        return self._request("GET", endpoint, params=params, signed=True)
    
    # ==================== Trading ====================
    
    def place_order(self, symbol: str, side: str, type: str, size: str, 
                    price: Optional[str] = None, client_order_id: Optional[str] = None) -> Dict:
        """
        Place a new order
        
        Args:
            symbol: Trading pair (e.g., BTC_USDT)
            side: Order side (buy, sell)
            type: Order type (limit, market, limit_maker, ioc)
            size: Order size (quantity)
            price: Order price (required for limit orders)
            client_order_id: Custom order ID
            
        Returns:
            Order result
        """
        endpoint = "/spot/v2/submit_order"
        
        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "size": size
        }
        
        if price:
            data["price"] = price
        if client_order_id:
            data["client_order_id"] = client_order_id
        
        return self._request("POST", endpoint, data=data, signed=True)
    
    def cancel_order(self, symbol: str, order_id: Optional[str] = None, 
                     client_order_id: Optional[str] = None) -> Dict:
        """
        Cancel an order
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            client_order_id: Client order ID
            
        Returns:
            Cancellation result
        """
        endpoint = "/spot/v3/cancel_order"
        
        data = {"symbol": symbol}
        if order_id:
            data["order_id"] = order_id
        if client_order_id:
            data["client_order_id"] = client_order_id
        
        return self._request("POST", endpoint, data=data, signed=True)
    
    def get_order_detail(self, symbol: str, order_id: str) -> Dict:
        """
        Get order details
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            
        Returns:
            Order details
        """
        endpoint = "/spot/v2/order_detail"
        params = {
            "symbol": symbol,
            "order_id": order_id
        }
        return self._request("GET", endpoint, params=params, signed=True)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> Dict:
        """
        Get all open orders
        
        Args:
            symbol: Trading pair (optional, get all if not specified)
            
        Returns:
            List of open orders
        """
        endpoint = "/spot/v2/orders"
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return self._request("GET", endpoint, params=params, signed=True)
    
    def get_order_history(self, symbol: str, offset: int = 1, limit: int = 100) -> Dict:
        """
        Get order history
        
        Args:
            symbol: Trading pair
            offset: Page number (starts from 1)
            limit: Number of results (max 100)
            
        Returns:
            Order history
        """
        endpoint = "/spot/v2/orders"
        params = {
            "symbol": symbol,
            "offset": offset,
            "limit": limit,
            "status": "6"  # 6 = all orders
        }
        return self._request("GET", endpoint, params=params, signed=True)
    
    # ==================== Helper Methods ====================
    
    def get_current_price(self, symbol: str) -> float:
        """
        Get current market price
        
        Args:
            symbol: Trading pair
            
        Returns:
            Current price as float
        """
        ticker = self.get_ticker(symbol)
        data = ticker.get("data", {})
        tickers = data.get("tickers", [])
        if tickers:
            return float(tickers[0].get("last_price", 0))
        return 0.0
    
    def get_balance_for_asset(self, asset: str) -> Tuple[float, float]:
        """
        Get available and frozen balance for specific asset
        
        Args:
            asset: Asset symbol (e.g., BTC, USDT)
            
        Returns:
            Tuple of (available, frozen) balance
        """
        try:
            wallet = self.get_wallet_balance()
            currencies = wallet.get("data", {}).get("wallet", [])
            
            for currency in currencies:
                if currency.get("id") == asset:
                    available = float(currency.get("available", 0))
                    frozen = float(currency.get("frozen", 0))
                    return available, frozen
            
            return 0.0, 0.0
            
        except Exception as e:
            print(f"Error getting balance for {asset}: {e}")
            return 0.0, 0.0
    
    def check_order_status(self, symbol: str, order_id: str) -> str:
        """
        Check order status
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            
        Returns:
            Order status (filled, partially_filled, cancelled, pending, failed)
        """
        try:
            order = self.get_order_detail(symbol, order_id)
            status_map = {
                "1": "pending",
                "2": "partially_filled",
                "3": "filled",
                "4": "cancelled",
                "5": "partially_cancelled",
                "6": "failed"
            }
            status_code = order.get("data", {}).get("status", "0")
            return status_map.get(status_code, "unknown")
        except Exception as e:
            print(f"Error checking order status: {e}")
            return "error"
    
    def calculate_quantity(self, symbol: str, usdt_amount: float, price: float) -> float:
        """
        Calculate quantity based on USDT amount and price
        
        Args:
            symbol: Trading pair
            usdt_amount: Amount in USDT
            price: Current price
            
        Returns:
            Calculated quantity
        """
        symbol_info = self.get_symbol_detail(symbol)
        if not symbol_info:
            return 0.0
        
        # Get precision
        base_precision = int(symbol_info.get("base_min_size", "0.00000001").split('.')[-1].rstrip('0').__len__())
        quantity = usdt_amount / price
        
        # Round to precision
        quantity = round(quantity, base_precision)
        return quantity
    
    def format_price(self, symbol: str, price: float) -> str:
        """
        Format price according to symbol precision
        
        Args:
            symbol: Trading pair
            price: Price value
            
        Returns:
            Formatted price string
        """
        symbol_info = self.get_symbol_detail(symbol)
        if not symbol_info:
            return str(price)
        
        quote_increment = symbol_info.get("quote_increment", "0.01")
        precision = len(quote_increment.split('.')[-1].rstrip('0'))
        
        return f"{price:.{precision}f}"
    
    def format_quantity(self, symbol: str, quantity: float) -> str:
        """
        Format quantity according to symbol precision
        
        Args:
            symbol: Trading pair
            quantity: Quantity value
            
        Returns:
            Formatted quantity string
        """
        symbol_info = self.get_symbol_detail(symbol)
        if not symbol_info:
            return str(quantity)
        
        base_min_size = symbol_info.get("base_min_size", "0.00000001")
        precision = len(base_min_size.split('.')[-1].rstrip('0'))
        
        return f"{quantity:.{precision}f}"


if __name__ == "__main__":
    # Test code
    print("BitMart API Client initialized")
    print("Use this module by importing: from bitmart_api import BitMartAPI")
