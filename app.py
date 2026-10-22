import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Northstar | Equity Analysis", page_icon="📈", layout="wide")

# Reported annual fundamentals, USD billions. Valuation inputs are illustrative snapshots
# and should be refreshed from linked market data before drawing conclusions.
BASE = {
    "Microsoft": dict(ticker="MSFT", sector="Software / cloud", fy="FY2026 (year ended 2026-06-30)",
        revenue=331.839, gross_profit=225.465, operating_income=155.237, net_income=133.749,
        operating_cash_flow=182.9, capex=115.9, market_cap=3950.0, enterprise_value=3990.0,
        source="https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm",
        notes="Recurring enterprise software and cloud exposure support durable profitability. FY2026 net income benefited from investment gains, so earnings yield should be read alongside operating income and cash flow."),
    "NVIDIA": dict(ticker="NVDA", sector="Semiconductors", fy="FY2026 (year ended 2026-01-25)",
        revenue=215.938, gross_profit=153.463, operating_income=130.387, net_income=120.067,
        operating_cash_flow=102.718, capex=6.143, market_cap=5375.0, enterprise_value=5325.0,
        source="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm",
        notes="High reported margins and cash generation are offset by semiconductor cyclicality, customer concentration, export restrictions and expectations embedded in valuation."),
    "Amazon": dict(ticker="AMZN", sector="E-commerce / cloud", fy="FY2025 (year ended 2025-12-31)",
        revenue=716.924, gross_profit=360.510, operating_income=79.975, net_income=77.670,
        operating_cash_flow=139.5, capex=128.306, market_cap=2833.0, enterprise_value=2960.0,
        source="https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm",
        notes="AWS and advertising support earnings, while high infrastructure investment can compress free cash flow. FCF is particularly sensitive to the capital expenditure cycle."),
    "Uber": dict(ticker="UBER", sector="Mobility / delivery platform", fy="FY2025 (year ended 2025-12-31)",
        revenue=52.017, gross_profit=20.679, operating_income=5.565, net_income=10.053,
        operating_cash_flow=9.763, capex=0.0, market_cap=140.14, enterprise_value=136.0,
        source="https://www.sec.gov/Archives/edgar/data/1543151/000154315126000015/uber-20251231.htm",
        notes="Reported net income was meaningfully affected by tax valuation items. Operating income and free cash flow provide useful cross-checks; the app uses reported company FCF when available.")
}

st.markdown("""
<style>
.stApp{background:#07111f;color:#eaf1fa}
[data-testid="stSidebar"]{background:#0c1b2d}
.block-container{padding-top:1.4rem;max-width:1500px}
h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{background:#102238;border:1px solid #20354c;padding:15px;border-radius:14px}
div[data-testid="stDataFrame"]{border:1px solid #20354c;border-radius:10px}
.small-muted{color:#9db1c8;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

st.markdown("#### NORTHSTAR · EQUITY RESEARCH LAB")
st.title("Technology Stock Analysis")
st.caption("Interactive financial statement screening · BUY candidates and potential overvaluation / SELL candidates")
st.warning("Data integrity: annual fundamentals are sourced from company SEC filings. Market capitalization and enterprise value begin as editable reference estimates, not a live feed. Refresh valuation inputs before relying on recommendations. This is an educational screening tool, not investment advice.")

with st.sidebar:
    st.header("Screen controls")
    selected = st.multiselect("Companies", list(BASE.keys()), default=list(BASE.keys()))
    min_revenue = st.number_input("Minimum annual revenue ($B)", min_value=0.0, value=0.0, step=10.0)
    min_fcf_yield = st.slider("Minimum FCF / EV yield (%)", -10.0, 20.0, -10.0, 0.5)
    max_earnings_yield = st.slider("Maximum earnings yield for overvaluation screen (%)", 0.0, 20.0, 4.0, 0.5)
    min_score = st.slider("Minimum BUY score", 0, 100, 55, 5)
    st.divider()
    st.subheader("BUY model weights")
    w_fcf = st.slider("FCF yield weight", 0, 100, 35)
    w_gp = st.slider("Gross profit / EV weight", 0, 100, 20)
    w_ebit = st.slider("EBIT / EV weight", 0, 100, 25)
    w_growth = st.slider("Revenue growth weight", 0, 100, 20)
    st.caption("BUY weights are normalized automatically. SELL candidates use a separate valuation-and-quality screen; it is not simply the reverse BUY ranking.")

rows = []
for name in selected:
    d = BASE[name].copy()
    d["company"] = name
    # Explicitly editable valuation inputs, not silently refreshed / fabricated live data.
    d["market_cap"] = float(d["market_cap"])
    d["enterprise_value"] = float(d["enterprise_value"])
    rows.append(d)
df = pd.DataFrame(rows)
if df.empty:
    st.info("Select at least one company in the sidebar.")
    st.stop()

st.subheader("1. Valuation inputs")
st.caption("Edit the market capitalization and enterprise value estimates below. Values are USD billions. Annual statement data is held constant at the cited reporting period.")
edit = df[["company", "ticker", "fy", "market_cap", "enterprise_value"]].copy()
edited = st.data_editor(edit, hide_index=True, use_container_width=True,
    column_config={
        "company": st.column_config.TextColumn("Company", disabled=True),
        "ticker": st.column_config.TextColumn("Ticker", disabled=True),
        "fy": st.column_config.TextColumn("Financial reporting period", disabled=True),
        "market_cap": st.column_config.NumberColumn("Market cap ($B)", min_value=0.1, step=1.0, format="%.2f"),
        "enterprise_value": st.column_config.NumberColumn("Enterprise value ($B)", min_value=0.1, step=1.0, format="%.2f"),
    }, key="valuation_editor")
for _, r in edited.iterrows():
    df.loc[df.company == r.company, "market_cap"] = float(r.market_cap)
    df.loc[df.company == r.company, "enterprise_value"] = float(r.enterprise_value)

# Reported FCF definitions differ by issuer; where cash-flow inputs are present, FCF = OCF - capex.
# Amazon and Microsoft values are calculated from annual OCF less reported capex; Uber uses company-reported FCF.
reported_fcf = {"Microsoft": 67.0, "NVIDIA": 96.575, "Amazon": 11.194, "Uber": 9.763}
df["fcf"] = df["company"].map(reported_fcf)
df["earnings_yield"] = df.net_income / df.market_cap
df["ebit_ev_yield"] = df.operating_income / df.enterprise_value
df["fcf_ev_yield"] = df.fcf / df.enterprise_value
df["gp_ev_yield"] = df.gross_profit / df.enterprise_value
df["operating_margin"] = df.operating_income / df.revenue
df["net_margin"] = df.net_income / df.revenue
df["revenue_growth"] = df.company.map({"Microsoft": 0.178, "NVIDIA": 0.650, "Amazon": 0.12, "Uber": 0.18})

# Independent BUY and SELL model inputs.
def percentile(s, higher_is_better=True):
    return s.rank(pct=True, method="average") * 100 if higher_is_better else s.rank(pct=True, method="average", ascending=False) * 100

buy_weights = np.array([w_fcf, w_gp, w_ebit, w_growth], dtype=float)
if buy_weights.sum() == 0:
    buy_weights = np.array([25,25,25,25], dtype=float)
buy_weights = buy_weights / buy_weights.sum()
df["buy_score"] = (
    percentile(df["fcf_ev_yield"]) * buy_weights[0] +
    percentile(df["gp_ev_yield"]) * buy_weights[1] +
    percentile(df["ebit_ev_yield"]) * buy_weights[2] +
    percentile(df["revenue_growth"]) * buy_weights[3]
)
# SELL score rises when valuation yields are low and quality/FCF support is weaker.
df["sell_score"] = (
    percentile(df["earnings_yield"], higher_is_better=False) * 0.30 +
    percentile(df["fcf_ev_yield"], higher_is_better=False) * 0.30 +
    percentile(df["ebit_ev_yield"], higher_is_better=False) * 0.25 +
    percentile(df["operating_margin"]) * 0.15
)
df["buy_flag"] = (df["buy_score"] >= min_score) & (df["fcf_ev_yield"] * 100 >= min_fcf_yield)
df["sell_flag"] = (df["earnings_yield"] * 100 <= max_earnings_yield) & (df["sell_score"] >= 55)

c1,c2,c3,c4 = st.columns(4)
c1.metric("Companies screened", len(df))
c2.metric("BUY candidates", int(df.buy_flag.sum()))
c3.metric("Potential SELL flags", int(df.sell_flag.sum()))
c4.metric("Highest BUY score", f"{df.buy_score.max():.0f}/100")

st.subheader("2. Financial yield comparison")
metric_choice = st.selectbox("Chart metric", ["FCF / EV yield", "EBIT / EV yield", "Earnings yield", "Gross profit / EV yield", "BUY composite score", "SELL risk score"])
col_map = {"FCF / EV yield":("fcf_ev_yield","FCF / EV yield"),"EBIT / EV yield":("ebit_ev_yield","EBIT / EV yield"),"Earnings yield":("earnings_yield","Earnings yield"),"Gross profit / EV yield":("gp_ev_yield","Gross profit / EV yield"),"BUY composite score":("buy_score","BUY score"),"SELL risk score":("sell_score","SELL score")}
col,label = col_map[metric_choice]
chart = df[["company", col]].sort_values(col, ascending=False).copy()
chart[col] = chart[col] * (1 if "score" in col else 100)
fig = px.bar(chart, x=col, y="company", orientation="h", text=col, title=label, template="plotly_dark")
fig.update_layout(paper_bgcolor="#0d1b2d", plot_bgcolor="#0d1b2d", font_color="#eaf1fa", margin=dict(l=5,r=15,t=50,b=5), yaxis_title="", xaxis_title="Score / percent", showlegend=False)
fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", marker_color="#63e0d1")
st.plotly_chart(fig, use_container_width=True)

st.subheader("3. Ranked companies")
filtered = df[(df.revenue >= min_revenue) & (df.fcf_ev_yield * 100 >= min_fcf_yield)].copy()
view = filtered.sort_values("buy_score", ascending=False)[["company","ticker","revenue","market_cap","enterprise_value","earnings_yield","ebit_ev_yield","fcf_ev_yield","gp_ev_yield","operating_margin","buy_score","sell_score","buy_flag","sell_flag"]].copy()
for c in ["earnings_yield","ebit_ev_yield","fcf_ev_yield","gp_ev_yield","operating_margin"]:
    view[c] = (view[c]*100).round(2)
view = view.rename(columns={"company":"Company","ticker":"Ticker","revenue":"Revenue ($B)","market_cap":"Market cap ($B)","enterprise_value":"Enterprise value ($B)","earnings_yield":"Earnings yield (%)","ebit_ev_yield":"EBIT / EV (%)","fcf_ev_yield":"FCF / EV (%)","gp_ev_yield":"Gross profit / EV (%)","operating_margin":"Operating margin (%)","buy_score":"BUY score","sell_score":"SELL risk score","buy_flag":"BUY candidate","sell_flag":"Potential SELL"})
st.dataframe(view, hide_index=True, use_container_width=True)

buy_candidates = df[df.buy_flag].sort_values("buy_score", ascending=False)
sell_candidates = df[df.sell_flag].sort_values("sell_score", ascending=False)
left,right = st.columns(2)
with left:
    st.subheader("4. Potential BUY candidates")
    if buy_candidates.empty:
        st.info("No company passes the current BUY thresholds. Adjust the weights or filters; do not force a BUY.")
    for _, r in buy_candidates.iterrows():
        st.markdown(f"**{r.company} ({r.ticker}) — BUY screen score {r.buy_score:.0f}/100**")
        st.write(f"FCF / EV yield: {r.fcf_ev_yield:.2%}; EBIT / EV yield: {r.ebit_ev_yield:.2%}; gross profit / EV yield: {r.gp_ev_yield:.2%}.")
        st.caption(r.notes)
with right:
    st.subheader("5. Potential overvaluation / SELL candidates")
    if sell_candidates.empty:
        st.info("No company passes the current SELL screen. A lack of flags is not proof that all stocks are fairly valued.")
    for _, r in sell_candidates.iterrows():
        st.markdown(f"**{r.company} ({r.ticker}) — SELL risk score {r.sell_score:.0f}/100**")
        st.write(f"Earnings yield: {r.earnings_yield:.2%}; FCF / EV yield: {r.fcf_ev_yield:.2%}; operating margin: {r.operating_margin:.2%}.")
        st.caption("Potential overvaluation flag only: compare the market's implied growth expectations with realistic forward growth, margins, reinvestment needs and competitive risks before concluding SELL.")
st.subheader("6. Calculation methodology")
st.markdown("""
- **Earnings yield** = annual net income ÷ market capitalization.
- **EBIT / EV yield** = annual operating income ÷ enterprise value.
- **FCF / EV yield** = annual free cash flow ÷ enterprise value.
- **Gross profit / EV yield** = annual gross profit ÷ enterprise value.
- **Operating margin** = operating income ÷ revenue.
- **BUY score** = weighted percentile score using FCF yield, gross-profit yield, EBIT yield and revenue growth. Weights are adjustable and normalized to 100%.
- **SELL risk score** = separate weighted screen emphasizing low earnings yield, low FCF yield and low EBIT yield, with operating margin included as a quality cross-check. It is not the inverse of the BUY score.
- A yield is not a valuation by itself. Fast-growing companies may rationally trade at lower yields; use growth expectations, business risk, capital intensity, accounting effects and peer context to validate a thesis.
""")
st.subheader("7. Sources and reporting dates")
for name in selected:
    d = BASE[name]
    st.markdown(f"- **{name} ({d['ticker']})** — {d['fy']}. [SEC annual report / Form 10-K]({d['source']})")
st.caption("Market cap and enterprise value are editable manual inputs, not a real-time feed. FCF definitions can differ between companies; validate each figure and definition in the cited filing before submission. USD billions unless stated otherwise.")
csv = view.to_csv(index=False).encode("utf-8")
st.download_button("Download current ranked screen as CSV", data=csv, file_name="northstar_ranked_screen.csv", mime="text/csv")
