# Trading Flow Documentation

## Table of Contents

1. [Overview](#overview)
2. [Complete Trading Flow](#complete-trading-flow)
3. [Entry Process](#entry-process)
4. [Position Monitoring](#position-monitoring)
5. [Exit Mechanisms](#exit-mechanisms)
6. [Trailing Stop System](#trailing-stop-system)
7. [Position Persistence](#position-persistence)
8. [Risk Management](#risk-management)

---

## Overview

This bot uses a **Moving Average trend-following strategy** with multiple entry points and dynamic exit management. It monitors positions continuously and uses ATR-based risk management.

**Trading Pair**: SOL_USDT (or configured pair)  
**Timeframe**: 4H (configurable)  
**Position Type**: LONG only (can be extended to SHORT)

---

## Complete Trading Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    1. SIGNAL DETECTION                       │
│  Strategy checks: EMA alignment, RSI, ADX, Volume           │
│  Calculates: Entry 1 @ EMA Short, Entry 2 @ EMA Long       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    2. PLACE LIMIT ORDERS                     │
│  Entry 1: 70% @ EMA Short (e.g., 137.89)                   │
│  Entry 2: 30% @ EMA Long  (e.g., 137.21)                   │
│  Orders wait to be filled when price drops                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    3. ORDERS FILLED                          │
│  Price drops → Entry 1 filled @ 137.89                      │
│  Price drops → Entry 2 filled @ 137.21                      │
│  Weighted Average Entry: 137.41                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  4. POSITION CREATED                         │
│  Entry: 137.41                                              │
│  Stop Loss: 134.57 (Entry - 1.5 × ATR)                     │
│  TP1: 142.11 (1.0 R:R) → Exit 30%                          │
│  TP2: None (can be configured)                              │
│  Trailing Stop: Activated (Entry - 1.0 × ATR)              │
│  ★ Position saved to position_state.json                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              5. CONTINUOUS MONITORING                        │
│  Bot checks every update cycle (new candle):                │
│  - Current price vs Stop Loss                               │
│  - Current price vs TP1/TP2                                 │
│  - Update trailing stop                                     │
│  ★ Position state updated in position_state.json            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    6. EXIT TRIGGERED                         │
│  One of these conditions met:                               │
│  → Price hits TP1: Sell 30%, move SL to breakeven          │
│  → Price hits TP2: Sell 40%, keep trailing remainder       │
│  → Stop Loss hit: Exit entire position                      │
│  → Trailing Stop hit: Exit remaining position               │
│  ★ Position removed from position_state.json                │
└─────────────────────────────────────────────────────────────┘
```

---

## Entry Process

### 1. Signal Detection

**File**: `strategy.py` → `check_entry_signal()`

**Conditions** (all must be TRUE):

- ✓ EMA Short > EMA Long (uptrend)
- ✓ RSI: 40-75 (not oversold/overbought)
- ✓ ADX > 25 (strong trend)
- ✓ Volume > 1.5 × MA(20) (high activity)

**Output**:

```python
{
    'entry_1': {
        'price': 137.89,        # EMA Short
        'position_size': 0.251, # 70% allocation
        'stop_loss': 134.57,
        'take_profit': 142.11
    },
    'entry_2': {
        'price': 137.21,        # EMA Long
        'position_size': 0.108, # 30% allocation
        'stop_loss': 134.57,
        'take_profit': 142.50
    }
}
```

### 2. Order Placement

**File**: `gate_ma_main.py` → `execute_entry()`

**Type**: LIMIT orders (wait for price to reach)

```python
# Entry 1: Limit buy at EMA Short
api.create_limit_order(
    symbol='SOL_USDT',
    side='buy',
    price=137.89,
    amount=0.251
)

# Entry 2: Limit buy at EMA Long
api.create_limit_order(
    symbol='SOL_USDT',
    side='buy',
    price=137.21,
    amount=0.108
)
```

**Why Limit Orders?**

- Better entry prices (buy on dips)
- Avoid slippage
- Wait for confirmation of support

### 3. Position Creation

**File**: `gate_ma_main.py` → `execute_entry()`

Once both orders are filled:

```python
self.current_position = {
    'side': 'long',
    'entry_time': '2026-01-12 00:42:14',
    'entry_price': 137.41,          # Weighted average
    'stop_loss': 134.57,
    'position_size': 0.359,         # Total size
    'remaining_size': 0.359,        # Updated on partial exits
    'risk_amount': 49.28,           # USDT at risk
    'tp1': 142.11,
    'tp1_percent': 30,              # 30% of position
    'tp2': None,
    'tp2_percent': 0,
    'trailing_stop': 137.41,        # Starts at entry
    'order_ids': ['12345', '12346']
}
```

---

## Position Monitoring

### Update Cycle

**File**: `gate_ma_main.py` → `manage_position()`

**Frequency**: Every time new candle data is fetched (e.g., every 4H on 4H timeframe)

```python
def manage_position(self):
    # Get latest market price
    current_price = self.df.iloc[-1]['close']
    current_atr = self.df.iloc[-1]['atr']

    # Check all exit conditions
    updated_position, action = self.risk_manager.update_position(
        self.current_position,
        current_price,
        current_atr
    )

    # Save updated position
    self._save_position_state()

    # Execute action if triggered
    if action == "tp1":
        # Sell 30% of position at market
    elif action == "stop_loss":
        # Exit entire position
    elif action == "trailing_stop":
        # Exit remaining position
```

### What Gets Checked

**File**: `risk_manager.py` → `update_position()`

1. **Stop Loss**: `current_price <= stop_loss?`
2. **TP1**: `current_price >= tp1?`
3. **TP2**: `current_price >= tp2?`
4. **Trailing Stop**: Calculate and check dynamically

---

## Exit Mechanisms

### 1. Take Profit 1 (TP1)

**Trigger**: `current_price >= TP1`

**Configuration**:

```env
TP1_RR=1.0          # Risk:Reward ratio
TP1_PERCENT=30      # Exit 30% of position
```

**Calculation**:

```python
risk_distance = entry_price - stop_loss  # 137.41 - 134.57 = 2.84
tp1 = entry_price + (risk_distance × 1.0)  # 137.41 + 2.84 = 140.25
```

**Action**:

```python
# Price hits 142.11 (TP1)
tp1_size = position_size × 0.30  # 0.359 × 0.30 = 0.108

# Execute market sell
api.create_market_order(
    symbol='SOL_USDT',
    side='sell',
    amount=0.108
)

# Update position
remaining_size = 0.359 - 0.108 = 0.251
stop_loss = entry_price  # Move to breakeven (137.41)
```

**Result**: 30% profit locked, 70% remains with breakeven protection

---

### 2. Take Profit 2 (TP2)

**Trigger**: `current_price >= TP2`

**Configuration**:

```env
TP2_RR=2.0          # Risk:Reward ratio
TP2_PERCENT=40      # Exit 40% of position
```

**Calculation**:

```python
tp2 = entry_price + (risk_distance × 2.0)  # 137.41 + (2.84 × 2) = 143.09
```

**Action**: Same as TP1 but exits 40% of position

**Current Status**: TP2 is **disabled** (set to None) in current implementation

---

### 3. Stop Loss

**Trigger**: `current_price <= stop_loss`

**Configuration**:

```env
SL_ATR_MULTIPLIER=1.5
```

**Calculation**:

```python
stop_loss = entry_price - (ATR × 1.5)  # 137.41 - (1.06 × 1.5) = 134.57
```

**Action**:

```python
# Price drops to 134.57 or below
# Exit ENTIRE remaining position at market
close_position("Stop loss hit")
```

**Protection**: Maximum loss = 1.5 × ATR per position

**Dynamic Update**: After TP1 hits → stop_loss moves to entry_price (breakeven)

---

### 4. Trailing Stop ⭐

See [Trailing Stop System](#trailing-stop-system) section below.

---

## Trailing Stop System

### Overview

The **trailing stop** is a dynamic exit mechanism that:

- Follows the price upward as it moves in your favor
- Never moves down (for LONG)
- Locks in profits automatically
- Exits on price reversals

### Configuration

```env
TRAILING_ATR_MULTIPLIER=1.0
```

### How It Works

#### Initial State (Entry)

```python
Entry: 137.41
ATR: 1.06
Trailing Stop: 137.41  # Starts at entry (breakeven)
```

#### Price Moves Up

```
Candle 1: Price = 139.00, ATR = 1.06
→ Trailing Stop = 139.00 - (1.06 × 1.0) = 137.94 ✓ (higher than 137.41)

Candle 2: Price = 141.00, ATR = 1.10
→ Trailing Stop = 141.00 - (1.10 × 1.0) = 139.90 ✓ (higher than 137.94)

Candle 3: Price = 144.00, ATR = 1.15
→ Trailing Stop = 144.00 - (1.15 × 1.0) = 142.85 ✓ (higher than 139.90)
```

#### Price Reverses

```
Candle 4: Price = 142.00, ATR = 1.20
→ New calculation = 142.00 - 1.20 = 140.80
→ But trailing stop stays at 142.85 (never moves down!)

Candle 5: Price = 141.00
→ Price (141.00) < Trailing Stop (142.85)
→ ✓ TRAILING STOP HIT → EXIT POSITION
```

### Code Implementation

**File**: `risk_manager.py` → `calculate_trailing_stop()`

```python
def calculate_trailing_stop(self, entry_price, current_price, atr,
                           side, current_trailing_stop):
    trailing_distance = atr * self.trailing_atr_multiplier

    if side == "long":
        new_trailing_stop = current_price - trailing_distance

        # First time setup
        if current_trailing_stop is None:
            if current_price > entry_price:
                return max(new_trailing_stop, entry_price)
            else:
                return entry_price  # Breakeven protection

        # Only move up, never down
        else:
            return max(new_trailing_stop, current_trailing_stop)
```

### Trailing Stop vs Stop Loss

| Feature         | Stop Loss                             | Trailing Stop               |
| --------------- | ------------------------------------- | --------------------------- |
| **Type**        | Fixed price                           | Dynamic price               |
| **Direction**   | Never changes (until TP1 → breakeven) | Moves up only               |
| **Purpose**     | Limit loss                            | Lock profits                |
| **Trigger**     | Price drops below entry - 1.5×ATR     | Price reverses after gain   |
| **Active When** | Always                                | After price moves in profit |

### Example Scenario

```
Entry: 137.41
Stop Loss: 134.57 (fixed until TP1)
Initial Trailing Stop: 137.41

Time | Price  | ATR  | Trailing Stop | Action
-----|--------|------|---------------|------------------
T0   | 137.41 | 1.06 | 137.41        | Entry filled
T1   | 138.00 | 1.06 | 136.94        | No action
T2   | 139.50 | 1.08 | 138.42        | Trailing up
T3   | 141.00 | 1.10 | 139.90        | Trailing up
T4   | 142.50 | 1.12 | 141.38        | Trailing up
T5   | 144.00 | 1.15 | 142.85        | Trailing up
T6   | 142.00 | 1.20 | 142.85        | Price drop, stop stays
T7   | 141.50 | 1.20 | 142.85        | Getting close...
T8   | 140.50 | 1.20 | 142.85        | ✓ TRAILING STOP HIT!

EXIT @ 140.50
Profit: (140.50 - 137.41) / 137.41 = +2.25%
```

**Without trailing stop**: Might have held longer and given back more profit

**With trailing stop**: Locked in profit when trend reversed

---

## Position Persistence

### Problem

When the bot shuts down, position data stored in memory (RAM) is lost. The bot cannot resume monitoring open positions.

### Solution

**File**: `gate_ma_main.py` → `_save_position_state()`, `_load_position_state()`

**Position State File**: `position_state.json`

### How It Works

#### 1. Save Position (After Every Update)

```python
def _save_position_state(self):
    if self.current_position is None:
        # Delete file if no position
        os.remove(self.position_file)
    else:
        # Save to JSON
        json.dump(self.current_position, open(self.position_file, 'w'))
```

**Saved After**:

- ✓ Entry orders filled
- ✓ TP1/TP2 hit
- ✓ Trailing stop updated
- ✓ Position closed (file deleted)

#### 2. Load Position (On Startup)

```python
def _load_position_state(self):
    if os.path.exists(self.position_file):
        # Load from JSON
        self.current_position = json.load(open(self.position_file))
        print("✓ Resumed position: LONG @ 137.4148")
```

#### 3. Example State File

**File**: `position_state.json`

```json
{
  "side": "long",
  "entry_time": "2026-01-12T00:42:14",
  "entry_price": 137.41,
  "stop_loss": 134.57,
  "position_size": 0.359,
  "remaining_size": 0.251,
  "risk_amount": 49.28,
  "tp1": 142.11,
  "tp1_percent": 30,
  "tp2": null,
  "tp2_percent": 0,
  "trailing_stop": 142.85,
  "order_ids": ["1234567", "1234568"]
}
```

### Resume Flow

```
Bot Running → Entry @ 137.41 → Save to position_state.json
                                         ↓
                              Price moves to 144.00
                         Trailing stop updates to 142.85
                              Save to position_state.json
                                         ↓
                         Bot Crashes/Power Outage
                         position_state.json remains on disk
                                         ↓
                              Bot Restarts
                         Load position_state.json
                      Resume monitoring from 142.85
                                         ↓
                         Price drops to 140.50
                    ✓ Trailing Stop Hit → Exit → Delete file
```

**Result**: Zero data loss, continuous monitoring even across restarts

---

## Risk Management

### Position Sizing

**File**: `risk_manager.py` → `calculate_position_size()`

**Method**: Fixed USDT allocation per trade

```python
MAX_POSITION_USDT=50  # Allocate 50 USDT per trade

position_size = 50 / entry_price
# Example: 50 / 137.41 = 0.364 SOL
```

**Not Risk-Based**: Current implementation uses fixed allocation, not % of equity at risk

### Stop Loss Distance

```python
stop_loss = entry_price - (ATR × 1.5)
```

**ATR = 1.06**:

- Stop Loss: 137.41 - 1.59 = 134.57
- Risk per coin: 2.84 USDT
- Total risk: 0.364 × 2.84 = 1.03 USDT per 50 USDT allocated = **2.07% risk**

### Risk:Reward Ratios

| Level    | R:R     | Exit % | Purpose                            |
| -------- | ------- | ------ | ---------------------------------- |
| TP1      | 1:1     | 30%    | Quick profit, move SL to breakeven |
| TP2      | 2:1     | 40%    | Major profit target                |
| Trailing | Dynamic | 30-70% | Lock gains on trend continuation   |

### Breakeven Protection

After TP1 hits:

```python
stop_loss = entry_price  # Move from 134.57 → 137.41
```

**Result**: Worst case = breakeven (no loss) after taking 30% profit

---

## Configuration Reference

### Environment Variables (.env)

```env
# Trading Settings
TRADING_PAIR=SOL_USDT
TIMEFRAME=4H
MAX_POSITION_USDT=50

# Entry Settings
ENTRY_1_PERCENT=70    # % allocated to Entry 1
ENTRY_2_PERCENT=30    # % allocated to Entry 2

# Risk Management
SL_ATR_MULTIPLIER=1.5
TP1_RR=1.0
TP1_PERCENT=30
TP2_RR=2.0
TP2_PERCENT=0        # Disabled
TRAILING_ATR_MULTIPLIER=1.0
MAX_CANDLES_HOLD=20  # Not currently enforced

# Strategy Parameters
EMA_SHORT_PERIOD=20
EMA_LONG_PERIOD=50
RSI_PERIOD=14
ADX_PERIOD=14
ATR_PERIOD=14
```

---

## Summary Diagram

```
ENTRY SIGNAL
    ↓
Place Limit Orders (70% @ EMA Short, 30% @ EMA Long)
    ↓
Orders Filled → Position Created
    ↓              ↓
    │         Save to position_state.json
    ↓
Monitor Price Every Update
    ↓
    ├─→ Price >= TP1 (142.11)
    │       → Sell 30%
    │       → Move SL to breakeven
    │       → Update position_state.json
    │
    ├─→ Price >= TP2 (disabled)
    │       → Sell 40%
    │
    ├─→ Price <= Stop Loss (134.57)
    │       → Exit entire position
    │       → Delete position_state.json
    │
    └─→ Trailing Stop Hit
            → Exit remaining position
            → Delete position_state.json
```

---

## Files Reference

| File                  | Purpose                                       |
| --------------------- | --------------------------------------------- |
| `gate_ma_main.py`     | Main bot logic, entry/exit execution          |
| `strategy.py`         | Signal detection, entry calculations          |
| `risk_manager.py`     | Position sizing, SL/TP/trailing stop logic    |
| `gate_api.py`         | Gate.io API wrapper                           |
| `indicators.py`       | Technical indicators (EMA, RSI, ADX, ATR)     |
| `position_state.json` | Current position persistence (auto-generated) |
| `.env`                | Configuration                                 |

---

## Key Takeaways

1. **Dual Entry**: Averages into positions at EMA levels
2. **Multiple Exits**: TP1, TP2, Stop Loss, Trailing Stop
3. **Breakeven Protection**: SL moves to entry after TP1
4. **Dynamic Trailing**: Locks profits automatically
5. **Position Persistence**: Survives bot restarts
6. **ATR-Based Risk**: All stops/trails based on volatility

**The bot is designed to ride trends while protecting capital and locking in gains progressively.**
