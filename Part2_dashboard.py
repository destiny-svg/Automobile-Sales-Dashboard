# Part2_dashboard.py
# Dash app for Final Assignment - Part 2
# Uses ONLY the hosted CSV; no local file is required.

import pandas as pd
import numpy as np
from dash import Dash, html, dcc, Input, Output, callback
import plotly.express as px

# ---------------------------------------------------------------------
# 1) Data: load once from the hosted URL
# ---------------------------------------------------------------------
URL = ("https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/"
       "IBMDeveloperSkillsNetwork-DV0101EN-SkillsNetwork/Data%20Files/"
       "historical_automobile_sales.csv")

df = pd.read_csv(URL)

# Basic cleaning / typing
df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
df["Month"] = df["Month"].astype(str)
df["Recession"] = pd.to_numeric(df["Recession"], errors="coerce").fillna(0).astype(int)

# Keep only columns we’ll reference; if any are missing, create safe fallbacks
for col, default in [
    ("Automobile_Sales", 0.0),
    ("Vehicle_Type", "Unknown"),
    ("Advertising_Expenditure", 0.0),
    ("unemployment_rate", np.nan),
]:
    if col not in df.columns:
        df[col] = default

# A helper for empty-safe charts
def _empty_fig(title):
    fig = px.scatter(title=title)
    fig.update_layout(xaxis={'visible': False}, yaxis={'visible': False},
                      annotations=[dict(text="No data", x=0.5, y=0.5, showarrow=False)])
    return fig

# Controls
years = sorted([int(y) for y in df["Year"].dropna().unique().tolist()])

# ---------------------------------------------------------------------
# 2) App & Layout
# ---------------------------------------------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Automobile Sales Dashboard"

controls = html.Div(
    [
        html.H2("Controls"),
        html.Label("Report"),
        dcc.Dropdown(
            id="report-dd",
            value="Yearly Statistics",
            clearable=False,
            options=[
                {"label": "Yearly Statistics", "value": "Yearly Statistics"},
                {"label": "Recession Period Statistics", "value": "Recession Period Statistics"},
            ],
        ),
        html.Br(),
        html.Label("Year"),
        dcc.Dropdown(
            id="year-dd",
            options=[{"label": str(y), "value": y} for y in years],
            value=years[-1] if years else None,
            clearable=False,
        ),
        html.Div(id="year-help", style={"marginTop": "6px", "fontSize": 12, "color": "#666"}),
    ],
    className="three columns",
    style={"minWidth": 300, "padding": "12px", "borderRight": "1px solid #eee"},
)

# 2×2 grid of charts
grid = html.Div(
    [
        html.Div(
            [
                dcc.Graph(id="fig-1"),
                dcc.Graph(id="fig-2"),
            ],
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
        ),
        html.Div(
            [
                dcc.Graph(id="fig-3"),
                dcc.Graph(id="fig-4"),
            ],
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "16px"},
        ),
    ],
    className="nine columns",
    style={"padding": "12px", "width": "100%"},
)

app.layout = html.Div(
    [
        html.H1("Automobile Sales Dashboard", style={"textAlign": "center"}),
        html.Div([controls, grid], style={"display": "flex", "gap": "16px"}),
    ],
    style={"margin": "12px"},
)

# ---------------------------------------------------------------------
# 3) Callbacks
# ---------------------------------------------------------------------

# Enable/disable Year dropdown based on report type
@callback(
    Output("year-dd", "disabled"),
    Output("year-help", "children"),
    Input("report-dd", "value"),
)
def toggle_year_dropdown(report_type):
    if report_type == "Yearly Statistics":
        return False, "Year is enabled for Yearly Statistics."
    return True, "Year is disabled for Recession Period Statistics."

# Main plotting callback (returns 4 figures)
@callback(
    Output("fig-1", "figure"),
    Output("fig-2", "figure"),
    Output("fig-3", "figure"),
    Output("fig-4", "figure"),
    Input("report-dd", "value"),
    Input("year-dd", "value"),
)
def update_charts(report_type, year_value):
    # Defensive: if no year is selected yet (first render), pick last one
    if year_value is None and years:
        year_value = years[-1]

    # ---------------------- Yearly Statistics -------------------------
    if report_type == "Yearly Statistics":
        # 1) Yearly automobile sales (whole period) – line chart
        yearly = (df.groupby("Year", as_index=False)["Automobile_Sales"]
                    .mean(numeric_only=True))
        if yearly.empty:
            fig1 = _empty_fig("Yearly Automobile Sales (Average)")
        else:
            fig1 = px.line(yearly, x="Year", y="Automobile_Sales",
                           title="Yearly Automobile Sales (Average over Months)")

        # Data for selected year
        dff = df[df["Year"] == year_value].copy()

        # 2) Total monthly sales for selected year – line chart
        monthly = (dff.groupby("Month", as_index=False)["Automobile_Sales"]
                     .sum(numeric_only=True))
        # preserve month order if the CSV provides numeric months
        try:
            monthly["Month_num"] = monthly["Month"].astype(int)
            monthly = monthly.sort_values("Month_num")
        except Exception:
            pass

        fig2 = (_empty_fig(f"Total Monthly Automobile Sales — {year_value}")
                if monthly.empty else
                px.line(monthly, x="Month", y="Automobile_Sales",
                        title=f"Total Monthly Automobile Sales — {year_value}"))

        # 3) Average vehicles sold by vehicle type (selected year) – bar
        by_type = (dff.groupby("Vehicle_Type", as_index=False)["Automobile_Sales"]
                     .mean(numeric_only=True))
        fig3 = (_empty_fig(f"Average Vehicles Sold by Vehicle Type — {year_value}")
                if by_type.empty else
                px.bar(by_type, x="Vehicle_Type", y="Automobile_Sales",
                       title=f"Average Vehicles Sold by Vehicle Type — {year_value}"))

        # 4) Total advertisement expenditure for each vehicle type (selected year) – pie
        adv = (dff.groupby("Vehicle_Type", as_index=False)["Advertising_Expenditure"]
                 .sum(numeric_only=True))
        fig4 = (_empty_fig(f"Ad Expenditure Share by Vehicle Type — {year_value}")
                if adv.empty else
                px.pie(adv, names="Vehicle_Type", values="Advertising_Expenditure",
                       title=f"Ad Expenditure Share by Vehicle Type — {year_value}"))
        return fig1, fig2, fig3, fig4

    # ------------------ Recession Period Statistics -------------------
    rec = df[df["Recession"] == 1].copy()

    # 1) Average sales fluctuation over recession years – line
    rec_yearly = (rec.groupby("Year", as_index=False)["Automobile_Sales"]
                    .mean(numeric_only=True))
    fig1 = (_empty_fig("Avg Automobile Sales during Recession (Year-wise)")
            if rec_yearly.empty else
            px.line(rec_yearly, x="Year", y="Automobile_Sales",
                    title="Avg Automobile Sales during Recession (Year-wise)"))

    # 2) Average number of vehicles sold by vehicle type during recessions – bar
    rec_type_avg = (rec.groupby("Vehicle_Type", as_index=False)["Automobile_Sales"]
                      .mean(numeric_only=True))
    fig2 = (_empty_fig("Avg Vehicles Sold by Vehicle Type (Recession)")
            if rec_type_avg.empty else
            px.bar(rec_type_avg, x="Vehicle_Type", y="Automobile_Sales",
                   title="Avg Vehicles Sold by Vehicle Type (Recession)"))

    # 3) Advertising expenditure share by vehicle type during recessions – pie
    rec_adv = (rec.groupby("Vehicle_Type", as_index=False)["Advertising_Expenditure"]
                 .sum(numeric_only=True))
    fig3 = (_empty_fig("Ad Expenditure Share by Vehicle Type (Recession)")
            if rec_adv.empty else
            px.pie(rec_adv, names="Vehicle_Type", values="Advertising_Expenditure",
                   title="Ad Expenditure Share by Vehicle Type (Recession)"))

    # 4) Effect of unemployment rate on vehicle type and sales (Recession)
    #    A scatter with size ~ sales, color = type, x=unemployment_rate, y=sales
    rec_u = rec.dropna(subset=["unemployment_rate"]).copy()
    if rec_u.empty:
        fig4 = _empty_fig("Unemployment vs Sales (Recession)")
    else:
        fig4 = px.scatter(
            rec_u, x="unemployment_rate", y="Automobile_Sales",
            color="Vehicle_Type", size="Automobile_Sales",
            title="Unemployment vs Automobile Sales by Vehicle Type (Recession)",
            hover_data=["Year", "Month"]
        )
        fig4.update_layout(xaxis_title="Unemployment Rate", yaxis_title="Automobile Sales")

    return fig1, fig2, fig3, fig4

# ---------------------------------------------------------------------
# 4) Main
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Use a port that won’t clash with anything else
    app.run(debug=True, port=8069)
