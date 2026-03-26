import pandas as pd
import plotly.express as px

# -----------------------------
# Data Helpers
# -----------------------------

def filter_country(df, country="KENYA"):
    """Filter dataframe to a specific country (default Kenya)."""
    return df[df['country'].str.upper() == country.upper()]

def aggregate_global(df, group_col, agg_col):
    """Aggregate global totals by a grouping column."""
    return df.groupby(group_col).agg({agg_col:"sum"}).reset_index()

def compare_kenya_global(df, group_col, agg_col):
    """Return a dataframe comparing Kenya vs Global for a given metric."""
    kenya = filter_country(df)
    global_df = aggregate_global(df, group_col, agg_col)

    combined = pd.DataFrame({
        group_col: global_df[group_col],
        "Global": global_df[agg_col],
        "Kenya": kenya.groupby(group_col)[agg_col].sum().reindex(global_df[group_col]).fillna(0).values
    })
    return combined

# -----------------------------
# Chart Helpers
# -----------------------------

def bar_compare(df, group_col, agg_col, title):
    """Grouped bar chart comparing Kenya vs Global."""
    combined = compare_kenya_global(df, group_col, agg_col)
    fig = px.bar(
        combined.melt(id_vars=group_col, value_vars=["Global","Kenya"]),
        x=group_col,
        y="value",
        color="variable",
        barmode="group",
        title=title
    )
    return fig

def line_trend(df, x_col, y_col, country="KENYA", title="Trend Comparison"):
    """Line chart showing Kenya vs Global trend over time."""
    kenya = filter_country(df, country).groupby(x_col).agg({y_col:"sum"}).reset_index()
    global_df = df.groupby(x_col).agg({y_col:"sum"}).reset_index()

    kenya["scope"] = "Kenya"
    global_df["scope"] = "Global"
    combined = pd.concat([kenya, global_df])

    fig = px.line(combined, x=x_col, y=y_col, color="scope", title=title)
    return fig

# -----------------------------
# Formatting Helpers
# -----------------------------

def format_number(num):
    """Format numbers with commas."""
    return f"{num:,}"

def calculate_delta(series):
    """Calculate delta and percent change for metrics."""
    if len(series) < 2:
        return 0, 0
    current = series.iloc[-1]
    previous = series.iloc[-2]
    delta = current - previous
    delta_percent = (delta / previous * 100) if previous != 0 else 0
    return delta, delta_percent
