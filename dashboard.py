import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

# --- Config ---
import os
DATA_PATH = os.path.join(os.path.dirname(__file__), "layoffs_by_company.csv")
MONTHLY_PATH = os.path.join(os.path.dirname(__file__), "layoffs_by_month.csv")

st.set_page_config(
    page_title="Tech Layoffs Dashboard",
    page_icon="📉",
    layout="wide"
)

st.title("📉 Tech Layoffs Analytics")
st.caption("Source: layoffs.fyi — updated through March 2026")

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    return df

@st.cache_data
def load_monthly():
    df = pd.read_csv(MONTHLY_PATH, parse_dates=["month"])
    return df

df = load_data()
df_monthly = load_monthly()

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
