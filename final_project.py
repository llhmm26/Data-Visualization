# streamlit_app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(
    page_title="RideWise - Komuter Data Visualization",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🚉 RideWise: Komuter Ridership Visualization Dashboard")
st.markdown("An interactive data visualization platform for analyzing **KTM Komuter ridership patterns** and suggesting travel times for workers and tourists.")

# =====================
# LOAD DATA
# =====================
@st.cache_data
def load_data():
    daily = pd.read_csv("komuter_ridership_daily_v2.csv")
    hourly = pd.read_csv("komuter_hourly_schedule_combined_iqbal_v2.csv")
    # Clean and unify
    for df in [daily, hourly]:
        df.columns = df.columns.str.strip().str.lower()
    if 'time' in hourly.columns:
        hourly['time'] = pd.to_datetime(hourly['time'], errors='coerce')
    if 'date' in daily.columns:
        daily['date'] = pd.to_datetime(daily['date'], errors='coerce')
    return daily, hourly

daily_df, hourly_df = load_data()

# =====================
# SIDEBAR FILTERS
# =====================
st.sidebar.header("🔧 Filters")

role = st.sidebar.radio("Select Your Role", ["Tourist", "Worker"])

day_type = st.sidebar.selectbox(
    "Select Day Type", sorted(hourly_df["day_type"].dropna().unique())
)

line = st.sidebar.selectbox(
    "Select Line", sorted(hourly_df["line_tag"].dropna().unique())
)

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=[daily_df["date"].min(), daily_df["date"].max()]
)

# Filter daily data
mask = (daily_df["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
daily_filtered = daily_df.loc[mask]

# Filter hourly data
hourly_filtered = hourly_df[
    (hourly_df["day_type"] == day_type) &
    (hourly_df["line_tag"] == line)
]

# =====================
# MAIN VISUALS
# =====================
st.subheader(f"📅 Monthly Ridership Trend ({line})")

# Detect numeric column for ridership automatically
numeric_cols = daily_df.select_dtypes(include=["number"]).columns.tolist()
if len(numeric_cols) == 0:
    st.warning("No numeric ridership column found in daily dataset.")
else:
    # Try to find the column that most likely represents ridership
    ridership_col = [c for c in numeric_cols if "ridership" in c.lower() or "passenger" in c.lower()]
    ridership_col = ridership_col[0] if ridership_col else numeric_cols[0]

    # Filter by line if exists
    if "line" in daily_df.columns:
        daily_filtered = daily_df[
            (daily_df["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))) &
            (daily_df["line"].astype(str).str.lower() == line.lower())
        ]
    else:
        daily_filtered = daily_df[
            daily_df["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))
        ]

    if not daily_filtered.empty:
        # --- Convert to monthly ---
        daily_filtered["month"] = daily_filtered["date"].dt.to_period("M").dt.to_timestamp()

        # Aggregate by month
        monthly_summary = (
            daily_filtered.groupby("month")[ridership_col].sum().reset_index()
        )

        # Create line chart
        fig_monthly = px.line(
            monthly_summary,
            x="month",
            y=ridership_col,
            title=f"Monthly Ridership Trend ({line})",
            labels={"month": "Month", ridership_col: "Total Passengers"},
            markers=True
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

        # Add key insights
        avg = monthly_summary[ridership_col].mean()
        peak = monthly_summary.loc[monthly_summary[ridership_col].idxmax()]
        st.info(
            f"📈 **Average Monthly Ridership:** {avg:,.0f} passengers  \n"
            f"🏆 **Peak Month:** {peak['month'].strftime('%B %Y')} "
            f"with {peak[ridership_col]:,.0f} passengers"
        )
    else:
        st.warning("No monthly data found for the selected filters.")

st.subheader(f"🕒 Average Hourly Ridership Pattern ({day_type}, {line})")

# Filter hourly data based on selected day type and line
hourly_filtered = hourly_df[
    (hourly_df["day_type"].astype(str).str.lower() == day_type.lower()) &
    (hourly_df["line_tag"].astype(str).str.lower() == line.lower())
    ]

if not hourly_filtered.empty:
    # --- Clean & prepare time column ---
    if 'time' in hourly_filtered.columns:
        hourly_filtered['hour'] = pd.to_datetime(hourly_filtered['time'], errors='coerce').dt.hour
    elif 'hour' in hourly_filtered.columns:
        hourly_filtered['hour'] = hourly_filtered['hour'].astype(int)
    else:
        st.warning("No valid time or hour column found in hourly dataset.")

    # --- Detect the ridership column automatically ---
    numeric_cols = hourly_filtered.select_dtypes(include=["number"]).columns.tolist()
    ridership_col = [c for c in numeric_cols if "ridership" in c.lower() or "passenger" in c.lower()]
    ridership_col = ridership_col[0] if ridership_col else numeric_cols[0]

    # --- Compute average ridership per hour ---
    hourly_avg = (
        hourly_filtered.groupby("hour")[ridership_col]
        .mean()
        .reset_index()
        .sort_values("hour")
    )

    # --- Plot average hourly ridership ---
    fig_hourly = px.bar(
        hourly_avg,
        x="hour",
        y=ridership_col,
        title=f"Average Hourly Ridership ({day_type})",
        labels={"hour": "Hour of Day", ridership_col: "Average Passengers"},
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

    # --- Optional line version for smooth trend view ---
    fig_hourly_line = px.line(
        hourly_avg,
        x="hour",
        y=ridership_col,
        markers=True,
        title=f"Hourly Ridership Trend ({day_type})",
        labels={"hour": "Hour of Day", ridership_col: "Average Passengers"},
    )
    st.plotly_chart(fig_hourly_line, use_container_width=True)

    # --- Display insights ---
    peak_hour = hourly_avg.loc[hourly_avg[ridership_col].idxmax(), "hour"]
    st.info(
        f"🕔 **Peak Hour:** {int(peak_hour)}:00 with the highest average ridership.\n"
        f"📊 Showing *average passengers per hour* based on all records for {day_type.lower()}s."
    )

else:
    st.warning("No hourly data available for the selected line and day type.")

# Heatmap (hour vs day)
st.subheader("🔥 Heatmap of Ridership by Hour and Day")
if "day_type" in hourly_filtered.columns:
    pivot_df = hourly_filtered.pivot_table(
        values="ridership",
        index="hour",
        columns="day_type",
        aggfunc="mean"
    )
    fig_heat = px.imshow(
        pivot_df,
        title="Average Ridership Heatmap",
        labels=dict(x="Day Type", y="Hour", color="Avg Passengers"),
        color_continuous_scale="YlOrRd"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# =====================
# ROLE-BASED RECOMMENDATION
# =====================
st.subheader("🧭 Suggested Travel Times")

if not hourly_filtered.empty:
    avg_ridership = hourly_filtered.groupby("hour")["ridership"].mean().reset_index()

    if role == "Tourist":
        # Recommend hours with low ridership
        threshold = avg_ridership["ridership"].quantile(0.3)
        recommended = avg_ridership[avg_ridership["ridership"] <= threshold]
        st.success(f"**Recommended Hours for Tourists (Least Crowded):** {', '.join(map(str, recommended['hour'].astype(int)))}")
    else:
        # Recommend hours that align with worker commuting hours (7–9 AM, 5–7 PM)
        recommended = avg_ridership[
            (avg_ridership["hour"].between(7, 9)) |
            (avg_ridership["hour"].between(17, 19))
        ]
        st.info(f"**Typical Worker Commute Hours (High Demand):** {', '.join(map(str, recommended['hour'].astype(int)))}")

    fig_rec = px.line(
        avg_ridership,
        x="hour",
        y="ridership",
        title=f"Hourly Ridership with {role} Recommendations",
        labels={"hour": "Hour of Day", "ridership": "Avg Passengers"},
    )
    fig_rec.add_hline(y=threshold if role == "Tourist" else avg_ridership["ridership"].quantile(0.7),
                      line_dash="dot", annotation_text="Recommendation Threshold", annotation_position="top left")
    st.plotly_chart(fig_rec, use_container_width=True)

# =====================
# FOOTER
# =====================
st.markdown("---")
st.caption("Developed by RideWise Team — Universiti Teknologi PETRONAS © 2025")
