# app.py
import time
import streamlit as st
import pandas as pd

from data.positions import Portfolio, CWPosition, HedgePosition
from data.position_store import load_portfolio
from data.market_data import MarketDataService

from engine.risk_engine import calculate_portfolio_risk
from engine.pnl_engine import calculate_pnl
from engine.stress_engine import stress_test_grid
from engine.hedge_engine import generate_hedge_actions
from engine.pricing_engine import price_cw
from engine.portfolio_hedge_engine import hedge_by_underlying
from engine.issuance_risk_engine import evaluate_issuance_risk
from engine.issuance_engine import evaluate_issuance, scan_strikes

from datetime import date
from config.settings import STRESS_SHOCKS


# =========================
# INIT
# =========================

st.set_page_config(layout="wide")
st.title("📊 CW Trading Desk Dashboard (Issuer)")

# =========================
# REFRESH CONTROL
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    auto_refresh = st.checkbox("🔄 Auto Refresh", value=False)

with col2:
    refresh_interval = st.selectbox(
        "Interval (sec)",
        [5, 10, 30, 60],
        index=1
    )

with col3:
    if st.button("🔁 Manual Refresh"):
        st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview",
    "Risk & Monitoring",
    "Issuance & Optimization",
    "Simulation",
    "Portfolio & Hedging",
    "Capital"
])

# --- Portfolio ---
cw_positions, hedge_positions = load_portfolio()
portfolio = Portfolio(cw_positions, hedge_positions)

md = MarketDataService()
# =========================
# CALCULATIONS
# =========================

risk = calculate_portfolio_risk(portfolio, md)
pnl = calculate_pnl(portfolio, md)

spot_shocks = STRESS_SHOCKS
vol_shocks = [-0.10, 0.0, 0.10]

stress = stress_test_grid(portfolio, md, spot_shocks, vol_shocks)
hedge_actions = generate_hedge_actions(risk)

# =========================
# OVERVIEW -TAB1
# =========================
with tab1:
    st.subheader("📌 Portfolio Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Net Delta", f"{risk['total']['delta']:,.0f}")
    col2.metric("Gamma", f"{risk['total']['gamma']:,.2f}")
    col3.metric("Vega", f"{risk['total']['vega']:,.0f}")
    col4.metric("Theta", f"{risk['total']['theta']:,.0f}")
    col5.metric("Total P&L", f"{pnl['total_pnl']:,.0f}")

# =========================
# RISK & MONITORING - TAB2
# =========================
with tab2:

    sub1, sub2 = st.tabs(["Risk", "Monitoring"])

    with sub1:
        st.subheader("📊 Risk by Underlying")

        risk_table = []

        for u, r in risk["by_underlying"].items():
            risk_table.append({
                "Underlying": u,
                "Delta": round(r["delta"], 0),
                "Gamma": round(r["gamma"], 2),
                "Vega": round(r["vega"], 0),
                "Theta": round(r["theta"], 0)
            })

        df_risk = pd.DataFrame(risk_table)
        st.dataframe(df_risk, use_container_width=True)


# =========================
# MONITORING
# =========================
    with sub2:
        st.subheader("📡 Monitoring & Alerts")

        from data.monitor_store import record_snapshot, load_logs

        # =========================
        # SNAPSHOT BUTTON
        # =========================

        if st.button("📸 Record Snapshot"):
            record_snapshot(risk, pnl)
            st.success("Snapshot recorded")

        logs = load_logs()

        # =========================
        # TIME SERIES TABLE
        # =========================

        if logs:

            df_logs = pd.DataFrame(logs)
            st.dataframe(df_logs, use_container_width=True)

            # =========================
            # SIMPLE ALERTS
            # =========================

            st.subheader("🚨 Monitoring Alerts")

            latest = logs[-1]

            # Delta drift alert
            if len(logs) > 1:
                prev = logs[-2]

                delta_change = latest["delta"] - prev["delta"]

                if abs(delta_change) > 100_000:
                    st.warning(f"Large Delta Change: {delta_change:,.0f}")

            # P&L drop alert
            if len(logs) > 1:
                pnl_change = latest["pnl"] - logs[-2]["pnl"]

                if pnl_change < -500_000:
                    st.error(f"P&L Drop: {pnl_change:,.0f}")

        else:
            st.info("No monitoring data yet")

    # =========================
    # ALERT
    # =========================

        st.subheader("🚨 Risk Alerts")

        if risk["breaches"]:
            for b in risk["breaches"]:
                st.error(b)
        else:
            st.success("All risk within limits")

# =========================
# ISSUANCE
# =========================
with tab3:

    sub1, sub2, sub3 = st.tabs([
        "Issuance",
        "Strike Optimizer",
        "Gamma Check"
    ])

    with sub1:
        st.subheader("🏗️ CW Issuance Strategy")


        # =========================
        # INPUT
        # =========================

        col1, col2, col3 = st.columns(3)

        with col1:
            ticker = st.text_input("Ticker", value="HPG.VN")

        with col2:
            expiry = st.date_input("Expiry", value=date(2026, 6, 30))

        with col3:
            strike = st.number_input("Single Strike", value=30.0)

        # =========================
        # SINGLE EVALUATION
        # =========================

        if st.button("Evaluate CW"):

            res = evaluate_issuance(md, ticker, strike, expiry.isoformat())
            pricing = price_cw(md, ticker, strike, expiry.isoformat())

            st.write("### 📊 Issuance Decision")

            col1, col2 = st.columns(2)

            with col1:
                st.write("#### Strategy Metrics")
                st.json(res)

            with col2:
                st.write("#### Pricing")
                st.json(pricing)

    # =========================
    # AUTO STRIKE GENERATOR
    # =========================
    with sub2:
        st.write("### ⚙️ Auto Strike Generator")

        if st.button("Generate Strikes from Spot"):

            spot = md.get_spot(ticker)

            auto_strikes = [
                round(spot * x, 1)
                for x in [0.9, 0.95, 1.0, 1.05, 1.1, 1.2]
            ]

            strike_range = ",".join([str(k) for k in auto_strikes])

            st.success(f"Generated: {strike_range}")

        # =========================
        # STRIKE SCAN
        # =========================

        st.write("### 🔍 Scan Multiple Strikes")

        col1, col2 = st.columns([3,1])

        with col1:
            strike_range = st.text_input(
                "Strike List (comma separated)",
                value="25,27,30,32,35"
            )

        with col2:
            run_scan = st.button("Run Scan")

        if run_scan:

            try:
                strike_list = [float(x.strip()) for x in strike_range.split(",") if x.strip() != ""]

                rows = []

                for K in strike_list:

                    res = evaluate_issuance(md, ticker, K, expiry.isoformat())
                    pricing = price_cw(md, ticker, K, expiry.isoformat())

                    rows.append({
                        "Strike": K,
                        "Moneyness": res["moneyness"],
                        "Vol": pricing["sigma"],
                        "Fair Value": pricing["fair_value"],
                        "Issue Price": pricing["issuance_price"],
                        "Edge": pricing["edge"],
                        "Risk": res["risk"]
                    })

                df = pd.DataFrame(rows)

                st.dataframe(df, use_container_width=True)

            except Exception as e:
                st.error(f"Invalid input: {e}")

        # =========================
        # STRIKE OPTIMIZER
        # =========================
        st.write("### 🎯 Strike Optimizer")

        from engine.strike_optimizer import optimize_strikes

        qty = st.number_input("CW Quantity", min_value=1, step=1000, key="opt_qty")
        cr = st.number_input("Conversion Ratio", min_value=0.1, step=0.1, key="opt_cr")
        gamma_limit = st.number_input("Gamma Limit", min_value=1, step=100, key="opt_gamma")
        lambda_risk = st.slider("Risk Aversion (λ)", 0.0, 0.001, 0.0001, key="opt_lambda")

        if st.button("Run Strike Optimization"):

            results = optimize_strikes(
                portfolio,
                md,
                ticker,
                expiry.isoformat(),
                qty,
                cr,
                gamma_limit,
                lambda_risk
            )

            if results:

                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)

                best = results[0]

                st.success(
                    f"Best Strike: {best['strike']} | Score: {round(best['score'],4)}"
                )

            else:
                st.error("No feasible strikes under gamma constraint")

    # =========================
    # GAMMA RISK CHECK
    # =========================
    with sub3:
        st.write("### ⚠️ Gamma Risk Check")



        gamma_limit = st.number_input("Gamma Limit", value=10000)

        qty = st.number_input("CW Quantity", value=1_000_000)
        cr = st.number_input("Conversion Ratio", value=1.0, key="gamma_cr")

        if st.button("Check Issuance Risk"):

            res = evaluate_issuance_risk(
                portfolio,
                md,
                ticker,
                strike,
                expiry.isoformat(),
                qty,
                cr,
                gamma_limit
            )

            col1, col2, col3 = st.columns(3)

            col1.metric("Current Gamma", res["current_gamma"])
            col2.metric("Candidate Gamma", res["candidate_gamma"])
            col3.metric("New Gamma", res["new_gamma"])

            if res["decision"] == "APPROVE":
                st.success(f"✅ APPROVED: {res['reason']}")
            else:
                st.error(f"❌ REJECTED: {res['reason']}")



# =========================
# SIMULATION - TAB4
# =========================
with tab4:
    sub1, sub2, sub3, sub4, sub5 = st.tabs([
        "Stress",
        "Grid Simulation",
        "Hedging Simulation",
        "Portfolio Hedge Optimization",
        "Monte Carlo"
    ])

    with sub1:
        st.subheader("📉 Stress Test (Spot × Vol)")

        rows = []

        for s in spot_shocks:
            for v in vol_shocks:
                res = stress[(s, v)]

                rows.append({
                    "Spot Shock": f"{int(s*100)}%",
                    "Vol Shock": f"{int(v*100)}%",
                    "P&L": round(res["total_pnl"], 0)
                })

        df_stress = pd.DataFrame(rows)

        pivot = df_stress.pivot(
            index="Spot Shock",
            columns="Vol Shock",
            values="P&L"
        )

        st.dataframe(pivot, use_container_width=True)

# =========================
# GRID SIMULATION
# =========================

    with sub2:
        st.subheader("🧪 Pre-Trade Simulation")

        from engine.simulation_engine import simulate_grid
        from engine.pricing_engine import price_cw

        col1, col2, col3 = st.columns(3)

        with col1:
            ticker = st.text_input("Ticker", value="HPG.VN", key="sim_ticker")

        with col2:
            strike = st.number_input("Strike", value=30.0, key="sim_strike")

        with col3:
            expiry = st.date_input("Expiry", key="sim_expiry")

        # pricing first
        pricing = price_cw(md, ticker, strike, expiry.isoformat())

        issue_price = pricing["issuance_price"]

        st.write(f"**Issuance Price Used:** {issue_price}")

        # shocks
        shocks = [-0.1, -0.05, 0, 0.05, 0.1]

        if st.button("Run Simulation"):

            results = simulate_grid(
                md, ticker, strike, expiry.isoformat(), issue_price, shocks
            )

            df = pd.DataFrame(results)

            st.dataframe(df, use_container_width=True)


# =========================
# HEDGING SIMULATION
# =========================

    with sub3:

        st.subheader("🔄 Delta Hedging Simulation")

        from engine.hedging_simulation import simulate_delta_hedge
        from engine.pricing_engine import price_cw

        col1, col2, col3 = st.columns(3)

        with col1:
            ticker = st.text_input("Ticker", value="HPG.VN", key="hedge_ticker")

        with col2:
            strike = st.number_input("Strike", value=30.0, key="hedge_strike")

        with col3:
            expiry = st.date_input("Expiry", key="hedge_expiry")

        shock = st.slider("Final Price Move (%)", -0.2, 0.2, 0.1)

        pricing = price_cw(md, ticker, strike, expiry.isoformat())
        issue_price = pricing["issuance_price"]

        st.write(f"**Issuance Price:** {issue_price}")

        if st.button("Run Hedging Simulation"):

            res = simulate_delta_hedge(
                md,
                ticker,
                strike,
                expiry.isoformat(),
                issue_price,
                shock
            )

            st.write("### 📊 Result")
            st.json(res)

            df_hist = pd.DataFrame(res["history"])
            st.dataframe(df_hist, use_container_width=True)

# =========================
# PORTFOLIO HEDGE OPTIMIZATION
# =========================

    with sub4:

        st.subheader("📊 Portfolio Hedge Optimization")

        from engine.portfolio_hedge_engine import (
            aggregate_greeks,
            hedge_by_underlying
        )

        # =========================
        # INPUT PARAMETERS
        # =========================

        col1, col2 = st.columns(2)

        with col1:
            band = st.number_input("Delta Band", value=50000, step=10000)

        with col2:
            st.write(" ")  # spacing
            run_hedge = st.button("Compute Optimal Hedge")

        # =========================
        # RUN HEDGE ENGINE
        # =========================

        if run_hedge:

            # ---- Portfolio level ----
            agg = aggregate_greeks(portfolio, md)

            st.write("### 📌 Portfolio Summary")

            col1, col2 = st.columns(2)
            col1.metric("Total Delta", f"{agg['delta']:,.0f}")
            col2.metric("Total Gamma", f"{agg['gamma']:,.2f}")

            # ---- Underlying breakdown ----
            st.write("### 📊 Hedge Plan by Underlying")

            hedge_plan = hedge_by_underlying(portfolio, md, band)

            rows = []

            for u, res in hedge_plan.items():

                rows.append({
                    "Underlying": u,
                    "Net Delta": round(res["delta"], 0),
                    "Action": res["action"],
                    "Shares to Trade": res["hedge"]
                })

            df = pd.DataFrame(rows)

            st.dataframe(df, use_container_width=True)

            # =========================
            # INTERPRETATION
            # =========================

            st.write("### 🧠 Interpretation")

            for r in rows:

                if r["Action"] == "TRADE":
                    st.warning(
                        f"{r['Underlying']}: Trade {r['Shares to Trade']} shares to neutralize delta"
                    )
                else:
                    st.success(
                        f"{r['Underlying']}: Within band → no action"
                    )

# =========================
# MONTE CARLO
# =========================
    with sub5:

        st.subheader("🎲 Monte Carlo Risk Simulation")

        from engine.monte_carlo_engine import run_monte_carlo
        from engine.pricing_engine import price_cw

        col1, col2, col3 = st.columns(3)

        with col1:
            ticker = st.text_input("Ticker", value="HPG.VN", key="mc_ticker")

        with col2:
            strike = st.number_input("Strike", value=30.0, key="mc_strike")

        with col3:
            expiry = st.date_input("Expiry", key="mc_expiry")

        col4, col5 = st.columns(2)

        with col4:
            n_sims = st.number_input("Simulations", value=1000)

        with col5:
            steps = st.number_input("Steps", value=30)

        pricing = price_cw(md, ticker, strike, expiry.isoformat())
        issue_price = pricing["issuance_price"]

        st.write(f"**Issuance Price:** {issue_price}")

        if st.button("Run Monte Carlo"):

            res = run_monte_carlo(
                md,
                ticker,
                strike,
                expiry.isoformat(),
                issue_price,
                int(n_sims),
                int(steps)
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Mean P&L", round(res["mean"], 2))
            col2.metric("Std Dev", round(res["std"], 2))
            col3.metric("5% Worst", round(res["p5"], 2))
            col4.metric("95% Best", round(res["p95"], 2))

            df = pd.DataFrame(res["all"], columns=["PnL"])
            st.bar_chart(df["PnL"])



        st.subheader("📊 Portfolio Monte Carlo")

        from engine.portfolio_monte_carlo import run_portfolio_mc

        n_sims = st.number_input("Simulations", value=500)

        if st.button("Run Portfolio MC"):

            res = run_portfolio_mc(portfolio, md, int(n_sims))

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Mean", round(res["mean"], 0))
            col2.metric("Std", round(res["std"], 0))
            col3.metric("5% Worst", round(res["p5"], 0))
            col4.metric("95% Best", round(res["p95"], 0))

            df = pd.DataFrame(res["all"], columns=["PnL"])
            st.histogram(df, x="PnL")

# =========================
# POSITIONS
# =========================
with tab5:
    sub1, sub2, sub3 = st.tabs([
        "Positions",
        "Execution",
        "Hedge Optimization"
    ])

    with sub1:
        st.subheader("📦 Manage CW Positions")

        # =========================
        # ADD NEW CW
        # =========================

        with st.form("add_cw"):

            underlying = st.text_input("Underlying")
            ticker = st.text_input("Ticker (e.g. HPG.VN)")
            qty = st.number_input("Quantity", step=1000)
            strike = st.number_input("Strike")
            expiry = st.date_input("Expiry")
            issue_price = st.number_input("Issue Price")
            cr = st.number_input("Conversion Ratio", value=1.0, key="add_cr")
            sigma = st.number_input("Vol", value=0.30)

            submitted = st.form_submit_button("Add CW")

            if submitted:

                if qty <= 0:
                    st.error("Quantity must be positive")
                else:
                    from data.positions import CWPosition
                    from data.position_store import add_cw

                    new_pos = CWPosition(
                        underlying,
                        ticker,
                        int(qty),
                        float(cr),
                        float(strike),
                        expiry.isoformat(),
                        float(issue_price),
                        float(sigma)
                    )

                    add_cw(new_pos, cw_positions, hedge_positions)

                    st.success("CW Added")
                    st.rerun()

        # =========================
        # CURRENT POSITIONS
        # =========================

        st.subheader("📋 Current Positions")

        pos_table = []

        for i, p in enumerate(cw_positions):

            # ✅ define T correctly
            T = (date.fromisoformat(p.expiry) - date.today()).days / 365

            vol = md.get_vol(p.ticker, p.strike, T)

            pos_table.append({
                "ID": i,
                "Underlying": p.underlying,
                "Ticker": p.ticker,
                "Qty": p.cw_qty,
                "Strike": p.strike,
                "Expiry": p.expiry,
                "Vol Used": round(vol, 4),  # 👈 NEW
                "CR": p.conversion_ratio
            })

        df_pos = pd.DataFrame(pos_table)
        st.dataframe(df_pos, use_container_width=True)

        # =========================
        # ACTIONS (SAFE)
        # =========================

        st.subheader("⚙️ Position Actions")

        from data.position_store import remove_cw, remove_expired

        if len(cw_positions) > 0:

            remove_idx = st.selectbox(
                "Select CW to remove",
                range(len(cw_positions)),
                format_func=lambda x: f"{x} - {cw_positions[x].ticker}"
            )

            confirm_remove = st.checkbox("Confirm removal")

            if confirm_remove and st.button("❌ Remove Selected CW"):
                remove_cw(remove_idx, cw_positions, hedge_positions)
                st.success("CW Removed")
                st.rerun()

        # Remove expired
        if st.button("🧹 Remove Expired CWs"):
            remove_expired(cw_positions, hedge_positions)
            st.success("Expired CWs removed")
            st.rerun()

# =========================
# TRADING
# =========================
    with sub2:

        st.subheader("🛠️ Hedge Execution")

        from data.trade_store import record_trade, load_trades

        # =========================
        # SUGGESTED ACTIONS
        # =========================

        st.write("### Suggested Hedge Actions")

        for action in hedge_actions:

            if action["action"] == "HOLD":
                st.write(f"{action['underlying']}: HOLD")
            else:
                col1, col2 = st.columns([3,1])

                col1.write(
                    f"{action['underlying']}: {action['action']} {action['size']:,}"
                )

                price = col2.number_input(
                    f"Price {action['underlying']}",
                    key=action['underlying']
                )

                if col2.button(f"Execute {action['underlying']}"):
                    record_trade(
                        action["underlying"],
                        action["action"],
                        action["size"],
                        price
                    )
                    st.success("Trade Recorded")
                    st.rerun()

        # =========================
        # TRADE HISTORY
        # =========================

        st.write("### 📜 Trade History")

        trades = load_trades()

        if trades:
            df_trades = pd.DataFrame(trades)
            st.dataframe(df_trades, use_container_width=True)
        else:
            st.write("No trades yet")

        # =========================
        # P&L
        # =========================
        st.subheader("💰 P&L Breakdown")

        col1, col2 = st.columns(2)

        col1.metric("CW P&L (Short)", f"{pnl['cw_pnl']:,.0f}")
        col2.metric("Hedge P&L", f"{pnl['hedge_pnl']:,.0f}")

# =====================================
# CAPITAL ALLOCATION & ROE OPTIMIZATION
# =====================================
with tab6:

    st.subheader("💼 Capital Allocation & ROE Optimization")

    from engine.capital_allocation_engine import allocate_capital
    from engine.strike_optimizer import generate_strikes

    total_capital = st.number_input("Total Capital", value=1_000_000_000)

    ticker = st.text_input("Underlying", value="HPG.VN")
    expiry = st.date_input("Expiry")

    qty = st.number_input("CW Size", value=1_000_000)
    cr = st.number_input("Conversion Ratio", value=1.0, key="capital_cr")

    spot = md.get_spot(ticker)
    strikes = generate_strikes(spot)

    candidates = []

    for K in strikes:
        candidates.append({
            "ticker": ticker,
            "strike": K,
            "expiry": expiry.isoformat(),
            "qty": qty,
            "cr": cr
        })

    if st.button("Run Allocation"):

        res = allocate_capital(
            portfolio,
            md,
            candidates,
            total_capital
        )

        df = pd.DataFrame(res["selected"])
        st.dataframe(df, use_container_width=True)

        st.metric("Capital Used", round(res["used_capital"], 0))
