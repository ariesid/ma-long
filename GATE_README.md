# Gate.io API Integration

This folder contains Gate.io API integration for cryptocurrency trading.

## Files Overview

### Core Files

- **`gate_api.py`** - Main Gate.io API client wrapper
- **`gate_grid_bot.py`** - Advanced grid trading bot with interactive menu
- **`gate_api_example.py`** - Simple example demonstrating API usage

### Configuration Files

- **`.env`** - Main environment configuration (includes both BitMart and Gate.io)
- **`config.env`** - Gate.io grid bot specific configuration

## Quick Start

### 1. Install Dependencies

```bash
pip install requests python-dotenv
```

### 2. Configure API Credentials

Edit `.env` file and add your Gate.io API credentials:

```env
# Gate.io API Configuration
GATE_API_KEY=your_gate_api_key_here
GATE_API_SECRET=your_gate_api_secret_here
USE_TESTNET=1
GATE_ACCOUNT=spot
```

**Important:**

- Set `USE_TESTNET=1` for testing (recommended)
- Set `USE_TESTNET=0` for live trading (use with caution!)

### 3. Test Connection

Run the example script to test your API connection:

```bash
python gate_api_example.py
```

This will test:

- ✅ Connection to Gate.io
- ✅ API authentication
- ✅ Market data retrieval
- ✅ Account balance access
- ✅ Open orders listing

## Usage Examples

### Basic Market Data

```python
from gate_api import GateAPI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize API
api = GateAPI(
    api_key=os.getenv("GATE_API_KEY"),
    secret_key=os.getenv("GATE_API_SECRET"),
    testnet=True  # Use testnet
)

# Get last price
price = api.get_last_price("BTC_USDT")
print(f"BTC/USDT: ${price:,.2f}")

# Get ticker
ticker = api.get_ticker("BTC_USDT")
print(f"24h High: ${float(ticker['high_24h']):,.2f}")
print(f"24h Low: ${float(ticker['low_24h']):,.2f}")
```

### Account Balance

```python
# Get all balances
accounts = api.get_spot_accounts()
for acc in accounts:
    if float(acc['available']) > 0:
        print(f"{acc['currency']}: {acc['available']}")

# Get specific currency
usdt = api.get_balance("USDT")
print(f"USDT Available: {usdt['available']}")
```

### Place Orders

```python
# Create limit order
order = api.create_limit_order(
    symbol="BTC_USDT",
    side="buy",
    price=50000.0,
    amount=0.001,
    time_in_force="gtc"  # Good till cancelled
)
print(f"Order ID: {order['id']}")

# Create market order
order = api.create_market_order(
    symbol="BTC_USDT",
    side="buy",
    amount=0.001
)

# List open orders
orders = api.list_open_orders("BTC_USDT")
for order in orders:
    print(f"{order['side']} {order['amount']} @ {order['price']}")

# Cancel order
api.cancel_order(order_id="12345", symbol="BTC_USDT")

# Cancel all orders
api.cancel_all_orders(symbol="BTC_USDT")
```

### Get Historical Data

```python
# Get candlestick data
klines = api.get_klines(
    symbol="BTC_USDT",
    interval="1h",  # 10s, 1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 7d, 30d
    limit=100
)

for candle in klines[:5]:
    timestamp, volume, close, high, low, open_price, amount = candle
    print(f"Time: {timestamp} | Open: {open_price} | Close: {close}")
```

## Grid Bot Usage

The advanced grid trading bot (`gate_grid_bot.py`) can be run in two modes:

### Interactive Menu Mode (Recommended)

```bash
python gate_grid_bot.py
```

Features:

- 🚀 Start/Stop bot in background
- 📊 Live monitoring dashboard
- 💰 Check balances and orders
- 📈 Profit calculator
- ⛔ Emergency stop (cancel all)

### CLI Mode

```bash
# Start bot
python gate_grid_bot.py start

# Monitor live
python gate_grid_bot.py monitor

# Check orders
python gate_grid_bot.py orders

# Check balance
python gate_grid_bot.py balance

# Calculate profit
python gate_grid_bot.py profit

# Emergency stop
python gate_grid_bot.py stop
```

### Grid Bot Configuration

Edit `config.env`:

```env
# Trading Symbol
SYMBOL=BTC_USDT

# Auto Range Mode (recommended for beginners)
AUTO_RANGE_PERCENT=5  # ±5% from current price

# Manual Range Mode (comment out AUTO_RANGE_PERCENT)
# LOWER=55000
# UPPER=65000

# Grid Settings
GRIDS=20              # Number of grid levels
QUOTE_PER_ORDER=50    # USDT per order
GEOMETRIC=0           # 0=arithmetic, 1=geometric spacing
POLL=5                # Polling interval in seconds
```

## API Reference

### GateAPI Class

#### Public Methods (No Authentication Required)

- `get_ticker(symbol)` - Get ticker data
- `get_last_price(symbol)` - Get last traded price
- `get_orderbook(symbol, limit)` - Get order book
- `get_klines(symbol, interval, limit)` - Get candlestick data
- `get_pair_detail(symbol)` - Get trading pair details
- `get_server_time()` - Get server timestamp
- `test_connection()` - Test API connection

#### Private Methods (Authentication Required)

- `get_spot_accounts(currency)` - Get account balances
- `get_balance(currency)` - Get specific currency balance
- `create_limit_order(...)` - Create limit order
- `create_market_order(...)` - Create market order
- `list_open_orders(symbol)` - List open orders
- `get_order(order_id, symbol)` - Get order details
- `cancel_order(order_id, symbol)` - Cancel single order
- `cancel_all_orders(symbol)` - Cancel all orders
- `get_my_trades(symbol, limit)` - Get trade history
- `test_auth()` - Test authentication

## Symbol Format

Gate.io uses underscore format for trading pairs:

- `BTC_USDT` (not BTC/USDT or BTCUSDT)
- `ETH_USDT`
- `PUMP_USDT`

Use the helper method:

```python
symbol = api.format_symbol("BTC", "USDT")  # Returns "BTC_USDT"
```

## Rate Limits

The API client includes automatic rate limiting:

- Default: 100ms between requests
- Automatic retry on 429 (rate limit) errors
- Exponential backoff: 1s, 2s, 4s

## Error Handling

```python
try:
    price = api.get_last_price("BTC_USDT")
except Exception as e:
    print(f"Error: {e}")
```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use .env files** and add them to `.gitignore`
3. **Start with testnet** before going live
4. **Use IP whitelist** on Gate.io dashboard
5. **Enable 2FA** on your Gate.io account
6. **Set API permissions** carefully (read-only for testing)
7. **Monitor bot activity** regularly

## Getting API Keys

1. Go to [Gate.io](https://www.gate.io) and log in
2. Navigate to: Account → API Management
3. Create new API key with required permissions
4. For testnet: Use [Gate.io Testnet](https://www.gate.io/testnet)

### Recommended Permissions

- ✅ Spot Trading
- ✅ Read Balance
- ⚠️ Withdrawal (NOT recommended for bots)

## Troubleshooting

### Authentication Failed

- Check API key and secret are correct
- Verify API key has spot trading permissions
- Ensure system time is synchronized

### Connection Timeout

- Check internet connection
- Verify firewall settings
- Try different network

### Order Rejected

- Check minimum order amounts
- Verify sufficient balance
- Ensure price is within limits

### Rate Limit Error

- The client handles this automatically
- If persistent, increase `min_request_interval`

## Support

For issues or questions:

1. Check Gate.io API documentation: https://www.gate.io/docs/developers/apiv4/
2. Review example files in this folder
3. Test with `gate_api_example.py` first

## License

This code is provided as-is for educational purposes.

## Disclaimer

⚠️ **Trading cryptocurrencies carries risk. This software is provided for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses.**

---

Happy trading! 🚀
