# BitMart Trading Bot - MA Method 2

Bot trading crypto otomatis dengan strategi Trend-Following + Momentum Confluence.

## 🚀 Multi-Exchange Support

This project supports multiple exchanges with the **SAME MA STRATEGY**:

### Available Bots

| Bot                  | Exchange | Strategy                  | File                     |
| -------------------- | -------- | ------------------------- | ------------------------ |
| **BitMart MA Bot**   | BitMart  | MA Trend Following        | `ma_main.py`             |
| **Gate.io MA Bot**   | Gate.io  | MA Trend Following (SAME) | `gate_ma_main.py` ✨ NEW |
| **Gate.io Grid Bot** | Gate.io  | Grid DCA (Different)      | `gate_grid_bot.py`       |

**Strategy is 100% identical** between BitMart and Gate.io MA bots!

For documentation:

- Gate.io MA Bot: [GATE_MA_BOT_READY.md](GATE_MA_BOT_READY.md)
- Gate.io Grid Bot: [GATE_README.md](GATE_README.md)

## Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Konfigurasi API

Edit file `.env`:

```
BITMART_API_KEY=your_api_key_here
BITMART_SECRET_KEY=your_secret_key_here
BITMART_MEMO=your_memo_here
```

### 3. Jalankan Bot

```powershell
python main.py
```

## Menu

1. Start Trading Bot - Mulai bot trading
2. View Current Position - Lihat posisi terbuka
3. View Strategy Status - Analisis market
4. View Account Balance - Cek balance
5. View Configuration - Lihat pengaturan
6. View Trade History - Riwayat trading
7. Test API Connection - Test API
8. Emergency Stop All - Stop darurat
9. Exit - Keluar

## ⚠️ Trading Type

**SPOT TRADING - LONG ONLY (BUY & SELL)**

- ✅ BUY (LONG) = Beli crypto dengan USDT
- ✅ SELL (EXIT) = Jual crypto kembali ke USDT
- ❌ NO SHORT SELLING = Tidak bisa jual dulu beli kemudian
- ❌ NO LEVERAGE = Tidak ada pinjaman/margin

## Strategi Entry (SEMUA Kondisi Harus Terpenuhi)

Bot **HANYA** akan place order jika **SEMUA** kondisi di bawah ini ✓ (Signal = YES):

1. **EMA Alignment** ✓
   - Price > EMA 9 > EMA 21 (uptrend confirmed)
2. **RSI Valid** ✓
   - RSI antara 40-70 (momentum baik, tidak overbought/oversold)
3. **ADX Strong** ✓
   - ADX ≥ 25 (trend kuat, bukan sideways)
4. **Volume Confirmation** ✓
   - Volume ≥ Volume MA 20 (likuiditas cukup)

**Jika salah satu kondisi ✗ = Signal NO = Bot TIDAK place order**

## Exit Strategy

- **Stop Loss**: ATR-based (2.0x default) - proteksi kerugian
- **Take Profit 1**: 1R (default TP1_PERCENT) - ambil profit awal
- **Take Profit 2**: 2R (default TP2_PERCENT) - target profit utama
- **Trailing Stop**: 1.5x ATR default - maximize profit

## Position Allocation (Scale-In Strategy)

**Allocation-Based System:**

- **MAX_USDT_PER_TRADE**: Total USDT yang dialokasikan per signal (contoh: 500 USDT)
- **Entry 1**: 30% dari MAX_USDT di EMA Short (support pertama)
- **Entry 2**: 70% dari MAX_USDT di EMA Long (support kedua)

**Entry Logic:**

- Signal muncul saat trend bullish (Price > EMA_short > EMA_long)
- Entry BUKAN di current price (tidak chase price tinggi)
- Entry 1 placed di EMA Short (pullback ke support)
- Entry 2 placed di EMA Long (pullback lebih dalam)
- Menunggu pullback untuk entry di harga yang baik

**Contoh:**

```
MAX_USDT_PER_TRADE = 500 USDT
ENTRY_1_PERCENT = 30% → 150 USDT @ EMA Short
ENTRY_2_PERCENT = 70% → 350 USDT @ EMA Long
```

## Mode

- **DRY_RUN=true**: Testing mode (default, aman)
- **DRY_RUN=false**: Live trading (gunakan dana real)

## Key Configuration (.env)

```bash
# Trading allocation
MAX_USDT_PER_TRADE=500  # Total USDT per signal (REQUIRED > 0)
ENTRY_1_PERCENT=30      # 30% for entry 1
ENTRY_2_PERCENT=70      # 70% for entry 2

# Risk management
STOP_LOSS_ATR_MULTIPLIER=2.0
TP1_RR=1.0              # 1:1 risk/reward
TP2_RR=2.0              # 2:1 risk/reward
```

## Logs

Semua aktivitas tercatat di folder `logs/`:

- `trading_YYYYMMDD.log` - Trading activity
- `errors_YYYYMMDD.log` - Error logs
- `bot_YYYYMMDD.log` - Bot logs

Mulai dengan DRY_RUN mode dan risk kecil (0.5-1%).

## 🌐 Gate.io Integration

### Gate.io MA Bot (Same Strategy as BitMart) ⭐

**Use the exact same MA strategy on Gate.io!**

```bash
python gate_ma_main.py
```

✅ **Same entry logic:** EMA crossover + RSI + ADX + Volume
✅ **Same exit logic:** Stop Loss, TP1, TP2, Trailing Stop
✅ **Same risk management:** Scale-in entries (30%/70%)

### Quick Start for Gate.io

1. **Configure API Keys**

```bash
# Edit .env file
GATE_API_KEY=your_gate_api_key_here
GATE_API_SECRET=your_gate_api_secret_here
USE_TESTNET=1
```

2. **Test Connection**

```bash
python gate_api_example.py
```

3. **Run MA Bot (Same Strategy as BitMart)**

```bash
python gate_ma_main.py
```

### Gate.io Files

- `gate_api.py` - Gate.io API client wrapper
- `gate_ma_main.py` - **MA trading bot (SAME strategy)** ⭐ NEW
- `gate_grid_bot.py` - Grid trading bot (different strategy)
- `gate_api_example.py` - API usage examples
- `config.env` - Grid bot configuration
- `GATE_MA_BOT_READY.md` - MA bot setup guide ⭐ NEW
- `GATE_README.md` - Grid bot documentation

For detailed setup:

- **MA Strategy:** [GATE_MA_BOT_READY.md](GATE_MA_BOT_READY.md) ⭐
- **Grid Strategy:** [GATE_README.md](GATE_README.md)

---

**Version**: 1.0 | **API**: BitMart Spot v1, Gate.io Spot v4 | **Python**: 3.8+
