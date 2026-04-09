# app.py  v2.3.0 — two-page app: overview + daily trade view
import os, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import Dash, html, dcc, callback, Input, Output, State, ctx
from dotenv import load_dotenv
from dashboard.helpers import (
    load_trades, load_symbols, get_symbol_name,
    stat_card, empty_fig, base_layout,
    DATA_FILE, SYMBOLS_FILE,
    BG, PANEL, CARD, BORDER, TEXT, MUTED, GOLD, UP, DOWN,
)
from dashboard.scenarios import (
    SC_COLOURS, build_scenarios, calc_scenario_exposure,
)
from dashboard.journal import (
    build_daily_summary, calc_exposure_drawdown, SESSIONS,
)
from dashboard.floating_pnl import build_floating_pnl

BASE_DIR    = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

SYMBOL      = os.getenv("CTRADER_SYMBOL", "XAUUSD")
APP_VERSION = "2.3.0"

TIMEFRAMES = [
    {"label": "All", "days": 9999},
    {"label": "4M",  "days": 120},
    {"label": "3M",  "days": 90},
    {"label": "2M",  "days": 60},
    {"label": "1M",  "days": 30},
    {"label": "3W",  "days": 21},
    {"label": "2W",  "days": 14},
    {"label": "1W",  "days": 7},
]

app = Dash(__name__, title="Trading Journal", suppress_callback_exceptions=True)

# ── Global CSS fixes ──────────────────────────────────────────
# Fix date picker: white text on dark background, dark dropdown
app.index_string = '''<!DOCTYPE html>
<html>
<head>
{%metas%}
<title>{%title%}</title>
{%favicon%}
{%css%}
<style>
  /* Date picker input box */
  .DateInput_input {
    background: #1e1e1e !important;
    color: #e8e8e8 !important;
    border: 1px solid #333 !important;
    font-family: monospace !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 8px 12px !important;
    border-radius: 6px !important;
    width: auto !important;
    min-width: 130px !important;
  }
  .DateInput_input__focused {
    border-color: #7eb8f7 !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(126,184,247,0.2) !important;
  }
  .DateInput_input::placeholder {
    color: #666 !important;
  }
  .SingleDatePickerInput {
    background: #1e1e1e !important;
    border: none !important;
    border-radius: 6px !important;
  }
  .SingleDatePickerInput__withBorder {
    border: 1px solid #333 !important;
    border-radius: 6px !important;
  }
  .DateInput {
    background: #1e1e1e !important;
    border-radius: 6px !important;
  }
  /* Date picker calendar popup */
  .DayPicker, .DayPicker__withBorder {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
  }
  .CalendarMonth_caption strong,
  .DayPickerNavigation_button,
  .DayPicker_weekHeader_li small {
    color: #e0e0e0 !important;
  }
  .CalendarDay__default {
    background: #1a1a1a !important;
    color: #e0e0e0 !important;
    border-color: #2a2a2a !important;
  }
  .CalendarDay__default:hover {
    background: #2a2a2a !important;
    color: #7eb8f7 !important;
  }
  .CalendarDay__selected {
    background: #7eb8f7 !important;
    color: #0a0a0a !important;
    border-color: #7eb8f7 !important;
    font-weight: 700 !important;
  }
  .CalendarDay__selected:hover {
    background: #5a9fd4 !important;
  }
  .DayPickerNavigation_button__default {
    background: #1a1a1a !important;
    border-color: #2a2a2a !important;
    color: #e0e0e0 !important;
  }
  .DayPickerNavigation_button__default:hover {
    background: #2a2a2a !important;
  }
  .CalendarMonthGrid {
    background: #1a1a1a !important;
  }
  .CalendarMonth {
    background: #1a1a1a !important;
  }
  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0a0a0a; }
  ::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #7eb8f7; }
</style>
</head>
<body>
{%app_entry%}
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
</html>'''

# ── Helpers ───────────────────────────────────────────────────
# Helper functions imported from dashboard/helpers.py
# load_trades, load_symbols, get_symbol_name, stat_card, empty_fig, base_layout

def nav_btn(label, page_id, active=False):
    return html.Button(label, id=page_id, n_clicks=0, style={
        "fontSize": "13px", "padding": "10px 20px",
        "background": GOLD if active else "transparent",
        "color": BG if active else TEXT,
        "border": f"1px solid {GOLD if active else BORDER}",
        "borderRadius": "8px", "cursor": "pointer",
        "fontWeight": "700",
        "letterSpacing": "0.5px",
    })

def tf_btn(label, active=False):
    return html.Button(label, id=f"tf-{label}", n_clicks=0, style={
        "fontSize": "14px", "padding": "10px 22px",
        "background": GOLD if active else CARD,
        "color": BG if active else TEXT,
        "border": f"2px solid {GOLD if active else BORDER}",
        "borderRadius": "8px", "cursor": "pointer",
        "fontWeight": "700",
        "letterSpacing": "1px",
    })

# ── Shared header ─────────────────────────────────────────────
def header(active_page="overview"):
    return html.Div(style={
        "display": "flex", "justifyContent": "space-between",
        "alignItems": "center", "marginBottom": "24px",
        "paddingBottom": "20px", "borderBottom": f"1px solid {BORDER}"},
    children=[
        html.Div([
            html.Span("TRADING JOURNAL", style={"fontSize": "22px", "fontWeight": "800",
                                      "color": GOLD, "letterSpacing": "2px"}),
            html.Span("  GOLD & METALS  ·  DEEPALI",
                      style={"fontSize": "10px", "color": MUTED, "letterSpacing": "3px"}),
        ]),
        html.Div(style={"display": "flex", "gap": "8px"}, children=[
            nav_btn("📊  Overview",    "nav-overview", active=(active_page=="overview")),
            nav_btn("📋  Journal",     "nav-journal",  active=(active_page=="journal")),
            nav_btn("🔍  Scenarios",   "nav-scenarios",active=(active_page=="scenarios")),
            nav_btn("📱  Mobile",      "nav-mobile",   active=(active_page=="mobile")),
        ]),
    ])

# ── Page 1: Overview ──────────────────────────────────────────
page_overview = html.Div(id="page-overview", children=[
    header("overview"),

    # Timeframe selector
    html.Div(style={"display": "flex", "alignItems": "center",
                    "gap": "8px", "marginBottom": "20px"},
    children=[
        html.Div("Period:", style={"fontSize": "10px", "color": MUTED, "marginRight": "4px"}),
        *[tf_btn(tf["label"], active=(tf["label"] == "All")) for tf in TIMEFRAMES],
    ]),

    html.Div(id="stat-cards",
             style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
                    "gap": "12px", "marginBottom": "20px"}),

    html.Div([
        html.Div(id="pnl-title", style={"fontSize": "9px", "letterSpacing": "2px",
                                         "textTransform": "uppercase", "color": MUTED,
                                         "marginBottom": "12px"}),
        dcc.Graph(id="pnl-chart", config={"displayModeBar": False}, style={"height": "280px"}),
    ], style={"background": PANEL, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"}),

    # ── Daily charts embedded in overview ──────────────────────
    html.Div(style={"display": "flex", "alignItems": "center",
                    "gap": "16px", "marginBottom": "16px",
                    "background": PANEL, "border": f"1px solid {BORDER}",
                    "borderRadius": "10px", "padding": "16px 20px"},
    children=[
        html.Div("Date:", style={"fontSize": "10px", "color": MUTED,
                                  "letterSpacing": "2px", "textTransform": "uppercase"}),
        dcc.DatePickerSingle(
            id="date-picker",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            display_format="DD MMM YYYY",
            style={"fontFamily": "monospace", "color": TEXT,
                   "background": CARD},
        ),
        html.Div(id="day-summary",
                 style={"fontSize": "11px", "color": MUTED, "marginLeft": "auto"}),
    ]),

    html.Div(id="daily-charts"),

    html.Div(id="last-updated",
             style={"fontSize": "10px", "color": MUTED, "marginTop": "12px", "textAlign": "right"}),

])



# ── Page 4: Daily Journal ─────────────────────────────────────
page_journal = html.Div(id="page-journal", children=[
    header("journal"),

    # Controls row
    html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between",
                    "marginBottom": "20px"},
    children=[
        html.Div(style={"display": "flex", "alignItems": "center", "gap": "16px"},
        children=[
            html.Div("Sort:", style={"fontSize": "10px", "color": MUTED,
                                     "letterSpacing": "2px", "textTransform": "uppercase"}),
            html.Button("Date ↓",  id="sort-date",  n_clicks=0,
                        style={"fontSize": "13px", "padding": "8px 16px", "background": GOLD,
                               "color": BG, "border": f"1px solid {GOLD}",
                               "borderRadius": "6px", "cursor": "pointer", "fontWeight": "700"}),
            html.Button("P&L",     id="sort-pnl",   n_clicks=0,
                        style={"fontSize": "13px", "padding": "8px 16px", "background": CARD,
                               "color": TEXT, "border": f"1px solid {BORDER}",
                               "borderRadius": "6px", "cursor": "pointer"}),
            html.Button("Trades",  id="sort-trades", n_clicks=0,
                        style={"fontSize": "13px", "padding": "8px 16px", "background": CARD,
                               "color": TEXT, "border": f"1px solid {BORDER}",
                               "borderRadius": "6px", "cursor": "pointer"}),
        ]),
        html.Button("⬇  Download CSV", id="download-btn", n_clicks=0,
                    style={"fontSize": "13px", "padding": "10px 22px", "background": CARD,
                           "color": TEXT, "border": f"1px solid {BORDER}",
                           "borderRadius": "6px", "cursor": "pointer"}),
        html.Button("📊  Calculate Exposure DD", id="live-dd-btn", n_clicks=0,
                    style={"fontSize": "13px", "padding": "10px 22px", "background": CARD,
                           "color": TEXT, "border": f"1px solid {BORDER}",
                           "borderRadius": "6px", "cursor": "pointer"}),
        html.Div("(instant — from CSV)", id="live-dd-hint",
                 style={"fontSize": "10px", "color": MUTED}),
    ]),

    # Summary stats bar
    html.Div(id="journal-summary",
             style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
                    "gap": "12px", "marginBottom": "20px"}),

    # Table
    dcc.Loading(type="circle", color=GOLD, children=
        html.Div(id="journal-table",
                 style={"background": PANEL, "border": f"1px solid {BORDER}",
                        "borderRadius": "10px", "padding": "20px"})
    ),

    dcc.Download(id="journal-download"),
    dcc.Store(id="sort-store",   data="date"),
    dcc.Store(id="live-dd-store", data={}),
])

# ── Page 5: Scenarios ────────────────────────────────────────
page_scenarios = html.Div(id="page-scenarios", children=[
    header("scenarios"),

    # Controls row
    html.Div(style={"display": "flex", "alignItems": "center", "gap": "16px",
                    "marginBottom": "20px", "background": PANEL,
                    "border": f"1px solid {BORDER}",
                    "borderRadius": "10px", "padding": "16px 20px"},
    children=[
        html.Div("Date:", style={"fontSize": "13px", "color": TEXT,
                                  "letterSpacing": "1px", "textTransform": "uppercase", "fontWeight": "600"}),
        dcc.DatePickerSingle(
            id="sc-date-picker",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            display_format="DD MMM YYYY",
            style={"fontFamily": "monospace", "color": TEXT, "background": CARD},
        ),
        html.Div(id="sc-day-summary",
                 style={"fontSize": "14px", "color": TEXT, "marginLeft": "auto", "fontWeight": "600"}),
        html.Button("🕯  Load Chart", id="sc-chart-btn", n_clicks=0,
                    style={"fontSize": "13px", "padding": "9px 18px",
                           "background": CARD, "color": TEXT,
                           "border": f"1px solid {BORDER}",
                           "borderRadius": "6px", "cursor": "pointer"}),
        html.Button("⬇  Download CSV", id="sc-download-btn", n_clicks=0,
                    style={"fontSize": "13px", "padding": "9px 18px",
                           "background": CARD, "color": TEXT,
                           "border": f"1px solid {BORDER}",
                           "borderRadius": "6px", "cursor": "pointer"}),
        html.Button("📉  Download Floating P&L", id="sc-float-btn", n_clicks=0,
                    style={"fontSize": "13px", "padding": "9px 18px",
                           "background": CARD, "color": TEXT,
                           "border": f"1px solid {BORDER}",
                           "borderRadius": "6px", "cursor": "pointer"}),
    ]),

    # Scenario summary cards
    html.Div(id="sc-cards",
             style={"display": "flex", "gap": "12px", "flexWrap": "wrap",
                    "marginBottom": "20px"}),

    # Scenarios table
    html.Div([
        html.Div("Scenario log", style={"fontSize": "12px", "letterSpacing": "2px",
                                         "textTransform": "uppercase", "color": TEXT,
                                         "marginBottom": "12px"}),
        html.Div(id="sc-table"),
    ], style={"background": PANEL, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"}),

    # Market chart — loads when button clicked
    html.Div([
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                        "alignItems": "center", "marginBottom": "12px"},
        children=[
            html.Div(id="sc-chart-title",
                     style={"fontSize": "12px", "letterSpacing": "1px",
                            "textTransform": "uppercase", "color": TEXT, "fontWeight": "600"}),
        ]),
        dcc.Loading(type="circle", color=GOLD, children=
            html.Div(id="sc-market-chart-wrap",
                     children=html.Div(
                         "Click  🕯 Load Chart  above to overlay your trades on the market",
                         style={"color": TEXT, "fontSize": "12px",
                                "padding": "40px", "textAlign": "center"}
                     ))
        ),
    ], style={"background": PANEL, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "20px"}),

    dcc.Download(id="sc-download"),
    dcc.Download(id="sc-float-download"),
    dcc.Store(id="sc-store", data={}),
])


# ── Page 6: Mobile View ───────────────────────────────────────
page_mobile = html.Div(id="page-mobile", style={
    "maxWidth": "480px", "margin": "0 auto",
    "paddingBottom": "80px", "fontFamily": "monospace",
}, children=[
    html.Div(style={
        "background": PANEL, "borderBottom": f"1px solid {BORDER}",
        "padding": "16px 20px",
        "display": "flex", "justifyContent": "space-between", "alignItems": "center",
    }, children=[
        html.Div([
            html.Div("TRADING JOURNAL",
                     style={"fontSize": "16px", "fontWeight": "800",
                            "color": GOLD, "letterSpacing": "2px"}),
            html.Div("GOLD & METALS",
                     style={"fontSize": "10px", "color": MUTED}),
        ]),
        html.Button("🔄 Refresh", id="mob-refresh-real", n_clicks=0,
                    style={"fontSize": "12px", "background": CARD,
                           "border": f"1px solid {BORDER}", "color": TEXT,
                           "cursor": "pointer", "padding": "8px 12px",
                           "borderRadius": "8px", "fontWeight": "700"}),
    ]),

    # mob-content is in app.layout — rendered here via CSS show/hide
    html.Div(id="mob-content-view", style={"padding": "16px",
             "minHeight": "300px"}),

    # Bottom tabs
    html.Div(style={
        "position": "fixed", "bottom": "0", "left": "0", "right": "0",
        "maxWidth": "480px", "margin": "0 auto",
        "background": PANEL, "borderTop": f"2px solid {BORDER}",
        "display": "flex", "zIndex": "999",
    }, children=[
        html.Button("📊 Overview",  id="mob-tab-overview",  n_clicks=0,
                    style={"flex":"1","fontSize":"11px","padding":"13px 2px",
                           "background":GOLD,"color":BG,"border":"none",
                           "cursor":"pointer","fontWeight":"800"}),
        html.Button("📈 P&L",       id="mob-tab-pnl",       n_clicks=0,
                    style={"flex":"1","fontSize":"11px","padding":"13px 2px",
                           "background":CARD,"color":TEXT,"border":"none",
                           "cursor":"pointer","fontWeight":"700"}),
        html.Button("📅 Weekly",    id="mob-tab-weekly",    n_clicks=0,
                    style={"flex":"1","fontSize":"11px","padding":"13px 2px",
                           "background":CARD,"color":TEXT,"border":"none",
                           "cursor":"pointer","fontWeight":"700"}),
        html.Button("📋 Journal",   id="mob-tab-journal",   n_clicks=0,
                    style={"flex":"1","fontSize":"11px","padding":"13px 2px",
                           "background":CARD,"color":TEXT,"border":"none",
                           "cursor":"pointer","fontWeight":"700"}),
        html.Button("🔍 Scenarios", id="mob-tab-scenarios", n_clicks=0,
                    style={"flex":"1","fontSize":"11px","padding":"13px 2px",
                           "background":CARD,"color":TEXT,"border":"none",
                           "cursor":"pointer","fontWeight":"700"}),
    ]),
])


# ── App layout ────────────────────────────────────────────────
app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh", "padding": "28px",
           "fontFamily": "monospace", "color": TEXT},
    children=[
        dcc.Store(id="page-store", data="overview"),
        dcc.Store(id="tf-store", data="All"),
        dcc.Store(id="mob-tab-store", data="overview"),
        dcc.Interval(id="interval", interval=60_000, n_intervals=0),
        html.Button("🔄", id="mob-refresh", n_clicks=0,
                    style={"display":"none"}),
        html.Div(id="mob-content", style={"display":"none"}),
        html.Div(id="page-content"),
    ]
)

# ── Page routing ──────────────────────────────────────────────
@callback(
    Output("page-store",    "data"),
    Input("nav-overview",   "n_clicks"),
    Input("nav-journal",    "n_clicks"),
    Input("nav-scenarios",  "n_clicks"),
    prevent_initial_call=True,
)
def switch_page(*_):
    triggered = ctx.triggered_id
    if triggered == "nav-journal":      return "journal"
    if triggered == "nav-scenarios":    return "scenarios"
    if triggered == "nav-mobile":       return "mobile"
    if triggered == "mob-nav-overview":  return "overview"
    if triggered == "mob-nav-journal":   return "journal"
    if triggered == "mob-nav-scenarios": return "scenarios"
    return "overview"

@callback(
    Output("page-content", "children"),
    Input("page-store",    "data"),
)
def render_page(page):
    if page == "daily":     return page_daily
    if page == "journal":   return page_journal
    if page == "scenarios": return page_scenarios
    if page == "mobile":    return page_mobile
    return page_overview

# ── Overview: timeframe store ─────────────────────────────────
@callback(
    Output("tf-store", "data"),
    *[Input(f"tf-{tf['label']}", "n_clicks") for tf in TIMEFRAMES],
    prevent_initial_call=True,
)
def set_tf(*_):
    return ctx.triggered_id.replace("tf-", "") if ctx.triggered_id else "All"

@callback(
    *[Output(f"tf-{tf['label']}", "style") for tf in TIMEFRAMES],
    Input("tf-store", "data"),
)
def update_tf_styles(active):
    return [{
        "fontSize": "13px", "padding": "9px 18px",
        "background": GOLD if tf["label"] == active else CARD,
        "color": BG if tf["label"] == active else TEXT,
        "border": f"1px solid {GOLD if tf['label'] == active else BORDER}",
        "borderRadius": "6px", "cursor": "pointer",
        "fontWeight": "700" if tf["label"] == active else "400",
    } for tf in TIMEFRAMES]

# ── Overview: main data callback ──────────────────────────────
@callback(
    Output("stat-cards",   "children"),
    Output("pnl-chart",    "figure"),
    Output("last-updated", "children"),
    Output("pnl-title",    "children"),
    Input("tf-store",      "data"),
    Input("interval",      "n_intervals"),
)
def update_overview(active_tf, _):
    df_all = load_trades()
    if df_all is None:
        empty = empty_fig("No data — run fetch_data.py first")
        cards = [stat_card("No data", "—") for _ in range(5)]
        return cards, empty, "No data", "Cumulative P&L"

    days   = next((t["days"] for t in TIMEFRAMES if t["label"] == active_tf), 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    df     = df_all if days == 9999 else df_all[df_all["time"] >= cutoff].copy()

    if df.empty:
        empty = empty_fig(f"No trades in the last {active_tf}")
        cards = [stat_card(f"No trades ({active_tf})", "—") for _ in range(5)]
        return cards, empty, "", f"Cumulative P&L · {active_tf}"

    total_pnl = df["pnl"].sum()
    wins      = df[df["pnl"] > 0]
    losses    = df[df["pnl"] < 0]
    win_rate  = len(wins) / len(df) * 100
    pnl_color = UP if total_pnl >= 0 else DOWN

    daily_avg = total_pnl / max((df["time"].max() - df["time"].min()).days, 1)
    cards = [
        stat_card("Total P&L", f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}',
                  pnl_color, f"£{daily_avg:+.2f}/day avg"),
        stat_card("Trades", str(len(df)), TEXT, f"{len(wins)}W  {len(losses)}L"),
        stat_card("Win rate", f"{win_rate:.1f}%", UP if win_rate >= 50 else DOWN),
        stat_card("Best",  f'+£{df["pnl"].max():.2f}', UP),
        stat_card("Worst", f'£{df["pnl"].min():.2f}',  DOWN),
    ]

    df = df.sort_values("time").reset_index(drop=True)
    df["cum_pnl"] = df["pnl"].cumsum()

    pnl_fig = go.Figure()
    pnl_fig.add_hline(y=0, line_color=BORDER, line_width=1)
    pnl_fig.add_trace(go.Scatter(
        x=df["time"], y=df["cum_pnl"], mode="lines+markers",
        line={"color": GOLD, "width": 2, "shape": "spline"},
        marker={"size": 5, "color": [UP if v >= 0 else DOWN for v in df["cum_pnl"]]},
        fill="tozeroy", fillcolor="rgba(38,166,154,0.12)",
        hovertemplate="%{x|%d %b %H:%M}<br>£%{y:.2f}<extra></extra>",
    ))
    pnl_fig.update_layout(**base_layout())

    updated = f'Updated {datetime.now().strftime("%H:%M:%S")}  ·  {len(df)} trades  ·  {"+" if total_pnl>=0 else ""}£{total_pnl:.2f}'
    return cards, pnl_fig, updated, f"Cumulative P&L · {active_tf}"

# ── Daily view callback ───────────────────────────────────────
@callback(
    Output("daily-charts", "children"),
    Output("day-summary",  "children"),
    Input("date-picker",   "date"),
)
def update_daily(selected_date):
    if not selected_date:
        return html.Div("Pick a date above.", style={"color": MUTED}), ""

    df_all  = load_trades()
    symbols = load_symbols()

    if df_all is None:
        return html.Div("No data — run fetch_data.py first.",
                        style={"color": MUTED}), ""

    # Filter to selected date (UTC)
    sel_dt    = pd.to_datetime(selected_date).tz_localize("UTC")
    sel_end   = sel_dt + timedelta(days=1)
    df_day    = df_all[(df_all["time"] >= sel_dt) & (df_all["time"] < sel_end)].copy()

    if df_day.empty:
        return html.Div([
            html.Div("📭  No trades on this day.",
                     style={"color": TEXT, "fontSize": "14px",
                            "padding": "40px 0", "textAlign": "center"}),
            html.Div("Try another date using the picker above.",
                     style={"color": TEXT, "fontSize": "11px", "textAlign": "center"}),
        ]), "No trades this day"

    total_pnl = df_day["pnl"].sum()
    summary   = (f"{len(df_day)} trades  ·  "
                 f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}  ·  '
                 f'{df_day["symbol_id"].nunique()} symbol(s)')

    # One chart per symbol traded that day
    charts = []
    for sym_id, df_sym in df_day.groupby("symbol_id"):
        sym_name  = get_symbol_name(sym_id, symbols)
        sym_pnl   = df_sym["pnl"].sum()
        pnl_color = UP if sym_pnl >= 0 else DOWN
        df_sym    = df_sym.sort_values("time").reset_index(drop=True)
        df_sym["cum_pnl"] = df_sym["pnl"].cumsum()

        # Scatter chart: price over time with buy/sell markers
        fig = go.Figure()

        # Cumulative P&L line
        fig.add_trace(go.Scatter(
            x=df_sym["time"], y=df_sym["cum_pnl"],
            mode="lines", name="Cum P&L",
            line={"color": GOLD, "width": 1.5, "dash": "dot"},
            yaxis="y2",
            hovertemplate="%{x|%H:%M}<br>Cum P&L: £%{y:.2f}<extra></extra>",
        ))

        # Entry price scatter coloured by direction
        for direction, color in [("BUY", UP), ("SELL", DOWN)]:
            mask = df_sym["direction"] == direction
            if mask.any():
                fig.add_trace(go.Scatter(
                    x=df_sym[mask]["time"],
                    y=df_sym[mask]["fill_price"],
                    mode="markers",
                    name=direction,
                    marker={"color": color, "size": 8, "symbol": "circle",
                            "line": {"color": BG, "width": 1}},
                    hovertemplate=(f"{direction}<br>"
                                   "%{x|%H:%M}<br>"
                                   "Price: %{y:.2f}<br>"
                                   "<extra></extra>"),
                ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
            font={"family": "monospace", "color": TEXT, "size": 11},
            margin={"t": 10, "r": 70, "b": 40, "l": 10},
            height=220,
            xaxis={"gridcolor": BORDER, "zerolinecolor": BORDER,
                   "tickfont": {"color": MUTED}, "tickformat": "%H:%M"},
            yaxis={"gridcolor": BORDER, "zerolinecolor": BORDER,
                   "tickfont": {"color": MUTED}, "side": "right",
                   "title": {"text": "price", "font": {"color": TEXT, "size": 9}}},
            yaxis2={"overlaying": "y", "side": "left",
                    "tickprefix": "£", "tickfont": {"color": MUTED},
                    "gridcolor": "rgba(0,0,0,0)",
                    "title": {"text": "cum P&L", "font": {"color": TEXT, "size": 9}}},
            legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": MUTED},
                    "orientation": "h", "x": 0, "y": 1.1},
            hovermode="x unified",
            hoverlabel={"bgcolor": CARD, "font": {"color": TEXT, "family": "monospace"}},
        )

        charts.append(html.Div([
            # Symbol header
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "12px"},
            children=[
                html.Div([
                    html.Span(sym_name, style={"fontSize": "16px", "fontWeight": "800",
                                               "color": GOLD}),
                    html.Span(f"  {len(df_sym)} trades",
                              style={"fontSize": "10px", "color": TEXT,
                                     "marginLeft": "8px"}),
                ]),
                html.Div(f'{"+" if sym_pnl>=0 else ""}£{sym_pnl:.2f}',
                         style={"fontSize": "18px", "fontWeight": "800",
                                "color": pnl_color}),
            ]),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px",
                  "marginBottom": "16px"}))

    return html.Div(charts), summary


# ── Market view: timeframe store ─────────────────────────────
# SESSIONS imported from dashboard/journal.py

def add_session_boxes(fig, date_utc):
    """Add shaded session regions to a candlestick figure for a given UTC date."""
    from datetime import timedelta
    d = pd.Timestamp(date_utc).normalize().tz_localize("UTC") if pd.Timestamp(date_utc).tzinfo is None else pd.Timestamp(date_utc).normalize()

    for sess in SESSIONS:
        start_h = sess["start"]
        end_h   = sess["end"]

        if start_h < end_h:
            # Same day
            x0 = d + timedelta(hours=start_h)
            x1 = d + timedelta(hours=end_h)
            _add_box(fig, x0, x1, sess)
        else:
            # Crosses midnight — two segments: prev day end→midnight, midnight→next day
            # Segment 1: start_h → end of day
            x0 = d + timedelta(hours=start_h)
            x1 = d + timedelta(hours=24)
            _add_box(fig, x0, x1, sess, show_label=True)
            # Segment 2: start of next day → end_h
            x0 = d + timedelta(hours=24)
            x1 = d + timedelta(hours=24 + end_h)
            _add_box(fig, x0, x1, sess, show_label=False)

def _add_box(fig, x0, x1, sess, show_label=True):
    fig.add_vrect(
        x0=x0, x1=x1,
        fillcolor=sess["color"],
        layer="below",
        line_width=0,
    )
    if show_label:
        fig.add_annotation(
            x=x0, xanchor="left",
            y=1.0, yanchor="top", yref="paper",
            text=sess["name"],
            showarrow=False,
            font={"size": 9, "color": sess["label_color"]},
            bgcolor="rgba(0,0,0,0)",
            borderpad=2,
        )


_DIGITS_CACHE = {}

def digits_from_raw(raw_value, symbol_id):
    """Find correct price divisor by matching raw bar value to known fill_price."""
    import math
    # Use cache — digits don't change per symbol
    if symbol_id in _DIGITS_CACHE:
        d = _DIGITS_CACHE[symbol_id]
        print(f"  → digits={d} (cached), price≈{raw_value/(10**d):.2f}")
        return d
    df = load_trades()
    if df is not None:
        sym_trades = df[df["symbol_id"] == symbol_id]
        if not sym_trades.empty and raw_value > 0:
            target = sym_trades["fill_price"].median()
            if target > 0:
                d = round(math.log10(raw_value / target))
                d = max(0, min(d, 10))
                _DIGITS_CACHE[symbol_id] = d
                print(f"  → digits={d}, price≈{raw_value/(10**d):.2f} (target={target:.2f})")
                return d
    # Fallback: find divisor landing in 10–500,000
    for d in range(10):
        if 10 < raw_value / (10**d) < 500_000:
            _DIGITS_CACHE[symbol_id] = d
            return d
    return 5

def fetch_candles_sync(symbol_id, from_dt, to_dt, period, minutes):
    """Fetch OHLCV candles from cTrader using a persistent reactor thread."""
    import warnings, threading
    warnings.filterwarnings("ignore")

    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
            ProtoOAAccountAuthReq,     ProtoOAAccountAuthRes,
            ProtoOAGetTrendbarsReq,    ProtoOAGetTrendbarsRes,
            ProtoOASymbolByIdReq,      ProtoOASymbolByIdRes,
            ProtoOAErrorRes,
        )
        from twisted.internet import reactor
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return None

    CLIENT_ID     = os.getenv("CTRADER_CLIENT_ID")
    CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
    ACCESS_TOKEN  = os.getenv("CTRADER_ACCESS_TOKEN")
    ACCOUNT_ID    = int(os.getenv("CTRADER_ACCOUNT_ID", "0"))
    HOST          = os.getenv("CTRADER_HOST", "live.ctraderapi.com")
    PORT          = int(os.getenv("CTRADER_PORT", "5035"))

    pad     = timedelta(hours=2)
    from_ms = int((from_dt - pad).timestamp() * 1000)
    to_ms   = int((to_dt   + pad).timestamp() * 1000)

    done_event = threading.Event()
    state      = {"candles": None, "digits": 5}
    client     = Client(HOST, PORT, TcpProtocol)

    def extract(message, cls):
        try:    return Protobuf.extract(message, cls)
        except TypeError:
            obj = cls(); obj.ParseFromString(message.payload); return obj

    def finish(candles=None):
        state["candles"] = candles
        done_event.set()
        # Do NOT stop the reactor — just disconnect this client
        try: client.stopService()
        except: pass

    def on_connected(c):
        req = ProtoOAApplicationAuthReq()
        req.clientId = CLIENT_ID; req.clientSecret = CLIENT_SECRET
        c.send(req)

    def on_disconnected(c, reason):
        done_event.set()

    def on_message(c, message):
        ptype = message.payloadType

        if ptype == ProtoOAApplicationAuthRes().payloadType:
            req = ProtoOAAccountAuthReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.accessToken         = ACCESS_TOKEN
            c.send(req)

        elif ptype == ProtoOAAccountAuthRes().payloadType:
            req = ProtoOASymbolByIdReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.symbolId.append(symbol_id)
            c.send(req)

        elif ptype == ProtoOASymbolByIdRes().payloadType:
            # Skip symbol details — we compute digits from raw candle value
            req = ProtoOAGetTrendbarsReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.symbolId            = symbol_id
            req.period              = period
            req.fromTimestamp       = from_ms
            req.toTimestamp         = to_ms
            c.send(req)

        elif ptype == ProtoOAGetTrendbarsRes().payloadType:
            res = extract(message, ProtoOAGetTrendbarsRes)
            if not res.trendbar:
                finish(pd.DataFrame())
                return
            # Compute digits from first bar vs known fill_price
            raw_low = res.trendbar[0].low
            d       = digits_from_raw(raw_low, symbol_id)
            divisor = 10 ** d
            rows    = []
            for bar in res.trendbar:
                low   = bar.low / divisor
                open_ = low + (bar.deltaOpen  / divisor)
                high  = low + (bar.deltaHigh  / divisor)
                close = low + (bar.deltaClose / divisor)
                ts    = datetime.fromtimestamp(
                            bar.utcTimestampInMinutes * 60, tz=timezone.utc)
                rows.append({"time": ts, "open": open_,
                             "high": high, "low": low, "close": close})
            df = pd.DataFrame(rows).sort_values("time")
            print(f"  → {len(rows)} candles, range: {df['low'].min():.2f}–{df['high'].max():.2f}")
            finish(df)

        elif ptype == ProtoOAErrorRes().payloadType:
            err = extract(message, ProtoOAErrorRes)
            print(f"  ✗ cTrader error: {err.errorCode}: {err.description}")
            finish(pd.DataFrame())

    client.setConnectedCallback(on_connected)
    client.setDisconnectedCallback(on_disconnected)
    client.setMessageReceivedCallback(on_message)

    # Start reactor in background thread only if not already running
    if not reactor.running:
        def run_reactor():
            reactor.run(installSignalHandlers=False)
        t = threading.Thread(target=run_reactor, daemon=True)
        t.start()

    # Schedule client connection on the reactor thread
    reactor.callFromThread(client.startService)

    done_event.wait(timeout=45)
    return state["candles"]


# (duplicate removed — see dashboard/journal.py)

# ── Journal: sort buttons ─────────────────────────────────────
@callback(
    Output("sort-store",  "data"),
    Output("sort-date",   "style"),
    Output("sort-pnl",    "style"),
    Output("sort-trades", "style"),
    Input("sort-date",    "n_clicks"),
    Input("sort-pnl",     "n_clicks"),
    Input("sort-trades",  "n_clicks"),
    prevent_initial_call=True,
)
def set_sort2(*_):
    triggered = ctx.triggered_id
    sort_key  = {"sort-date": "date", "sort-pnl": "pnl",
                 "sort-trades": "trades"}.get(triggered, "date")
    def btn_style(active):
        return {"fontSize": "13px", "padding": "8px 16px",
                "background": GOLD if active else CARD,
                "color": BG if active else TEXT,
                "border": f"1px solid {GOLD if active else BORDER}",
                "borderRadius": "6px", "cursor": "pointer",
                "fontWeight": "700" if active else "400"}
    return (sort_key,
            btn_style(sort_key == "date"),
            btn_style(sort_key == "pnl"),
            btn_style(sort_key == "trades"))


# ── Mobile: tab store ────────────────────────────────────────
@callback(
    Output("mob-tab-store",    "data"),
    Output("mob-tab-overview", "style"),
    Output("mob-tab-pnl",      "style"),
    Output("mob-tab-weekly",   "style"),
    Output("mob-tab-journal",  "style"),
    Output("mob-tab-scenarios","style"),
    Input("mob-tab-overview",  "n_clicks"),
    Input("mob-tab-pnl",       "n_clicks"),
    Input("mob-tab-weekly",    "n_clicks"),
    Input("mob-tab-journal",   "n_clicks"),
    Input("mob-tab-scenarios", "n_clicks"),
    prevent_initial_call=True,
)
def set_mob_tab(*_):
    tab_map = {
        "mob-tab-overview":  "overview",
        "mob-tab-pnl":       "pnl",
        "mob-tab-weekly":    "weekly",
        "mob-tab-journal":   "journal",
        "mob-tab-scenarios": "scenarios",
    }
    active = tab_map.get(ctx.triggered_id, "overview")
    tabs   = ["overview","pnl","weekly","journal","scenarios"]
    icons  = {"overview":"📊 Overview","pnl":"📈 P&L","weekly":"📅 Weekly",
              "journal":"📋 Journal","scenarios":"🔍 Scenarios"}

    def tab_style(t):
        is_active = (t == active)
        return {"flex":"1","fontSize":"12px","padding":"12px 4px",
                "background": GOLD if is_active else CARD,
                "color": BG if is_active else TEXT,
                "border":"none","cursor":"pointer","fontWeight":"800" if is_active else "700",
                "whiteSpace":"nowrap"}

    return (active, *[tab_style(t) for t in tabs])


# ── Mobile: main content callback ─────────────────────────────
@callback(
    Output("mob-content-view", "children"),
    Input("mob-tab-store", "data"),
    Input("mob-refresh",   "n_clicks"),
    Input("mob-refresh-real", "n_clicks"),
    Input("page-store",    "data"),
    Input("interval",      "n_intervals"),
)
def update_mobile(tab, _, __, page, ___):
    if page != "mobile":
        raise dash.exceptions.PreventUpdate

    df_all = load_trades()
    if df_all is None:
        return html.Div("No data — run fetch first.",
                        style={"color": MUTED, "padding": "40px", "textAlign": "center"})

    now      = datetime.now(timezone.utc)
    today    = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    df_today = df_all[df_all["time"] >= today]
    df_week  = df_all[df_all["time"] >= week_ago]

    def card(label, value, color=TEXT, sub=None, full=False):
        return html.Div(style={
            "background": PANEL, "border": f"1px solid {BORDER}",
            "borderRadius": "14px", "padding": "20px",
            "textAlign": "center",
            "gridColumn": "span 2" if full else "span 1",
        }, children=[
            html.Div(label, style={"fontSize": "10px", "color": MUTED,
                                    "letterSpacing": "3px", "marginBottom": "8px",
                                    "textTransform": "uppercase"}),
            html.Div(value, style={"fontSize": "28px", "fontWeight": "800", "color": color}),
            html.Div(sub,   style={"fontSize": "12px", "color": MUTED, "marginTop": "6px"}) if sub else None,
        ])

    def row(left, right, bold=False, color=TEXT, color_r=TEXT):
        return html.Div(style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "center", "padding": "14px 0",
            "borderBottom": f"1px solid {BORDER}",
        }, children=[
            html.Span(left,  style={"fontSize": "14px", "color": MUTED}),
            html.Span(right, style={"fontSize": "15px", "fontWeight": "700" if bold else "400",
                                     "color": color_r}),
        ])

    section_title = lambda t: html.Div(t, style={
        "fontSize": "10px", "color": MUTED, "letterSpacing": "3px",
        "textTransform": "uppercase", "marginBottom": "14px", "marginTop": "20px",
    })

    # ── OVERVIEW TAB ──────────────────────────────────────────
    if tab == "overview":
        total_pnl = df_all["pnl"].sum()
        today_pnl = df_today["pnl"].sum()
        week_pnl  = df_week["pnl"].sum()
        win_rate  = len(df_all[df_all["pnl"]>0]) / max(len(df_all),1) * 100
        today_col = UP if today_pnl >= 0 else DOWN
        today_lbl = f'{"+" if today_pnl>=0 else ""}£{today_pnl:.2f}'
        if df_today.empty:
            today_lbl = "No trades"
            today_col = MUTED

        return html.Div([
            html.Div(style={
                "display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px",
            }, children=[
                card("Today's P&L", today_lbl, today_col,
                     f'{len(df_today)} trades', full=False),
                card("This Week",
                     f'{"+" if week_pnl>=0 else ""}£{week_pnl:.2f}',
                     UP if week_pnl>=0 else DOWN),
                card("Total P&L",
                     f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}',
                     UP if total_pnl>=0 else DOWN),
                card("Win Rate", f"{win_rate:.0f}%",
                     UP if win_rate>=50 else DOWN,
                     f"{len(df_all)} total trades"),
            ]),
            section_title("Account Stats"),
            html.Div(style={"background": PANEL, "border": f"1px solid {BORDER}",
                            "borderRadius": "14px", "padding": "0 16px"},
            children=[
                row("Best single trade",  f'+£{df_all["pnl"].max():.2f}',  True, color_r=UP),
                row("Worst single trade", f'£{df_all["pnl"].min():.2f}',   True, color_r=DOWN),
                row("Total commission",   f'£{df_all["commission"].sum():.2f}', color_r=MUTED),
                row("Trading days",       str(df_all["time"].dt.date.nunique()), color_r=TEXT),
            ]),
        ])

    # ── P&L TAB ───────────────────────────────────────────────
    elif tab == "pnl":
        last10 = df_all.sort_values("time", ascending=False).head(10)
        rows = [section_title("Last 10 Trades")]
        for _, r in last10.iterrows():
            pc = UP if r["pnl"]>=0 else DOWN
            dc = UP if r["direction"]=="BUY" else DOWN
            rows.append(html.Div(style={
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "center", "padding": "14px 0",
                "borderBottom": f"1px solid {BORDER}",
            }, children=[
                html.Div([
                    html.Div(r["time"].strftime("%d %b  %H:%M"),
                             style={"fontSize": "14px", "color": TEXT, "fontWeight": "600"}),
                    html.Div(r["direction"],
                             style={"fontSize": "12px", "color": dc, "marginTop": "2px"}),
                ]),
                html.Div(f'{"+" if r["pnl"]>=0 else ""}£{r["pnl"]:.2f}',
                         style={"fontSize": "18px", "fontWeight": "800", "color": pc}),
            ]))
        return html.Div(rows)

    # ── WEEKLY TAB ────────────────────────────────────────────
    elif tab == "weekly":
        rows = [section_title("Last 14 Days")]
        for i in range(13, -1, -1):
            d     = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            d_end = d + timedelta(days=1)
            day_df  = df_all[(df_all["time"]>=d) & (df_all["time"]<d_end)]
            pnl_d = day_df["pnl"].sum()
            n_d   = len(day_df)
            if n_d == 0:
                color = MUTED
                val   = "—"
            else:
                color = UP if pnl_d>0 else DOWN
                val   = f'{"+" if pnl_d>=0 else ""}£{pnl_d:.2f}'

            rows.append(html.Div(style={
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "center", "padding": "13px 0",
                "borderBottom": f"1px solid {BORDER}",
            }, children=[
                html.Span(d.strftime("%a  %d %b"),
                          style={"fontSize": "14px", "color": MUTED, "width": "110px"}),
                html.Span(f"{n_d} trades" if n_d>0 else "",
                          style={"fontSize": "12px", "color": MUTED}),
                html.Span(val, style={"fontSize": "15px", "fontWeight": "700", "color": color}),
            ]))
        return html.Div(rows)

    # ── JOURNAL TAB ───────────────────────────────────────────
    elif tab == "journal":
        df_all["date"] = df_all["time"].dt.date
        last7_days = sorted(df_all["date"].unique())[-7:]
        rows = [section_title("Last 7 Trading Days")]
        for d in reversed(last7_days):
            day_df   = df_all[df_all["date"]==d]
            pnl_d    = day_df["pnl"].sum()
            n_d      = len(day_df)
            wins_d   = len(day_df[day_df["pnl"]>0])
            wr_d     = wins_d/n_d*100 if n_d>0 else 0
            syms     = ", ".join([str(s) for s in day_df["symbol_id"].unique()])
            pnl_c    = UP if pnl_d>=0 else DOWN
            rows.append(html.Div(style={
                "background": PANEL, "border": f"1px solid {BORDER}",
                "borderRadius": "12px", "padding": "16px", "marginBottom": "10px",
            }, children=[
                html.Div(style={"display":"flex","justifyContent":"space-between",
                                "marginBottom":"8px"}, children=[
                    html.Span(str(d), style={"fontSize":"15px","fontWeight":"700","color":GOLD}),
                    html.Span(f'{"+"if pnl_d>=0 else""}£{pnl_d:.2f}',
                              style={"fontSize":"18px","fontWeight":"800","color":pnl_c}),
                ]),
                html.Div(f'{n_d} trades  ·  {wr_d:.0f}% win rate',
                         style={"fontSize":"12px","color":MUTED}),
            ]))
        return html.Div(rows)

    # ── SCENARIOS TAB ─────────────────────────────────────────
    elif tab == "scenarios":
        today_str = now.strftime("%Y-%m-%d")
        df_sc = build_scenarios(today_str)
        if df_sc.empty:
            return html.Div([
                section_title("Today's Scenarios"),
                html.Div("No trades today.",
                         style={"color": MUTED, "fontSize": "14px",
                                "padding": "30px", "textAlign": "center"}),
            ])
        rows = [section_title(f"Today  ·  {now.strftime('%d %b %Y')}")]
        for i, (_, sc) in enumerate(df_sc.iterrows()):
            pnl   = sc["P&L (£)"]
            color = SC_COLOURS[i % len(SC_COLOURS)]
            pnl_c = UP if pnl>=0 else DOWN
            rows.append(html.Div(style={
                "background": PANEL,
                "borderLeft": f"4px solid {color}",
                "borderRadius": "12px", "padding": "16px",
                "marginBottom": "10px",
            }, children=[
                html.Div(style={"display":"flex","justifyContent":"space-between",
                                "marginBottom":"6px"}, children=[
                    html.Span(f'Scenario {sc["Scenario"]}',
                              style={"fontSize":"13px","fontWeight":"700","color":color,
                                     "letterSpacing":"1px"}),
                    html.Span(f'{"+"if pnl>=0 else""}£{pnl:.2f}',
                              style={"fontSize":"20px","fontWeight":"800","color":pnl_c}),
                ]),
                html.Div(f'{sc["Start"]} → {sc["Last Close"]}  ·  {sc["Trades"]} trades',
                         style={"fontSize":"13px","color":MUTED}),
                html.Div(f'{sc["Buys"]}B / {sc["Sells"]}S  ·  {sc["Instruments"]}',
                         style={"fontSize":"12px","color":MUTED,"marginTop":"4px"}),
                html.Div(
                    f'Exposure DD: £{sc["Exposure DD (£)"]:.2f}'
                    if sc["Exposure DD (£)"] < 0 else "Exposure DD: £0.00",
                    style={"fontSize":"12px","marginTop":"4px",
                           "color": DOWN if sc["Exposure DD (£)"]<-20 else MUTED,
                           "fontWeight":"600"}
                ),
            ]))
        return html.Div(rows)

    return html.Div()


# build_floating_pnl imported from dashboard/floating_pnl.py

# ── Scenarios: floating P&L download ─────────────────────────
@callback(
    Output("sc-float-download",  "data"),
    Input("sc-float-btn",        "n_clicks"),
    dash.dependencies.State("sc-date-picker", "date"),
    prevent_initial_call=True,
)
def download_floating_pnl(_, date_str):
    if not date_str:
        return None
    df = build_floating_pnl(date_str)
    if df.empty:
        return None
    return dcc.send_data_frame(df.to_csv, f"floating_pnl_{date_str}.csv", index=False)


if __name__ == "__main__":
    print(f"\n  {SYMBOL} Trades Dashboard v{APP_VERSION}")
    print(f"  http://127.0.0.1:8050\n")
    app.run(debug=True, host="0.0.0.0", port=8050)
