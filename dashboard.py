import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Config ---
import os
DATA_PATH   = os.path.join(os.path.dirname(__file__), "layoffs_by_company.csv")
MONTHLY_PATH = os.path.join(os.path.dirname(__file__), "layoffs_by_month.csv")
STOCKS_PATH = os.path.join(os.path.dirname(__file__), "layoffs_with_stocks.csv")

st.set_page_config(
    page_title="Tech Layoffs Dashboard",
    page_icon="📉",
    layout="wide"
)

st.title("📉 Tech Layoffs Analytics")
st.caption("Source: layoffs.fyi — updated through March 2026")

with st.expander("ℹ️ About this dashboard"):
    st.markdown("""
    ### What is this?
    This dashboard tracks tech industry layoffs from 2020 through early 2026, sourced from
    [layoffs.fyi](https://layoffs.fyi) — a crowd-sourced database maintained by Roger Lee.

    It answers three core questions:
    - **Who** is getting laid off (which companies, which industries)?
    - **When** did layoffs peak — and are they accelerating or slowing?
    - **What stage** are these companies at — early-stage startups or established public companies?

    ---

    ### How was it built?
    This is a end-to-end modern data stack project built entirely with free, open-source tools:

    | Layer | Tool | Purpose |
    |---|---|---|
    | Storage | **DuckDB** | Local SQL database — stores the raw CSV and all transformed tables |
    | Transform | **dbt Core** | SQL-based transformation pipeline — cleans and aggregates the raw data |
    | Dashboard | **Streamlit** | Python web app framework — renders this dashboard |
    | Charts | **Plotly** | Interactive charting library |
    | Hosting | **Streamlit Community Cloud** | Free public deployment direct from GitHub |

    ---

    ### The pipeline
    1. Raw CSV downloaded from Kaggle (layoffs.fyi data) and loaded into DuckDB
    2. A **dbt staging model** cleaned the data — fixed date formats, cast types, handled nulls
    3. Two **dbt mart models** aggregated the data by company and by month
    4. This Streamlit app reads those mart tables and renders the charts you see here

    ---
    *Built by Mike Duncan as a hands-on learning project with the modern data stack.*
    """)


# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    return df

@st.cache_data
def load_monthly():
    df = pd.read_csv(MONTHLY_PATH, parse_dates=["month"])
    return df

@st.cache_data
def load_stocks():
    df = pd.read_csv(STOCKS_PATH, parse_dates=["price_date", "layoff_date"])
    return df

df = load_data()
df_monthly = load_monthly()
df_stocks = load_stocks()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

industries = sorted(df["industry"].dropna().unique())
selected_industries = st.sidebar.multiselect("Industry", industries, default=industries)

stages = sorted(df["stage"].dropna().unique())
selected_stages = st.sidebar.multiselect("Funding Stage", stages, default=stages)

countries = sorted(df["country"].dropna().unique())
selected_countries = st.sidebar.multiselect("Country", countries, default=countries)

# --- Apply Filters ---
filtered = df[
    df["industry"].isin(selected_industries) &
    df["stage"].isin(selected_stages) &
    df["country"].isin(selected_countries)
]

# --- KPI Row ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Laid Off", f"{int(filtered['total_laid_off'].sum()):,}")
col2.metric("Companies Affected", f"{filtered['company'].nunique():,}")
col3.metric("Layoff Events", f"{int(filtered['layoff_events'].sum()):,}")
col4.metric("Avg % Laid Off", f"{filtered['avg_pct_laid_off'].mean():.1f}%")

st.divider()

# --- Row 1: Top Companies + Industry Breakdown ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top 15 Companies by Total Laid Off")
    top_companies = (
        filtered.nlargest(15, "total_laid_off")[["company", "total_laid_off", "industry"]]
        .sort_values("total_laid_off")
    )
    fig1 = px.bar(
        top_companies,
        x="total_laid_off",
        y="company",
        color="industry",
        orientation="h",
        labels={"total_laid_off": "Total Laid Off", "company": ""},
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig1.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig1, use_container_width=True)

with col_right:
    st.subheader("Layoffs by Industry")
    by_industry = (
        filtered.groupby("industry")["total_laid_off"]
        .sum()
        .reset_index()
        .sort_values("total_laid_off", ascending=False)
    )
    fig2 = px.bar(
        by_industry,
        x="industry",
        y="total_laid_off",
        labels={"total_laid_off": "Total Laid Off", "industry": ""},
        color="total_laid_off",
        color_continuous_scale="Reds"
    )
    fig2.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=0, b=0))
    fig2.update_xaxes(tickangle=45)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# --- Row 2: Funding Stage + Repeat Layers ---
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Layoffs by Funding Stage")
    by_stage = (
        filtered.groupby("stage")["total_laid_off"]
        .sum()
        .reset_index()
        .sort_values("total_laid_off", ascending=False)
    )
    fig3 = px.pie(
        by_stage,
        names="stage",
        values="total_laid_off",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig3.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig3, use_container_width=True)

with col_right2:
    st.subheader("Repeat Layers (Most Layoff Events)")
    repeat_layers = (
        filtered.nlargest(15, "layoff_events")[["company", "layoff_events", "total_laid_off"]]
        .sort_values("layoff_events")
    )
    fig4 = px.bar(
        repeat_layers,
        x="layoff_events",
        y="company",
        orientation="h",
        labels={"layoff_events": "Number of Layoff Events", "company": ""},
        color="layoff_events",
        color_continuous_scale="Blues"
    )
    fig4.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# --- Row 3: Layoffs Over Time ---
st.subheader("Layoffs Over Time")

time_grain = st.radio("View by", ["Month", "Quarter"], horizontal=True)

if time_grain == "Quarter":
    df_time = df_monthly.copy()
    df_time["period"] = df_time["month"].dt.to_period("Q").dt.to_timestamp()
    df_time = df_time.groupby("period").agg(
        total_laid_off=("total_laid_off", "sum"),
        companies_affected=("companies_affected", "sum"),
        layoff_events=("layoff_events", "sum")
    ).reset_index().rename(columns={"period": "month"})
else:
    df_time = df_monthly.copy()

fig5 = px.bar(
    df_time,
    x="month",
    y="total_laid_off",
    labels={"total_laid_off": "Total Laid Off", "month": ""},
    color_discrete_sequence=["#e74c3c"]
)
fig5.add_scatter(
    x=df_monthly["month"],
    y=df_monthly["rolling_3m_avg"],
    mode="lines",
    name="3-Month Avg",
    line=dict(color="#2c3e50", width=2)
)
fig5.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=True)
st.plotly_chart(fig5, use_container_width=True)

st.divider()

# --- Raw Data Table ---
with st.expander("View Raw Data"):
    st.dataframe(
        filtered.sort_values("total_laid_off", ascending=False).reset_index(drop=True),
        use_container_width=True
    )

st.divider()

# ── Stock Price Section ───────────────────────────────────────────────────────
st.header("📈 Stock Price Around Layoff Announcement")
st.caption("Prices indexed to 100 on the layoff announcement date. All companies comparable on same scale.")

# Filters
stock_col1, stock_col2, stock_col3 = st.columns(3)

with stock_col1:
    stock_industries = sorted(df_stocks["industry"].dropna().unique())
    selected_stock_industries = st.multiselect(
        "Filter by Industry", stock_industries, default=stock_industries, key="stock_industry"
    )

with stock_col2:
    all_companies = sorted(df_stocks[df_stocks["industry"].isin(selected_stock_industries)]["company"].unique())
    selected_companies = st.multiselect(
        "Select Companies (leave blank = all)", all_companies, default=[], key="stock_companies"
    )

with stock_col3:
    day_range = st.slider("Days from Layoff", min_value=-180, max_value=180, value=(-180, 180))

# Apply filters
stock_filtered = df_stocks[
    df_stocks["industry"].isin(selected_stock_industries) &
    df_stocks["days_from_layoff"].between(day_range[0], day_range[1])
]
if selected_companies:
    stock_filtered = stock_filtered[stock_filtered["company"].isin(selected_companies)]

# ── Line Chart: Indexed Price ─────────────────────────────────────────────────
st.subheader("Indexed Stock Price (-180 to +180 Days)")

fig_stock = px.line(
    stock_filtered,
    x="days_from_layoff",
    y="indexed_price",
    color="company",
    hover_data=["ticker", "industry", "total_laid_off", "close_price", "currency"],
    labels={
        "days_from_layoff": "Days from Layoff Announcement",
        "indexed_price": "Indexed Price (100 = announcement day)",
        "company": "Company"
    },
    color_discrete_sequence=px.colors.qualitative.Safe
)
fig_stock.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Layoff Date", annotation_position="top right")
fig_stock.add_hline(y=100, line_dash="dot", line_color="gray")
fig_stock.update_layout(margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", height=500)
st.plotly_chart(fig_stock, use_container_width=True)

st.divider()

# ── Summary Table: Key Checkpoints ───────────────────────────────────────────
st.subheader("Average Indexed Price at Key Checkpoints")
st.caption("How did stocks move on average before and after layoffs?")

checkpoints = {
    "-30 days": (-35, -25),
    "Day 0":    (-3,   3),
    "+30 days": (25,  35),
    "+60 days": (55,  65),
    "+90 days": (85,  95),
    "+180 days": (175, 185),
}

summary_rows = []
for label, (lo, hi) in checkpoints.items():
    window = stock_filtered[stock_filtered["days_from_layoff"].between(lo, hi)]
    avg = window.groupby("company")["indexed_price"].mean().reset_index()
    avg.columns = ["company", label]
    summary_rows.append(avg.set_index("company"))

if summary_rows:
    summary_df = pd.concat(summary_rows, axis=1).round(1).reset_index()
    summary_df = summary_df.sort_values("Day 0", ascending=False)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.divider()

# ── Average Across All Companies ──────────────────────────────────────────────
st.subheader("Average Indexed Price — All Selected Companies")

avg_by_day = (
    stock_filtered.groupby("days_from_layoff")["indexed_price"]
    .mean()
    .reset_index()
    .rename(columns={"indexed_price": "avg_indexed_price"})
)

fig_avg = px.line(
    avg_by_day,
    x="days_from_layoff",
    y="avg_indexed_price",
    labels={
        "days_from_layoff": "Days from Layoff Announcement",
        "avg_indexed_price": "Average Indexed Price"
    },
    color_discrete_sequence=["#2c3e50"]
)
fig_avg.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Layoff Date")
fig_avg.add_hline(y=100, line_dash="dot", line_color="gray")
fig_avg.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=400)
st.plotly_chart(fig_avg, use_container_width=True)
