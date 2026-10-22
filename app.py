import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Signal & Noise | Equity Lab", page_icon="◈", layout="wide")

# Annual statement inputs are in USD billions. Valuation inputs and growth rates are
# illustrative/manual reference values, not live market data. Verify against filings before submission.
BASE = {
    "Microsoft": dict(ticker="MSFT", sector="Software & cloud", period="FY2026 (year ended 2026-06-30)", revenue=331.839, gross_profit=225.465, operating_income=155.237, net_income=133.749, fcf=67.0, market_cap=3950.0, enterprise_value=3990.0, growth=0.178, source="https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm", thesis="Recurring enterprise software and cloud revenue support durable profitability. Check whether valuation already prices in sustained AI and cloud growth.", risk="Net income may include non-operating items; compare earnings yield with operating income and cash flow."),
    "NVIDIA": dict(ticker="NVDA", sector="Semiconductors", period="FY2026 (year ended 2026-01-25)", revenue=215.938, gross_profit=153.463, operating_income=130.387, net_income=120.067, fcf=96.575, market_cap=5375.0, enterprise_value=5325.0, growth=0.650, source="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm", thesis="Exceptional margins and AI infrastructure demand create strong operating momentum.", risk="Cyclicality, customer concentration, export controls and high growth expectations make valuation sensitive to any slowdown."),
    "Amazon": dict(ticker="AMZN", sector="Commerce & cloud", period="FY2025 (year ended 2025-12-31)", revenue=716.924, gross_profit=360.510, operating_income=79.975, net_income=77.670, fcf=11.194, market_cap=2833.0, enterprise_value=2960.0, growth=0.120, source="https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm", thesis="AWS and advertising can support margin expansion beyond the retail business.", risk="Infrastructure investment can absorb operating cash flow; FCF depends heavily on the capex cycle."),
    "Uber": dict(ticker="UBER", sector="Mobility platform", period="FY2025 (year ended 2025-12-31)", revenue=52.017, gross_profit=20.679, operating_income=5.565, net_income=10.053, fcf=9.763, market_cap=140.14, enterprise_value=136.0, growth=0.180, source="https://www.sec.gov/Archives/edgar/data/1543151/000154315126000015/uber-20251231.htm", thesis="Asset-light marketplace economics and improving cash generation can support a higher-quality platform narrative.", risk="Competition, regulation, insurance costs and reported earnings effects warrant cross-checking net income against cash flow."),
}

st.markdown("""
<style>
:root{--ink:#f3f1e8;--muted:#9ca7a5;--panel:#151b1a;--line:#303a35;--lime:#d5ff57;--orange:#ff8759}
.stApp{background:#0c100f;color:var(--ink)}
[data-testid="stSidebar"]{background:#121715;border-right:1px solid #303a35}
.block-container{max-width:1500px;padding-top:1.25rem;padding-bottom:3rem}
section[data-testid="stSidebar"] *{color:#f3f1e8}
h1,h2,h3{letter-spacing:-.04em}
h1{font-weight:750;font-size:2.8rem!important}
[data-testid="stMetric"]{background:#151b1a;border:1px solid #303a35;border-radius:5px;padding:15px 17px}
[data-testid="stMetricLabel"]{color:#9ca7a5!important;text-transform:uppercase;font-size:.72rem;letter-spacing:.12em}
[data-testid="stMetricValue"]{color:#d5ff57!important;font-weight:700}
div[data-testid="stDataFrame"]{border:1px solid #303a35;border-radius:5px}
.signal-kicker{font-size:.72rem;letter-spacing:.2em;color:#d5ff57;font-weight:700;text-transform:uppercase}
.signal-sub{color:#9ca7a5;font-size:.94rem;line-height:1.5}
.signal-card{background:#151b1a;border:1px solid #303a35;border-top:3px solid #d5ff57;padding:17px 18px;border-radius:4px;min-height:170px}
.signal-card.risk{border-top-color:#ff8759}
.signal-label{font-size:.7rem;text-transform:uppercase;letter-spacing:.13em;color:#9ca7a5}
.signal-name{font-size:1.15rem;font-weight:700;margin:.35rem 0}
.signal-number{font-size:1.8rem;font-weight:750;color:#d5ff57}
hr{border-color:#303a35}
.stButton>button,.stDownloadButton>button{border-radius:3px;border:1px solid #d5ff57;background:#d5ff57;color:#10140e;font-weight:700}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="signal-kicker">SIGNAL & NOISE / INDEPENDENT EQUITY LAB</div>', unsafe_allow_html=True)
st.title("Find the price that the story can’t justify.")
st.markdown('<div class="signal-sub">A comparative valuation workbench for testing when growth narratives are supported—or contradicted—by financial statement yields.</div>', unsafe_allow_html=True)
st.write("")
st.warning("Research integrity note: valuation inputs and growth assumptions are editable reference estimates, not a live market feed. Confirm all values and reporting periods against the linked filings before drawing conclusions. Educational screening only—not investment advice.")

with st.sidebar:
    st.markdown("### ◈ Screen setup")
    selected = st.multiselect("Universe", list(BASE.keys()), default=list(BASE.keys()))
    st.markdown("#### Guardrails")
    min_revenue = st.number_input("Minimum revenue ($B)", min_value=0.0, value=0.0, step=25.0)
    min_fcf = st.slider("Minimum FCF / EV (%)", -10.0, 20.0, -10.0, 0.5)
    buy_cutoff = st.slider("BUY score threshold", 0, 100, 60, 5)
    max_earnings = st.slider("Low earnings yield trigger (%)", 0.0, 20.0, 4.0, 0.5)
    sell_cutoff = st.slider("SELL risk threshold", 0, 100, 55, 5)
    st.markdown("#### What matters most? · BUY model")
    w_fcf = st.slider("Free cash flow yield", 0, 100, 35)
    w_ebit = st.slider("Operating earnings yield", 0, 100, 25)
    w_gp = st.slider("Gross profit yield", 0, 100, 20)
    w_growth = st.slider("Revenue growth assumption", 0, 100, 20)
    st.caption("Weights are normalized automatically. SELL risk is a separate screen, not simply the reverse BUY ranking.")

rows=[]
for name in selected:
    d=BASE[name].copy(); d["company"]=name; rows.append(d)
df=pd.DataFrame(rows)
if df.empty:
    st.info("Choose at least one company in the sidebar to start the analysis."); st.stop()

st.markdown("## 01 / Market assumptions")
st.caption("Edit the market-cap and enterprise-value assumptions here. All monetary values are USD billions; the statement period is shown for context.")
edit=df[["company","ticker","period","market_cap","enterprise_value"]].copy()
edited=st.data_editor(edit, hide_index=True, use_container_width=True, key="assumption_editor", column_config={
    "company":st.column_config.TextColumn("Company",disabled=True),"ticker":st.column_config.TextColumn("Ticker",disabled=True),"period":st.column_config.TextColumn("Statement period",disabled=True),
    "market_cap":st.column_config.NumberColumn("Market cap ($B)",min_value=0.1,step=1.0,format="%.2f"),"enterprise_value":st.column_config.NumberColumn("Enterprise value ($B)",min_value=0.1,step=1.0,format="%.2f")})
for _,r in edited.iterrows():
    df.loc[df.company==r.company,"market_cap"]=float(r.market_cap); df.loc[df.company==r.company,"enterprise_value"]=float(r.enterprise_value)

# Core yields and quality indicators
df["earnings_yield"]=df.net_income/df.market_cap
df["ebit_yield"]=df.operating_income/df.enterprise_value
df["fcf_yield"]=df.fcf/df.enterprise_value
df["gp_yield"]=df.gross_profit/df.enterprise_value
df["op_margin"]=df.operating_income/df.revenue

def pct_rank(s, higher=True):
    return s.rank(pct=True, method="average", ascending=not higher)*100
weights=np.array([w_fcf,w_ebit,w_gp,w_growth],dtype=float)
if weights.sum()==0: weights=np.array([25,25,25,25],dtype=float)
weights=weights/weights.sum()
df["buy_score"]=pct_rank(df.fcf_yield)*weights[0]+pct_rank(df.ebit_yield)*weights[1]+pct_rank(df.gp_yield)*weights[2]+pct_rank(df.growth)*weights[3]
df["sell_score"]=pct_rank(df.earnings_yield,False)*.30+pct_rank(df.fcf_yield,False)*.30+pct_rank(df.ebit_yield,False)*.25+pct_rank(df.op_margin)*.15
df["buy_flag"]=(df.buy_score>=buy_cutoff)&(df.fcf_yield*100>=min_fcf)
df["sell_flag"]=(df.earnings_yield*100<=max_earnings)&(df.sell_score>=sell_cutoff)

st.markdown("## 02 / The current read")
k1,k2,k3,k4=st.columns(4)
k1.metric("Names in universe",f"{len(df):02d}")
k2.metric("BUY screen passes",f"{int(df.buy_flag.sum()):02d}")
k3.metric("SELL risk flags",f"{int(df.sell_flag.sum()):02d}")
k4.metric("Top BUY composite",f"{df.buy_score.max():.0f}/100")

# Compact distinct stock signal cards
cards=st.columns(min(4,len(df)))
for i,(_,r) in enumerate(df.sort_values("buy_score",ascending=False).iterrows()):
    with cards[i%len(cards)]:
        cls="risk" if r.sell_flag else ""
        tag="SELL RISK FLAG" if r.sell_flag else ("BUY SCREEN PASS" if r.buy_flag else "WATCHLIST")
        st.markdown(f'<div class="signal-card {cls}"><div class="signal-label">{r.ticker} · {r.sector}</div><div class="signal-name">{r.company}</div><div class="signal-number">{r.buy_score:.0f}<span style="font-size:.8rem;color:#9ca7a5"> / 100</span></div><div class="signal-label">{tag}</div></div>',unsafe_allow_html=True)

st.markdown("## 03 / Valuation map")
st.markdown('<div class="signal-sub">The map contrasts assumed revenue growth with free-cash-flow yield. Companies in the high-growth / low-yield area may require more growth to justify their price; low yields alone do not prove overvaluation.</div>',unsafe_allow_html=True)
fig=px.scatter(df,x="growth",y="fcf_yield",size="revenue",color="sell_score",hover_name="company",text="ticker",size_max=54,color_continuous_scale=["#d5ff57","#ff8759"],labels={"growth":"Revenue growth assumption","fcf_yield":"FCF / EV yield","sell_score":"SELL risk score","revenue":"Revenue ($B)"},template="plotly_dark")
fig.update_traces(textposition="top center",marker_line_color="#0c100f",marker_line_width=1.5)
fig.update_layout(paper_bgcolor="#0c100f",plot_bgcolor="#151b1a",font_color="#f3f1e8",margin=dict(l=5,r=10,t=20,b=5),xaxis_tickformat=".0%",yaxis_tickformat=".0%",height=430,coloraxis_colorbar=dict(title="Risk"),xaxis=dict(gridcolor="#303a35",zerolinecolor="#303a35"),yaxis=dict(gridcolor="#303a35",zerolinecolor="#303a35"))
st.plotly_chart(fig,use_container_width=True)

st.markdown("## 04 / Ranking & diagnostic yields")
filtered=df[(df.revenue>=min_revenue)&(df.fcf_yield*100>=min_fcf)].copy().sort_values("buy_score",ascending=False)
view=filtered[["company","ticker","revenue","earnings_yield","ebit_yield","fcf_yield","gp_yield","op_margin","buy_score","sell_score","buy_flag","sell_flag"]].copy()
for c in ["earnings_yield","ebit_yield","fcf_yield","gp_yield","op_margin"]: view[c]=(view[c]*100).round(2)
view["BUY score"]=view.pop("buy_score").round(0); view["SELL risk"]=view.pop("sell_score").round(0)
view=view.rename(columns={"company":"Company","ticker":"Ticker","revenue":"Revenue ($B)","earnings_yield":"Earnings yield (%)","ebit_yield":"EBIT / EV (%)","fcf_yield":"FCF / EV (%)","gp_yield":"Gross profit / EV (%)","op_margin":"Operating margin (%)","buy_flag":"BUY pass","sell_flag":"SELL risk flag"})
st.dataframe(view,hide_index=True,use_container_width=True)

left,right=st.columns(2)
with left:
    st.markdown("### BUY screen / strongest relative signals")
    buys=df[df.buy_flag].sort_values("buy_score",ascending=False)
    if buys.empty: st.info("No company clears the current BUY rules. That is a valid outcome—adjust assumptions only when you can justify them.")
    for _,r in buys.iterrows():
        st.markdown(f"**{r.company} ({r.ticker}) · {r.buy_score:.0f}/100**")
        st.write(f"FCF / EV {r.fcf_yield:.2%} · EBIT / EV {r.ebit_yield:.2%} · gross profit / EV {r.gp_yield:.2%}")
        st.caption(r.thesis)
with right:
    st.markdown("### SELL risk / valuation pressure")
    sells=df[df.sell_flag].sort_values("sell_score",ascending=False)
    if sells.empty: st.info("No company currently triggers the SELL-risk rules. Absence of a flag is not proof of fair value.")
    for _,r in sells.iterrows():
        st.markdown(f"**{r.company} ({r.ticker}) · risk score {r.sell_score:.0f}/100**")
        st.write(f"Earnings yield {r.earnings_yield:.2%} · FCF / EV {r.fcf_yield:.2%} · operating margin {r.op_margin:.2%}")
        st.caption(r.risk)

st.markdown("## 05 / Method notes")
with st.expander("Open formulas, assumptions and interpretation"):
    st.markdown("""
    - **Earnings yield** = annual net income ÷ market capitalization.
    - **EBIT / EV yield** = annual operating income ÷ enterprise value.
    - **FCF / EV yield** = annual free cash flow ÷ enterprise value.
    - **Gross profit / EV yield** = annual gross profit ÷ enterprise value.
    - **Operating margin** = operating income ÷ revenue.
    - **BUY composite** = weighted percentile rank across FCF yield, EBIT yield, gross-profit yield and assumed revenue growth. Weights are normalized to 100%.
    - **SELL risk** = a separate heuristic emphasizing low earnings, FCF and EBIT yields, with operating margin as a quality cross-check. It is not the inverse of the BUY score.
    - Percentile scores are relative only to the companies selected; scores can change when the universe changes.
    - A high growth assumption can justify lower current yields, but only if future growth and margins materialize. Compare business quality, reinvestment needs, cyclicality, accounting effects and peer multiples before reaching a conclusion.
    """)

st.markdown("## 06 / Evidence trail")
for name in selected:
    d=BASE[name]
    st.markdown(f"- **{name} ({d['ticker']})** · {d['period']} · [SEC filing link]({d['source']})")
st.caption("USD billions unless noted. Market capitalization, enterprise value and growth rates are manual reference assumptions. Free-cash-flow figures may use issuer-specific definitions; verify every input and date in the source filing before submitting.")
st.download_button("Export current screen · CSV",data=view.to_csv(index=False).encode("utf-8"),file_name="signal_noise_equity_screen.csv",mime="text/csv")
