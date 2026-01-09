"""
Quick Gate.io API Setup Verification
Run this script to verify your Gate.io API configuration
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_variable(var_name, required=True):
    """Check if environment variable exists and is not empty"""
    value = os.getenv(var_name)
    
    if value is None or value == "":
        status = "❌ MISSING"
        if required:
            return False, status
        else:
            return True, "⚠️  OPTIONAL (not set)"
    elif value == "your_gate_api_key_here" or value == "your_gate_api_secret_here":
        status = "⚠️  PLACEHOLDER (needs to be replaced)"
        return False, status
    else:
        # Mask sensitive data
        if "KEY" in var_name or "SECRET" in var_name:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            status = f"✅ SET ({masked})"
        else:
            status = f"✅ SET ({value})"
        return True, status


def main():
    """Main verification function"""
    print("="*80)
    print("Gate.io API Setup Verification")
    print("="*80)
    print()
    
    # Check environment files
    print("Checking configuration files...")
    env_file = Path(".env")
    config_env_file = Path("config.env")
    
    if env_file.exists():
        print(f"✅ .env file found")
    else:
        print(f"⚠️  .env file not found (optional)")
    
    if config_env_file.exists():
        print(f"✅ config.env file found")
    else:
        print(f"⚠️  config.env file not found (optional)")
    
    print()
    
    # Check required variables
    print("Checking environment variables...")
    print("-"*80)
    
    all_good = True
    
    # Required variables
    required_vars = [
        ("GATE_API_KEY", True),
        ("GATE_API_SECRET", True),
    ]
    
    # Optional variables
    optional_vars = [
        ("USE_TESTNET", False),
        ("GATE_ACCOUNT", False),
    ]
    
    print("\nRequired Variables:")
    for var_name, required in required_vars:
        success, status = check_env_variable(var_name, required)
        print(f"  {var_name:<25} {status}")
        if not success:
            all_good = False
    
    print("\nOptional Variables:")
    for var_name, required in optional_vars:
        success, status = check_env_variable(var_name, required)
        print(f"  {var_name:<25} {status}")
    
    print()
    print("-"*80)
    
    # Check if gate_api.py exists
    gate_api_file = Path("gate_api.py")
    if not gate_api_file.exists():
        print("\n❌ gate_api.py not found!")
        all_good = False
    
    # Final result
    print()
    print("="*80)
    if all_good:
        print("✅ Configuration looks good!")
        print()
        print("Next steps:")
        print("  1. Run: python gate_api_example.py")
        print("  2. Test your API connection and authentication")
        print("  3. If successful, you can start using Gate.io API")
    else:
        print("❌ Configuration incomplete!")
        print()
        print("Action required:")
        print("  1. Edit .env file and add your Gate.io API credentials")
        print("  2. Get API keys from: https://www.gate.io/myaccount/api_key_manage")
        print("  3. Replace 'your_gate_api_key_here' with actual API key")
        print("  4. Replace 'your_gate_api_secret_here' with actual API secret")
        print("  5. Start with USE_TESTNET=1 for testing")
        print()
        print("Example .env configuration:")
        print("-"*80)
        print("GATE_API_KEY=abc123def456...")
        print("GATE_API_SECRET=xyz789uvw012...")
        print("USE_TESTNET=1")
        print("GATE_ACCOUNT=spot")
        print("-"*80)
    
    print("="*80)
    print()
    
    # Try to import gate_api
    if all_good:
        try:
            print("Testing gate_api module import...")
            from gate_api import GateAPI
            print("✅ gate_api module imported successfully")
            
            # Try to initialize (will fail if credentials are wrong, but that's ok)
            print("\nInitializing Gate.io API client...")
            api = GateAPI(
                api_key=os.getenv("GATE_API_KEY"),
                secret_key=os.getenv("GATE_API_SECRET"),
                testnet=os.getenv("USE_TESTNET", "1") == "1"
            )
            print("✅ API client initialized")
            
            print("\n🎉 Everything is ready!")
            print("   Run: python gate_api_example.py")
            
        except ImportError as e:
            print(f"❌ Failed to import gate_api: {e}")
            print("   Make sure gate_api.py is in the same folder")
        except Exception as e:
            print(f"⚠️  API initialization warning: {e}")
            print("   This might be normal if credentials are placeholders")
    
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
