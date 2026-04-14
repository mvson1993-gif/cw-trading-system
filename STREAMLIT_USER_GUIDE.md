# CW Trading System - Streamlit Dashboard User Guide

## Overview
The Streamlit dashboard for the CW Trading System provides real-time monitoring, issuance planning, simulation, and execution tools for covered warrant issuers. This guide walks you through each section.

---

## Quick Setup

### Launch the Dashboard
```bash
cd /workspaces/cw-trading-system
streamlit run app.py
```

Access at: `http://localhost:8501`

---

## Tab-by-Tab Guide

### **Tab 1: Overview**
**Purpose:** High-level portfolio snapshot

**Display:**
- **Net Delta**: Total portfolio delta exposure (0 = balanced)
- **Gamma**: Convexity of portfolio (higher = more risk from large moves)
- **Vega**: Sensitivity to volatility changes
- **Theta**: Daily P&L from time decay
- **Total P&L**: Cumulative realized gains/losses

**When to use:** 
- Quick health check at market open/close
- Identify if portfolio is within risk limits

---

### **Tab 2: Risk & Monitoring**

#### **Sub-tab: Risk**
**Shows:** Greeks breakdown by underlying

- **Underlying**: Stock symbol (e.g., HPG)
- **Delta/Gamma/Vega/Theta**: Per-underlying risk metrics

**What it means:**
- High Delta → Unhedged exposure, consider selling stock
- High Gamma → Need to rehedge frequently if spot moves
- High Vega → Volatility risk, consider vol hedges

**Action:** If any underlying breaches limits, note in trading log and adjust hedge.

#### **Sub-tab: Monitoring**
**Record Snapshots**
- Button: "📸 Record Snapshot" → Captures current risk/P&L state
- Used for audit trail and historical analysis

**View Logs**
- Time-series table of all recorded snapshots
- Columns: Timestamp, Delta, Gamma, Vega, P&L

**Alerts**
- **🚨 Risk Alerts**: Shows active breaches (red = critical, yellow = warning, green = ok)
- **Large Delta Change**: Alert if |Δ Change| > 100k
- **P&L Drop**: Alert if P&L drops > 500k in one snapshot

---

### **Tab 3: Issuance & Optimization**

#### **Sub-tab 1: Issuance**
**Purpose:** Plan new CW issuances

**Inputs:**
- **Ticker**: Underlying symbol (e.g., HPG.VN, MWG.VN)
- **Expiry**: Issue expiration date
- **Strike List**: Comma-separated strikes (e.g., "25,27,30,32,35")

**Outputs (after "Run Scan"):**
- **Moneyness**: Spot / Strike ratio (1.0 = ATM, >1.0 = ITM)
- **Vol**: Implied volatility for pricing
- **Fair Value**: Theoretical CW value
- **Issue Price**: Recommended issuance price
- **Edge**: Spread (Issue - Fair) = your profit margin
- **Risk**: Greek exposure per 1M units

**How to use:**
1. Input strikes you're considering
2. Review Fair Value and Edge
3. Choose highest-edge strike for issuance (or balanced position across strikes)
4. Note the Risk metrics before committing

#### **Sub-tab 2: Strike Optimizer**
**Purpose:** Find optimal strike for a given quantity and risk limit

**Inputs:**
- **CW Quantity**: How many CW units to issue (e.g., 1M)
- **Conversion Ratio**: CW / underlying shares (e.g., 1.0)
- **Gamma Limit**: Max gamma you accept (e.g., 50k)
- **Risk Aversion (λ)**: Weight on risk vs. profit (0 = profit only, 0.001 = strong risk penalty)

**Output:**
- Recommended strike that maximizes edge while respecting gamma limit

**How to use:**
1. Set your position size and risk tolerance
2. Run optimizer
3. Compare results to manual strike scan
4. Choose strike for issuance

#### **Sub-tab 3: Auto Strike Generator**
**Purpose:** Quick strike suggestions based on spot

- Click "Generate Strikes from Spot" → Shows 0.9x, 0.95x, 1.0x, 1.05x, 1.1x, 1.2x spot
- Use for rapid "what if" analysis

---

### **Tab 4: Simulation**

#### **Sub-tab 1: Pre-Trade Simulation**
**Purpose:** Forecast P&L under different spot moves before issuing

**Inputs:**
- **Ticker**: Underlying
- **Strike**: Proposed strike
- **Expiry**: Issue date
- (Auto-calculated: Issuance Price)

**Output:**
- Grid showing P&L for spot shocks: [-10%, -5%, 0%, +5%, +10%]

**How to use:**
1. Input proposed issuance details
2. Review P&L grid: 
   - Negative (red) = Loss zone (you're short, price moved against you)
   - Positive (green) = Profit zone
3. If losses too large, try higher strike or add hedge

#### **Sub-tab 2: Delta Hedging Simulation**
**Purpose:** Show profit/loss from delta-hedging a CW position

**Inputs:**
- **Ticker**: Underlying
- **Strike**: CW strike
- **Final Price Move**: How much spot moves (%, e.g., 10% = price up 10%)

**Output:**
- Summary: CW P&L, Hedge P&L, Net
- Time series: Daily rehedge log

**How to use:**
1. Post-issue, simulate expected hedge costs if price moves
2. Use to validate your hedge strategy

---

### **Tab 5: Portfolio & Hedging**

#### **Sub-tab 1: Stress Test**
**Purpose:** Portfolio behavior under extreme shocks

**Display:**
- Grid: Spot shocks × Vol shocks
- Values: Portfolio P&L

**Action:** Identify worst-case scenarios (e.g., -10% spot, +10% vol) and verify reserves are sufficient.

#### **Sub-tab 2: Portfolio Hedge Optimization**
**Purpose:** Auto-calculate hedge trades to neutralize delta

**Input:**
- **Delta Band**: Target delta range (e.g., ±50k)

**Output:**
- Per-underlying action:
  - **TRADE**: "Sell X shares to neutralize"
  - **NO ACTION**: "Already within band"

**How to use:**
1. Set your acceptable delta band
2. Click "Compute Optimal Hedge"
3. Execute recommended trades in broker (manual for now; auto-execution coming)

#### **Sub-tab 3: Monte Carlo Risk Simulation**
**Purpose:** Statistically model CW value paths

**Inputs:**
- Ticker, Strike, Expiry
- Number of simulations (e.g., 1000)
- Time steps (e.g., 30)

**Output:**
- Monte Carlo Expected Value, VaR (95%)
- Distribution chart

---

### **Tab 6: Trade Execution**

#### **OCBS Integration Status**
- **Green (✅)**: Broker API enabled, ready to execute
- **Yellow (⚠️)**: Integration disabled; trades not executed

#### **Execute Trades**
**CW Issuance Section:**
- Input: CW Ticker, Underlying, Quantity
- Action: "Submit CW Issuance"
- Response: Execution ID or error

**Trade Reconciliation:**
- Button: "Run Reconciliation"
- Matches internal trades vs. broker confirmations
- Shows discrepancies if any

#### **Recent Trades**
- Table: Last 10 executed trades
- Columns: ID, Action (BUY/SELL), Underlying, Quantity, Price, Time, Status

---

### **Tab 7: Capital**

#### **Capital Allocation & ROE Optimization**
**Purpose:** Allocate capital across multiple CW issuances to maximize ROE

**Inputs:**
- **Total Capital**: Budget for new issuances (e.g., $1B)
- **Underlying**, **Expiry**, **Quantity**, **Conversion Ratio**

**Process:**
1. System generates candidate strikes
2. Algorithm selects best-ROE basket
3. Displays allocation: which strikes, quantities, and total capital used

**How to use:**
- Weekly planning: How to deploy capital across multiple underlyings
- Output: "Allocate 500M to HPG at strike 30, 300M to MWG at 58"

---

## Managing Positions

### **Current Positions**
Current positions are stored in **`data/positions.json`**:

```json
{
  "cw_positions": [
    {
      "underlying": "HPG",
      "ticker": "HPG2606",
      "cw_qty": 1000,
      "conversion_ratio": 1.0,
      "strike": 100,
      "expiry": "2026-06-01",
      "issue_price": 10.0,
      "sigma": 0.3
    }
  ],
  "hedge_positions": []
}
```

### **To Clear All Positions (Set to Zero)**

#### Option 1: Direct Edit (Quick)
1. Edit `data/positions.json`
2. Clear both `cw_positions` and `hedge_positions` arrays:
   ```json
   {
     "cw_positions": [],
     "hedge_positions": []
   }
   ```
3. Refresh Streamlit dashboard (Ctrl+R)

#### Option 2: Via Dashboard (Future UI Enhancement)
Currently, use the **Override** approach:
- In "Overview" tab, note current positions
- In "Portfolio & Hedging" → "Portfolio Hedge Optimization"
  - Set Delta Band to 0
  - Click "Compute Optimal Hedge"
  - Execute suggested trades to bring delta to zero
- Remove CW positions manually via JSON edit or database

---

## Key Workflows

### **Workflow 1: Issue New CW**
1. **Tab 3** → **Issuance**: Scan strikes, pick one with best edge
2. **Tab 4** → **Simulation**: Verify P&L grid is acceptable
3. **Tab 6** → **Trade Execution**: Submit issuance order
4. **Tab 2** → **Monitoring**: Record snapshot to log issuance

### **Workflow 2: Daily Risk Management**
1. Open **Tab 1** (Overview): Check if within limits
2. **Tab 2** (Risk & Monitoring): Review by-underlying Greeks
3. If breach: **Tab 5** → **Portfolio Hedge Op**: Compute required hedge
4. **Tab 6**: Execute hedge trades
5. **Tab 2**: Record snapshot after hedge

### **Workflow 3: EOD Reconciliation**
1. **Tab 6** → **Trade Execution** → "Run Reconciliation"
2. Review discrepancies (if any)
3. Escalate to operations if unmatched trades found

---

## Tips & Best Practices

| Metric | Safe Range | Action if Breach |
|--------|------------|------------------|
| **Net Delta** | ±200k | Hedge via stock purchase/sale |
| **Gamma** | < 50k | Reduce short vega or reduce position size |
| **Vega** | < 200k | Reduce issuance or issue higher strikes |
| **Daily Loss** | > -$5M | Reduce exposure, increase hedge |

---

## Troubleshooting

### "No spot data available for {ticker}"
- **Problem**: Market data provider doesn't have ticker
- **Solution**: Add mock price in `cw_trading_system/data/market_data.py` → `SpotProvider.mock_prices`

### Dates showing as expired
- **Problem**: Check expiry dates in `data/positions.json`
- **Solution**: Update to future date or remove position

### P&L not matching manual calc
- **Problem**: Underlying spot price might be cached
- **Solution**: Refresh browser (Ctrl+R) to clear Streamlit cache

---

## Summary: Your First 5 Minutes

1. ✅ Launch: `streamlit run app.py`
2. ✅ **Tab 1**: Check portfolio health (metrics, etc.)
3. ✅ **Tab 3**: Plan an issuance (scan a few strikes)
4. ✅ **Tab 4**: Simulate P&L under -10% spot move
5. ✅ **Tab 6**: See recent trades / check reconciliation

You're now ready to manage CW positions!
