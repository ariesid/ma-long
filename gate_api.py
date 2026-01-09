"""
Gate.io API Client
Wrapper for Gate.io Spot API v4
Documentation: https://www.gate.io/docs/developers/apiv4/
"""

import requests
import hmac
import hashlib
import time
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class GateAPI:
    """Gate.io Spot API Client"""
    
    def __init__(self, api_key: str, secret_key: str, testnet: bool = False):
        """
        Initialize Gate.io API client
        
        Args:
            api_key: Gate.io API key
            secret_key: Gate.io secret key
            testnet: Use testnet (True) or mainnet (False)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://api-testnet.gateapi.io" if testnet else "https://api.gateio.ws"
        self.prefix = "/api/v4"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
    def _sha512_hex(self, s: str) -> str:
        """Generate SHA512 hash"""
        return hashlib.sha512((s or "").encode("utf-8")).hexdigest()
    
    def _sign_headers(self, method: str, url_path: str, query_str: str, body_str: str) -> Dict:
        """
        Generate signature headers for authenticated requests
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            url_path: API endpoint path
            query_str: Query string
            body_str: Request body as string
            
        Returns:
            Headers dict with KEY, Timestamp, and SIGN
        """
        ts = str(int(time.time()))
        sign_str = f"{method}\n{self.prefix}{url_path}\n{query_str}\n{self._sha512_hex(body_str)}\n{ts}"
        sign = hmac.new(
            self.secret_key.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()
        
        return {
            "KEY": self.api_key,
            "Timestamp": ts,
            "SIGN": sign
        }
    
    def _rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _request(self, method: str, url_path: str, params: Optional[Dict] = None,
                 body: Optional[Dict] = None, auth: bool = False, max_retries: int = 3) -> Dict:
        """
        Make HTTP request to Gate.io API with retry logic
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            url_path: API endpoint path
            params: Query parameters
            body: Request body
            auth: Whether request requires authentication
            max_retries: Maximum number of retries
            
        Returns:
            API response as dict or list
        """
        # Build query string
        query_str = ""
        if params:
            query_str = "&".join(f"{k}={v}" for k, v in params.items())
        
        # Build body string
        body_str = json.dumps(body) if body else ""
        
        # Add authentication headers if needed
        headers = {}
        if auth:
            headers = self._sign_headers(method, url_path, query_str, body_str)
        
        # Build full URL
        url = f"{self.base_url}{self.prefix}{url_path}"
        if query_str:
            url += f"?{query_str}"
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                self._rate_limit()
                
                if method == "GET":
                    response = self.session.get(url, headers=headers, timeout=15)
                elif method == "POST":
                    response = self.session.post(url, headers=headers, data=body_str if body else None, timeout=15)
                elif method == "DELETE":
                    response = self.session.delete(url, headers=headers, timeout=15)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Handle rate limit (429)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit, waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} retries")
                
                # Handle errors
                if response.status_code >= 400:
                    raise RuntimeError(f"{response.status_code} | {response.text}")
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Request error, waiting {wait_time}s before retry...")
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
            symbol: Trading pair (e.g., 'BTC_USDT')
            
        Returns:
            Ticker data including last price, volume, etc.
        """
        data = self._request("GET", "/spot/tickers", params={"currency_pair": symbol})
        if not data:
            raise RuntimeError("Tickers empty")
        return data[0]
    
    def get_last_price(self, symbol: str) -> float:
        """
        Get last price for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            
        Returns:
            Last traded price
        """
        ticker = self.get_ticker(symbol)
        return float(ticker["last"])
    
    def get_orderbook(self, symbol: str, limit: int = 10) -> Dict:
        """
        Get order book for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            limit: Number of entries (default 10, max 100)
            
        Returns:
            Order book with bids and asks
        """
        params = {"currency_pair": symbol, "limit": limit}
        return self._request("GET", "/spot/order_book", params=params)
    
    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100,
                   from_time: Optional[int] = None, to_time: Optional[int] = None) -> List[List]:
        """
        Get candlestick/kline data
        
        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            interval: Time interval (10s, 1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 7d, 30d)
            limit: Number of candlesticks (max 1000)
            from_time: Start timestamp in seconds
            to_time: End timestamp in seconds
            
        Returns:
            List of candlesticks [timestamp, volume, close, high, low, open, amount]
        """
        params = {"currency_pair": symbol, "interval": interval, "limit": limit}
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        
        return self._request("GET", "/spot/candlesticks", params=params)
    
    def get_pair_detail(self, symbol: str) -> Dict:
        """
        Get trading pair details (precision, limits, etc.)
        
        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            
        Returns:
            Pair details including precision, min/max amounts
        """
        return self._request("GET", f"/spot/currency_pairs/{symbol}")
    
    def get_server_time(self) -> int:
        """
        Get server timestamp
        
        Returns:
            Server timestamp in seconds
        """
        result = self._request("GET", "/spot/time")
        return int(result["server_time"])
    
    # ==================== Account & Balance ====================
    
    def get_spot_accounts(self, currency: Optional[str] = None) -> List[Dict]:
        """
        Get spot account balances
        
        Args:
            currency: Specific currency to query (optional)
            
        Returns:
            List of account balances
        """
        params = {}
        if currency:
            params["currency"] = currency
        
        return self._request("GET", "/spot/accounts", params=params, auth=True)
    
    def get_balance(self, currency: str) -> Dict:
        """
        Get balance for specific currency
        
        Args:
            currency: Currency symbol (e.g., 'USDT', 'BTC')
            
        Returns:
            Balance info with available and locked amounts
        """
        accounts = self.get_spot_accounts(currency)
        for acc in accounts:
            if acc.get('currency', '').upper() == currency.upper():
                return {
                    'currency': acc['currency'],
                    'available': float(acc.get('available', 0)),
                    'locked': float(acc.get('locked', 0)),
                    'total': float(acc.get('available', 0)) + float(acc.get('locked', 0))
                }
        return {'currency': currency, 'available': 0.0, 'locked': 0.0, 'total': 0.0}
    
    # ==================== Trading - Orders ====================
    
    def create_limit_order(self, symbol: str, side: str, price: float, amount: float,
                          time_in_force: str = "gtc", account: str = "spot",
                          text: Optional[str] = None) -> Dict:
        """
        Create a limit order
        
        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            side: 'buy' or 'sell'
            price: Order price
            amount: Order amount (in base currency)
            time_in_force: Time in force ('gtc', 'ioc', 'poc')
                          gtc: Good Till Cancelled
                          ioc: Immediate or Cancel
                          poc: Post Only (maker-only)
            account: Account type ('spot' or 'unified')
            text: Custom client order ID (must start with 't-')
            
        Returns:
            Order creation response
        """
        body = {
            "currency_pair": symbol,
            "type": "limit",
            "account": account,
            "side": side,
            "amount": str(amount),
            "price": str(price),
            "time_in_force": time_in_force
        }
        
        if text:
            body["text"] = text
        
        return self._request("POST", "/spot/orders", body=body, auth=True)
    
    def create_market_order(self, symbol: str, side: str, amount: float,
                           account: str = "spot", text: Optional[str] = None) -> Dict:
        """
        Create a market order
        
        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            side: 'buy' or 'sell'
            amount: Order amount (in base currency)
            account: Account type ('spot' or 'unified')
            text: Custom client order ID (must start with 't-')
            
        Returns:
            Order creation response
        """
        body = {
            "currency_pair": symbol,
            "type": "market",
            "account": account,
            "side": side,
            "amount": str(amount)
        }
        
        if text:
            body["text"] = text
        
        return self._request("POST", "/spot/orders", body=body, auth=True)
    
    def list_open_orders(self, symbol: Optional[str] = None, account: str = "spot") -> List[Dict]:
        """
        List all open orders
        
        Args:
            symbol: Trading pair (optional, filter by symbol)
            account: Account type ('spot' or 'unified')
            
        Returns:
            List of open orders
        """
        params = {"status": "open", "account": account}
        if symbol:
            params["currency_pair"] = symbol
        
        return self._request("GET", "/spot/orders", params=params, auth=True)
    
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Get order details
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            Order details
        """
        params = {"currency_pair": symbol}
        return self._request("GET", f"/spot/orders/{order_id}", params=params, auth=True)
    
    def cancel_order(self, order_id: str, symbol: str, account: str = "spot") -> Dict:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair
            account: Account type ('spot' or 'unified')
            
        Returns:
            Cancellation response
        """
        params = {"currency_pair": symbol, "account": account}
        return self._request("DELETE", f"/spot/orders/{order_id}", params=params, auth=True)
    
    def cancel_all_orders(self, symbol: str, account: str = "spot", side: Optional[str] = None) -> List[Dict]:
        """
        Cancel all open orders for a symbol
        
        Args:
            symbol: Trading pair
            account: Account type ('spot' or 'unified')
            side: Optional side filter ('buy' or 'sell')
            
        Returns:
            List of cancelled orders
        """
        params = {"currency_pair": symbol, "account": account}
        if side:
            params["side"] = side
        
        return self._request("DELETE", "/spot/orders", params=params, auth=True)
    
    # ==================== Trading History ====================
    
    def get_my_trades(self, symbol: str, limit: int = 100, 
                     from_id: Optional[int] = None, to_id: Optional[int] = None) -> List[Dict]:
        """
        Get personal trading history
        
        Args:
            symbol: Trading pair
            limit: Number of records (max 1000)
            from_id: Start trade ID
            to_id: End trade ID
            
        Returns:
            List of trades
        """
        params = {"currency_pair": symbol, "limit": limit}
        if from_id:
            params["from"] = from_id
        if to_id:
            params["to"] = to_id
        
        return self._request("GET", "/spot/my_trades", params=params, auth=True)
    
    def get_order_trades(self, order_id: str, symbol: str) -> List[Dict]:
        """
        Get trades for a specific order
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            List of trades for the order
        """
        params = {"currency_pair": symbol, "order_id": order_id}
        return self._request("GET", "/spot/my_trades", params=params, auth=True)
    
    # ==================== Helper Methods ====================
    
    def test_connection(self) -> bool:
        """
        Test API connection
        
        Returns:
            True if connection successful
        """
        try:
            self.get_server_time()
            return True
        except Exception:
            return False
    
    def test_auth(self) -> bool:
        """
        Test API authentication
        
        Returns:
            True if authentication successful
        """
        try:
            self.get_spot_accounts()
            return True
        except Exception:
            return False
    
    def format_symbol(self, base: str, quote: str) -> str:
        """
        Format symbol for Gate.io (BASE_QUOTE)
        
        Args:
            base: Base currency (e.g., 'BTC')
            quote: Quote currency (e.g., 'USDT')
            
        Returns:
            Formatted symbol (e.g., 'BTC_USDT')
        """
        return f"{base.upper()}_{quote.upper()}"


# ==================== Example Usage ====================
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize API
    api = GateAPI(
        api_key=os.getenv("GATE_API_KEY"),
        secret_key=os.getenv("GATE_API_SECRET"),
        testnet=os.getenv("USE_TESTNET", "1") == "1"
    )
    
    # Test connection
    print("Testing connection...")
    if api.test_connection():
        print("✓ Connection OK")
    else:
        print("✗ Connection failed")
    
    # Test authentication
    print("\nTesting authentication...")
    if api.test_auth():
        print("✓ Authentication OK")
    else:
        print("✗ Authentication failed")
    
    # Get ticker
    symbol = "BTC_USDT"
    print(f"\nGetting ticker for {symbol}...")
    try:
        ticker = api.get_ticker(symbol)
        print(f"Last Price: {ticker['last']}")
        print(f"24h High: {ticker['high_24h']}")
        print(f"24h Low: {ticker['low_24h']}")
        print(f"24h Volume: {ticker['base_volume']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Get balance (requires authentication)
    print("\nGetting balances...")
    try:
        balances = api.get_spot_accounts()
        for bal in balances:
            total = float(bal.get('available', 0)) + float(bal.get('locked', 0))
            if total > 0:
                print(f"{bal['currency']}: Available={bal['available']}, Locked={bal['locked']}")
    except Exception as e:
        print(f"Error: {e}")
