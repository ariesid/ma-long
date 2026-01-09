"""
Gate.io API Integration Example
Demonstrates how to use the Gate.io API client
"""

import os
from dotenv import load_dotenv
from gate_api import GateAPI

# Load environment variables
load_dotenv()


def main():
    """Main function demonstrating Gate.io API usage"""
    
    print("="*80)
    print("Gate.io API Integration Example")
    print("="*80)
    
    # Initialize Gate.io API
    api = GateAPI(
        api_key=os.getenv("GATE_API_KEY"),
        secret_key=os.getenv("GATE_API_SECRET"),
        testnet=os.getenv("USE_TESTNET", "1") == "1"
    )
    
    mode = "🧪 TESTNET" if os.getenv("USE_TESTNET", "1") == "1" else "🚀 MAINNET"
    print(f"\nMode: {mode}\n")
    
    # Test 1: Connection Test
    print("-"*80)
    print("Test 1: Connection Test")
    print("-"*80)
    try:
        if api.test_connection():
            print("✅ Connection successful!")
            server_time = api.get_server_time()
            print(f"Server time: {server_time}")
        else:
            print("❌ Connection failed!")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 2: Authentication Test
    print("\n" + "-"*80)
    print("Test 2: Authentication Test")
    print("-"*80)
    try:
        if api.test_auth():
            print("✅ Authentication successful!")
        else:
            print("❌ Authentication failed!")
            print("Please check your API credentials in .env file")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your API credentials in .env file")
        return
    
    # Test 3: Get Market Data
    print("\n" + "-"*80)
    print("Test 3: Get Market Data (Public)")
    print("-"*80)
    
    symbol = "BTC_USDT"
    
    try:
        # Get ticker
        print(f"\nGetting ticker for {symbol}...")
        ticker = api.get_ticker(symbol)
        print(f"✅ Last Price: ${float(ticker['last']):,.2f}")
        print(f"   24h High: ${float(ticker['high_24h']):,.2f}")
        print(f"   24h Low: ${float(ticker['low_24h']):,.2f}")
        print(f"   24h Volume: {float(ticker['base_volume']):,.2f} BTC")
        
        # Get order book
        print(f"\nGetting order book for {symbol}...")
        orderbook = api.get_orderbook(symbol, limit=5)
        print(f"✅ Top 5 Bids:")
        for bid in orderbook['bids'][:5]:
            print(f"   Price: ${float(bid[0]):,.2f} | Amount: {float(bid[1]):.4f}")
        print(f"   Top 5 Asks:")
        for ask in orderbook['asks'][:5]:
            print(f"   Price: ${float(ask[0]):,.2f} | Amount: {float(ask[1]):.4f}")
        
        # Get pair details
        print(f"\nGetting pair details for {symbol}...")
        pair = api.get_pair_detail(symbol)
        print(f"✅ Trading Pair Info:")
        print(f"   Base: {pair['base']} | Quote: {pair['quote']}")
        print(f"   Price Precision: {pair['precision']}")
        print(f"   Amount Precision: {pair['amount_precision']}")
        print(f"   Min Base Amount: {pair.get('min_base_amount', 'N/A')}")
        print(f"   Min Quote Amount: {pair.get('min_quote_amount', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Get Account Balance
    print("\n" + "-"*80)
    print("Test 4: Get Account Balance (Private)")
    print("-"*80)
    
    try:
        print("\nFetching spot account balances...")
        accounts = api.get_spot_accounts()
        
        print("✅ Account Balances:")
        has_balance = False
        for acc in accounts:
            available = float(acc.get('available', 0))
            locked = float(acc.get('locked', 0))
            total = available + locked
            
            if total > 0:
                has_balance = True
                print(f"   {acc['currency']:>8} | Available: {available:>15.8f} | Locked: {locked:>15.8f} | Total: {total:>15.8f}")
        
        if not has_balance:
            print("   No balance found (all balances are 0)")
        
        # Get specific currency balance
        print("\nFetching USDT balance...")
        usdt_bal = api.get_balance('USDT')
        print(f"✅ USDT Balance:")
        print(f"   Available: {usdt_bal['available']:.2f}")
        print(f"   Locked: {usdt_bal['locked']:.2f}")
        print(f"   Total: {usdt_bal['total']:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Get Open Orders
    print("\n" + "-"*80)
    print("Test 5: Get Open Orders (Private)")
    print("-"*80)
    
    try:
        print(f"\nFetching open orders for {symbol}...")
        orders = api.list_open_orders(symbol)
        
        if orders:
            print(f"✅ Found {len(orders)} open orders:")
            for order in orders:
                print(f"   ID: {order['id']} | {order['side'].upper()} | Price: {order['price']} | Amount: {order['amount']} | Status: {order['status']}")
        else:
            print("✅ No open orders")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)
    print("\n📖 Next Steps:")
    print("   1. Update API credentials in .env or config.env file")
    print("   2. Set USE_TESTNET=0 for mainnet trading")
    print("   3. Use gate_api.py in your trading bot")
    print("   4. Check gate_grid_bot.py for advanced grid bot example")
    print("\n")


if __name__ == "__main__":
    main()
