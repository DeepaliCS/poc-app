# app.py  v2.3.0 — two-page app: overview + daily trade view
import os, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import Dash, html, dcc, callback, Input, Output, State, ctx
from dotenv import load_dotenv

BASE_DIR    = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

SYMBOL      = os.getenv("CTRADER_SYMBOL", "XAUUSD")
DATA_FILE   = BASE_DIR / "data" / "trades.csv"
SYMBOLS_FILE= BASE_DIR / "data" / "symbols.json"
APP_VERSION = "2.3.0"

BG     = "#0a0a0a"
PANEL  = "#111111"
CARD   = "#161616"
BORDER = "#222222"
TEXT   = "#e0e0e0"
MUTED  = "#555555"
GOLD   = "#7eb8f7"
UP     = "#26a69a"
DOWN   = "#ef5350"

TIMEFRAMES = [
    {"label": "1W",  "days": 7},
    {"label": "2W",  "days": 14},
    {"label": "3W",  "days": 21},
    {"label": "1M",  "days": 30},
    {"label": "2M",  "days": 60},
    {"label": "3M",  "days": 90},
    {"label": "4M",  "days": 120},
    {"label": "All", "days": 9999},
]

app = Dash(__name__, title=f"{SYMBOL} Trades", suppress_callback_exceptions=True)

# ── Helpers ───────────────────────────────────────────────────
def load_trades():
    if not DATA_FILE.exists(): return None
    df = pd.read_csv(DATA_FILE)
    df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    df = df[df["is_closing"] == True].copy()
    return df if not df.empty else None

def load_symbols():
    if not SYMBOLS_FILE.exists(): return {}
    with open(SYMBOLS_FILE) as f:
        return json.load(f)

def get_symbol_name(symbol_id, symbols):
    return symbols.get(str(symbol_id), f"Symbol {symbol_id}")

def stat_card(label, value, color=TEXT, sub=None):
    return html.Div([
        html.Div(label, style={"fontSize": "9px", "letterSpacing": "2px",
                               "textTransform": "uppercase",
                               "color": MUTED, "marginBottom": "6px"}),
        html.Div(value, style={"fontSize": "22px", "fontWeight": "800", "color": color}),
        html.Div(sub, style={"fontSize": "10px", "color": MUTED, "marginTop": "2px"}) if sub else None,
    ], style={"background": CARD, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "16px 20px"})

def empty_fig(msg="No data"):
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
        annotations=[{"text": msg, "xref": "paper", "yref": "paper",
                      "x": 0.5, "y": 0.5, "showarrow": False,
                      "font": {"size": 13, "color": MUTED}}],
        xaxis={"visible": False}, yaxis={"visible": False},
        margin={"t": 0, "r": 0, "b": 0, "l": 0},
    )
    return fig

def base_layout():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
        font={"family": "monospace", "color": TEXT, "size": 11},
        margin={"t": 10, "r": 10, "b": 40, "l": 10},
        xaxis={"gridcolor": BORDER, "zerolinecolor": BORDER,
               "tickfont": {"color": MUTED}},
        yaxis={"gridcolor": BORDER, "zerolinecolor": BORDER,
               "tickfont": {"color": MUTED}, "side": "right", "tickprefix": "£"},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": MUTED}},
        hovermode="x unified",
        hoverlabel={"bgcolor": CARD, "font": {"color": TEXT, "family": "monospace"}},
    )

def nav_btn(label, page_id, active=False):
    return html.Button(label, id=page_id, n_clicks=0, style={
        "fontSize": "11px", "padding": "7px 18px",
        "background": GOLD if active else CARD,
        "color": BG if active else MUTED,
        "border": f"1px solid {GOLD if active else BORDER}",
        "borderRadius": "6px", "cursor": "pointer",
        "fontWeight": "700" if active else "400",
    })

def tf_btn(label, active=False):
    return html.Button(label, id=f"tf-{label}", n_clicks=0, style={
        "fontSize": "11px", "padding": "6px 14px",
        "background": GOLD if active else CARD,
        "color": BG if active else MUTED,
        "border": f"1px solid {GOLD if active else BORDER}",
        "borderRadius": "6px", "cursor": "pointer",
        "fontWeight": "700" if active else "400",
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
            nav_btn("📅  Daily View",  "nav-daily",    active=(active_page=="daily")),
            nav_btn("📋  Journal",     "nav-journal",  active=(active_page=="journal")),
            nav_btn("🔍  Scenarios",   "nav-scenarios",active=(active_page=="scenarios")),
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
        *[tf_btn(tf["label"], active=(tf["label"] == "1W")) for tf in TIMEFRAMES],
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

    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                    "gap": "16px", "marginBottom": "16px"},
    children=[
        html.Div([
            html.Div("P&L per trade", style={"fontSize": "9px", "letterSpacing": "2px",
                                              "textTransform": "uppercase", "color": MUTED,
                                              "marginBottom": "12px"}),
            dcc.Graph(id="bar-chart", config={"displayModeBar": False}, style={"height": "220px"}),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px"}),
        html.Div([
            html.Div("Buy vs Sell", style={"fontSize": "9px", "letterSpacing": "2px",
                                           "textTransform": "uppercase", "color": MUTED,
                                           "marginBottom": "12px"}),
            dcc.Graph(id="donut-chart", config={"displayModeBar": False}, style={"height": "220px"}),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px"}),
    ]),

    html.Div([
        html.Div("Trade log", style={"fontSize": "9px", "letterSpacing": "2px",
                                      "textTransform": "uppercase", "color": MUTED,
                                      "marginBottom": "12px"}),
        html.Div(id="trade-table"),
    ], style={"background": PANEL, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "20px"}),

    html.Div(id="last-updated",
             style={"fontSize": "10px", "color": MUTED, "marginTop": "12px", "textAlign": "right"}),

    dcc.Store(id="tf-store", data="1W"),
    dcc.Interval(id="interval", interval=60_000, n_intervals=0),
])

# ── Page 2: Daily View ────────────────────────────────────────
page_daily = html.Div(id="page-daily", children=[
    header("daily"),

    # Date picker + info
    html.Div(style={"display": "flex", "alignItems": "center",
                    "gap": "16px", "marginBottom": "24px",
                    "background": PANEL, "border": f"1px solid {BORDER}",
                    "borderRadius": "10px", "padding": "16px 20px"},
    children=[
        html.Div("Select date:", style={"fontSize": "10px", "color": MUTED,
                                         "letterSpacing": "2px", "textTransform": "uppercase"}),
        dcc.DatePickerSingle(
            id="date-picker",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            display_format="DD MMM YYYY",
            style={"fontFamily": "monospace"},
        ),
        html.Div(id="day-summary",
                 style={"fontSize": "11px", "color": MUTED, "marginLeft": "auto"}),
    ]),

    html.Div(id="daily-charts"),
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
                        style={"fontSize": "11px", "padding": "5px 12px", "background": GOLD,
                               "color": BG, "border": f"1px solid {GOLD}",
                               "borderRadius": "6px", "cursor": "pointer", "fontWeight": "700"}),
            html.Button("P&L",     id="sort-pnl",   n_clicks=0,
                        style={"fontSize": "11px", "padding": "5px 12px", "background": CARD,
                               "color": MUTED, "border": f"1px solid {BORDER}",
                               "borderRadius": "6px", "cursor": "pointer"}),
            html.Button("Trades",  id="sort-trades", n_clicks=0,
                        style={"fontSize": "11px", "padding": "5px 12px", "background": CARD,
                               "color": MUTED, "border": f"1px solid {BORDER}",
                               "borderRadius": "6px", "cursor": "pointer"}),
        ]),
        html.Button("⬇  Download CSV", id="download-btn", n_clicks=0,
                    style={"fontSize": "11px", "padding": "7px 18px", "background": CARD,
                           "color": TEXT, "border": f"1px solid {BORDER}",
                           "borderRadius": "6px", "cursor": "pointer"}),
        html.Button("📊  Calculate Exposure DD", id="live-dd-btn", n_clicks=0,
                    style={"fontSize": "11px", "padding": "7px 18px", "background": CARD,
                           "color": MUTED, "border": f"1px solid {BORDER}",
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
        html.Div("Date:", style={"fontSize": "10px", "color": MUTED,
                                  "letterSpacing": "2px", "textTransform": "uppercase"}),
        dcc.DatePickerSingle(
            id="sc-date-picker",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            display_format="DD MMM YYYY",
            style={"fontFamily": "monospace"},
        ),
        html.Div(id="sc-day-summary",
                 style={"fontSize": "11px", "color": MUTED, "marginLeft": "auto"}),
        html.Button("🕯  Load Chart", id="sc-chart-btn", n_clicks=0,
                    style={"fontSize": "11px", "padding": "6px 14px",
                           "background": CARD, "color": MUTED,
                           "border": f"1px solid {BORDER}",
                           "borderRadius": "6px", "cursor": "pointer"}),
        html.Button("⬇  Download CSV", id="sc-download-btn", n_clicks=0,
                    style={"fontSize": "11px", "padding": "6px 14px",
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
        html.Div("Scenario log", style={"fontSize": "9px", "letterSpacing": "2px",
                                         "textTransform": "uppercase", "color": MUTED,
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
                     style={"fontSize": "9px", "letterSpacing": "2px",
                            "textTransform": "uppercase", "color": MUTED}),
        ]),
        dcc.Loading(type="circle", color=GOLD, children=
            html.Div(id="sc-market-chart-wrap",
                     children=html.Div(
                         "Click  🕯 Load Chart  above to overlay your trades on the market",
                         style={"color": MUTED, "fontSize": "12px",
                                "padding": "40px", "textAlign": "center"}
                     ))
        ),
    ], style={"background": PANEL, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "20px"}),

    dcc.Download(id="sc-download"),
    dcc.Store(id="sc-store", data={}),
])

# ── App layout ────────────────────────────────────────────────
app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh", "padding": "28px",
           "fontFamily": "monospace", "color": TEXT},
    children=[
        dcc.Store(id="page-store", data="overview"),
        html.Div(id="page-content"),
    ]
)

# ── Page routing ──────────────────────────────────────────────
@callback(
    Output("page-store",    "data"),
    Input("nav-overview",   "n_clicks"),
    Input("nav-daily",      "n_clicks"),
    Input("nav-journal",    "n_clicks"),
    Input("nav-scenarios",  "n_clicks"),
    prevent_initial_call=True,
)
def switch_page(*_):
    triggered = ctx.triggered_id
    if triggered == "nav-daily":     return "daily"
    if triggered == "nav-journal":   return "journal"
    if triggered == "nav-scenarios": return "scenarios"
    return "overview"

@callback(
    Output("page-content", "children"),
    Input("page-store",    "data"),
)
def render_page(page):
    if page == "daily":     return page_daily
    if page == "journal":   return page_journal
    if page == "scenarios": return page_scenarios
    return page_overview

# ── Overview: timeframe store ─────────────────────────────────
@callback(
    Output("tf-store", "data"),
    *[Input(f"tf-{tf['label']}", "n_clicks") for tf in TIMEFRAMES],
    prevent_initial_call=True,
)
def set_tf(*_):
    return ctx.triggered_id.replace("tf-", "") if ctx.triggered_id else "1W"

@callback(
    *[Output(f"tf-{tf['label']}", "style") for tf in TIMEFRAMES],
    Input("tf-store", "data"),
)
def update_tf_styles(active):
    return [{
        "fontSize": "11px", "padding": "6px 14px",
        "background": GOLD if tf["label"] == active else CARD,
        "color": BG if tf["label"] == active else MUTED,
        "border": f"1px solid {GOLD if tf['label'] == active else BORDER}",
        "borderRadius": "6px", "cursor": "pointer",
        "fontWeight": "700" if tf["label"] == active else "400",
    } for tf in TIMEFRAMES]

# ── Overview: main data callback ──────────────────────────────
@callback(
    Output("stat-cards",   "children"),
    Output("pnl-chart",    "figure"),
    Output("bar-chart",    "figure"),
    Output("donut-chart",  "figure"),
    Output("trade-table",  "children"),
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
        return cards, empty, empty, empty, html.Div(), "No data", "Cumulative P&L"

    days   = next((t["days"] for t in TIMEFRAMES if t["label"] == active_tf), 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    df     = df_all if days == 9999 else df_all[df_all["time"] >= cutoff].copy()

    if df.empty:
        empty = empty_fig(f"No trades in the last {active_tf}")
        cards = [stat_card(f"No trades ({active_tf})", "—") for _ in range(5)]
        return cards, empty, empty, empty, html.Div(), "", f"Cumulative P&L · {active_tf}"

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
        fill="tozeroy", fillcolor="rgba(240,180,41,0.07)",
        hovertemplate="%{x|%d %b %H:%M}<br>£%{y:.2f}<extra></extra>",
    ))
    pnl_fig.update_layout(**base_layout())

    bar_fig = go.Figure(go.Bar(
        x=df["time"], y=df["pnl"],
        marker={"color": [UP if p >= 0 else DOWN for p in df["pnl"]], "opacity": 0.85},
        hovertemplate="%{x|%d %b %H:%M}<br>£%{y:.2f}<extra></extra>",
    ))
    bar_fig.update_layout(**base_layout())

    buys  = len(df[df["direction"] == "BUY"])
    sells = len(df[df["direction"] == "SELL"])
    donut_fig = go.Figure(go.Pie(
        values=[buys, sells] if (buys+sells) > 0 else [1,1],
        labels=["Buy","Sell"], hole=0.62,
        marker={"colors": [UP, DOWN]}, textinfo="percent+label",
    ))
    donut_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "monospace", "color": TEXT, "size": 11},
        margin={"t":10,"r":10,"b":10,"l":10}, showlegend=False,
        annotations=[{"text": f"{len(df)}<br>trades", "x":0.5, "y":0.5,
                      "showarrow": False, "font": {"size":14,"color":TEXT},
                      "xref":"paper","yref":"paper"}],
    )

    th  = {"fontSize":"9px","letterSpacing":"1px","textTransform":"uppercase",
           "color":MUTED,"padding":"8px 12px","borderBottom":f"1px solid {BORDER}",
           "textAlign":"right","background":CARD}
    thl = {**th,"textAlign":"left"}
    def td(c=TEXT):
        return {"fontSize":"11px","color":c,"padding":"8px 12px",
                "textAlign":"right","borderBottom":f"1px solid {BORDER}"}
    tdl = lambda c=TEXT: {**td(c),"textAlign":"left"}

    rows = [html.Tr([html.Th("Time",style=thl),html.Th("Side",style=th),
                     html.Th("Vol",style=th),html.Th("Price",style=th),
                     html.Th("P&L",style=th)])]
    for _, row in df.sort_values("time",ascending=False).head(30).iterrows():
        pc = UP if row["pnl"]>=0 else DOWN
        rows.append(html.Tr([
            html.Td(row["time"].strftime("%d %b  %H:%M"),style=tdl()),
            html.Td(row["direction"],style=td(UP if row["direction"]=="BUY" else DOWN)),
            html.Td(f'{row["volume"]:.2f}',style=td()),
            html.Td(f'{row["fill_price"]:.2f}',style=td()),
            html.Td(f'{"+" if row["pnl"]>=0 else ""}£{row["pnl"]:.2f}',style=td(pc)),
        ]))
    table   = html.Table(rows, style={"width":"100%","borderCollapse":"collapse"})
    updated = f'Updated {datetime.now().strftime("%H:%M:%S")}  ·  {len(df)} trades  ·  {"+" if total_pnl>=0 else ""}£{total_pnl:.2f}'
    return cards, pnl_fig, bar_fig, donut_fig, table, updated, f"Cumulative P&L · {active_tf}"

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
                     style={"color": MUTED, "fontSize": "14px",
                            "padding": "40px 0", "textAlign": "center"}),
            html.Div("Try another date using the picker above.",
                     style={"color": MUTED, "fontSize": "11px", "textAlign": "center"}),
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
                   "title": {"text": "price", "font": {"color": MUTED, "size": 9}}},
            yaxis2={"overlaying": "y", "side": "left",
                    "tickprefix": "£", "tickfont": {"color": MUTED},
                    "gridcolor": "rgba(0,0,0,0)",
                    "title": {"text": "cum P&L", "font": {"color": MUTED, "size": 9}}},
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
                              style={"fontSize": "10px", "color": MUTED,
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
# ── Trading session definitions (all times in UTC) ───────────
SESSIONS = [
    {
        "name":  "Sydney",
        "start": 21,  "end": 6,   # 21:00–06:00 UTC (crosses midnight)
        "color": "rgba(100,160,255,0.07)",
        "label_color": "rgba(100,160,255,0.7)",
    },
    {
        "name":  "Tokyo",
        "start": 0,   "end": 9,   # 00:00–09:00 UTC
        "color": "rgba(255,50,50,0.06)",
        "label_color": "rgba(255,100,100,0.7)",
    },
    {
        "name":  "London",
        "start": 8,   "end": 17,  # 08:00–17:00 UTC
        "color": "rgba(100,220,160,0.07)",
        "label_color": "rgba(100,220,160,0.7)",
    },
    {
        "name":  "New York",
        "start": 13,  "end": 22,  # 13:00–22:00 UTC
        "color": "rgba(255,180,50,0.07)",
        "label_color": "rgba(255,180,50,0.7)",
    },
]

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


# ── Journal: build daily summary dataframe ───────────────────
def calc_exposure_drawdown(date_str, all_df):
    """
    Maximum Adverse Exposure — uses fill prices from all deals as price checkpoints.

    For each open position, at every price event during its lifetime,
    we calculate the worst the position went against us (using the lowest
    price seen for BUYs, highest for SELLs). We sum across all simultaneously
    open positions to find the worst total floating loss at any point.

    This is purely from the CSV — no API calls needed.
    """
    date_utc  = pd.Timestamp(date_str).tz_localize("UTC")
    date_end  = date_utc + pd.Timedelta(days=1)

    day_all   = all_df[(all_df["time"] >= date_utc) & (all_df["time"] < date_end)].copy()
    if day_all.empty:
        return None

    openings   = day_all[day_all["is_closing"] == False]
    closings   = day_all[day_all["is_closing"] == True]
    all_prices = day_all[["time", "symbol_id", "fill_price"]].copy()

    # Build positions with scale factor derived from actual P&L
    positions = []
    for _, cl in closings.iterrows():
        op = openings[openings["position_id"] == cl["position_id"]]
        if op.empty:
            continue
        op         = op.iloc[0]
        price_diff = cl["fill_price"] - op["fill_price"]
        if op["direction"] == "SELL":
            price_diff = -price_diff
        vol    = op["volume"]
        scale  = (cl["pnl"] / (price_diff * vol)
                  if (price_diff != 0 and vol != 0) else 1.0)
        positions.append({
            "symbol_id":   cl["symbol_id"],
            "direction":   op["direction"],
            "volume":      vol,
            "entry_price": op["fill_price"],
            "entry_time":  op["time"],
            "exit_time":   cl["time"],
            "scale":       scale,
        })

    if not positions:
        return None

    pos_df = pd.DataFrame(positions)

    # Events = every fill_price timestamp during the day
    event_times = sorted(set(all_prices["time"].tolist()))
    if not event_times:
        return None

    worst_exposure = 0.0

    for t in event_times:
        open_pos = pos_df[
            (pos_df["entry_time"] <= t) & (pos_df["exit_time"] > t)
        ]
        if open_pos.empty:
            continue

        total_float = 0.0
        for _, pos in open_pos.iterrows():
            # Worst price seen for this symbol from entry up to now
            sym_px = all_prices[
                (all_prices["symbol_id"] == pos["symbol_id"]) &
                (all_prices["time"] >= pos["entry_time"]) &
                (all_prices["time"] <= t)
            ]["fill_price"]

            if sym_px.empty:
                continue

            if pos["direction"] == "BUY":
                worst_price = sym_px.min()
                adverse     = worst_price - pos["entry_price"]
            else:
                worst_price = sym_px.max()
                adverse     = pos["entry_price"] - worst_price

            total_float += adverse * pos["volume"] * pos["scale"]

        if total_float < worst_exposure:
            worst_exposure = total_float

    return round(worst_exposure, 2) if worst_exposure < 0 else 0.0


def build_daily_summary():
    """Aggregate all closing trades into per-day rows."""
    import math
    df_all  = pd.read_csv(DATA_FILE)
    df_all["time"] = pd.to_datetime(df_all["time"], format="ISO8601", utc=True)
    symbols = load_symbols()
    closing = df_all[df_all["is_closing"] == True].copy()
    if closing.empty:
        return pd.DataFrame()
    closing["date"] = closing["time"].dt.date

    def get_sessions_for_hour(hour):
        found = []
        for s in SESSIONS:
            st, en = s["start"], s["end"]
            if st < en:
                if st <= hour < en: found.append(s["name"])
            else:
                if hour >= st or hour < en: found.append(s["name"])
        return found

    rows = []
    for date, day_df in closing.groupby("date"):
        day_s      = day_df.sort_values("time")
        total_pnl  = day_s["pnl"].sum()
        total_comm = day_s["commission"].sum()
        n_trades   = len(day_s)
        wins       = len(day_s[day_s["pnl"] > 0])
        best       = day_s["pnl"].max()
        worst      = day_s["pnl"].min()

        # Closed-trade drawdown (fast — from CSV only)
        day_s = day_s.copy()
        day_s["cum_pnl"] = day_s["pnl"].cumsum()
        running_max = day_s["cum_pnl"].cummax()
        max_dd      = (day_s["cum_pnl"] - running_max).min()

        # Instruments
        sym_ids     = day_s["symbol_id"].unique()
        instruments = ", ".join([symbols.get(str(s), f"ID:{s}") for s in sym_ids])

        # Sessions touched
        all_hours = set(day_s["time"].dt.hour.tolist())
        seen_sess = []
        for h in sorted(all_hours):
            for s in get_sessions_for_hour(h):
                if s not in seen_sess: seen_sess.append(s)

        # First trade session
        first_hour    = day_s["time"].iloc[0].hour
        first_session = ", ".join(get_sessions_for_hour(first_hour)) or "Off-hours"

        rows.append({
            "Date":              str(date),
            "P&L (£)":           round(total_pnl, 2),
            "Commission (£)":    round(total_comm, 2),
            "Net (£)":           round(total_pnl + total_comm, 2),
            "Trades":            n_trades,
            "Wins":              wins,
            "Win %":             round(wins / n_trades * 100, 1) if n_trades else 0,
            "Best (£)":          round(best, 2),
            "Worst (£)":         round(worst, 2),
            "Closed DD (£)":     round(max_dd, 2),
            "Live DD (£)":       "—",   # populated on demand
            "Instruments":       instruments,
            "First Session":     first_session,
            "Sessions":          ", ".join(seen_sess),
        })

    return pd.DataFrame(rows)


# ── Journal: live drawdown fetch ─────────────────────────────
@callback(
    Output("live-dd-store",  "data"),
    Output("live-dd-btn",    "children"),
    Output("live-dd-btn",    "style"),
    Input("live-dd-btn",     "n_clicks"),
    prevent_initial_call=True,
)
def fetch_live_dd(_):
    """Calculate exposure drawdown for every trading day — CSV only, instant."""
    df_all = pd.read_csv(DATA_FILE)
    df_all["time"] = pd.to_datetime(df_all["time"], format="ISO8601", utc=True)

    closing = df_all[df_all["is_closing"] == True].copy()
    closing["date"] = closing["time"].dt.date
    dates = sorted(closing["date"].unique())

    results = {}
    for date in dates:
        dd = calc_exposure_drawdown(str(date), df_all)
        results[str(date)] = dd if dd is not None else 0.0

    btn_style = {"fontSize": "11px", "padding": "7px 18px", "background": UP,
                 "color": BG, "border": f"1px solid {UP}",
                 "borderRadius": "6px", "cursor": "pointer", "fontWeight": "700"}
    return results, "✓  Exposure DD Loaded", btn_style


# ── Journal: main table callback ──────────────────────────────
@callback(
    Output("journal-table",   "children"),
    Output("journal-summary", "children"),
    Input("sort-store",       "data"),
    Input("page-store",       "data"),
    Input("live-dd-store",    "data"),
)
def update_journal(sort_key, page, live_dd_data):
    if page != "journal":
        raise dash.exceptions.PreventUpdate

    df = build_daily_summary()
    if df.empty:
        return html.Div("No data.", style={"color": MUTED}), []

    # Sort
    col_map = {"date": "Date", "pnl": "P&L (£)", "trades": "Trades"}
    sort_col = col_map.get(sort_key, "Date")
    df = df.sort_values(sort_col, ascending=(sort_key == "date"),
                        key=(lambda x: pd.to_datetime(x) if sort_key == "date" else x)
                        ).reset_index(drop=True)

    # ── Summary cards ─────────────────────────────────────────
    total_pnl    = df["P&L (£)"].sum()
    total_comm   = df["Commission (£)"].sum()
    trading_days = len(df)
    win_days     = len(df[df["P&L (£)"] > 0])
    avg_daily    = df["P&L (£)"].mean()

    summary_cards = [
        stat_card("Total P&L",    f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}',
                  UP if total_pnl >= 0 else DOWN),
        stat_card("Trading Days", str(trading_days), TEXT,
                  f"{win_days} profitable"),
        stat_card("Day Win Rate", f'{win_days/trading_days*100:.0f}%',
                  UP if win_days/trading_days >= 0.5 else DOWN),
        stat_card("Avg Daily P&L",f'{"+" if avg_daily>=0 else ""}£{avg_daily:.2f}',
                  UP if avg_daily >= 0 else DOWN),
        stat_card("Total Commission", f'£{total_comm:.2f}', MUTED),
    ]

    # Merge live DD into df if available
    if live_dd_data:
        df["Exposure DD (£)"] = df["Date"].map(
            lambda d: live_dd_data.get(d, "—")
        )

    # ── Table ──────────────────────────────────────────────────
    cols = ["Date", "P&L (£)", "Net (£)", "Trades",
            "Win %", "Closed DD (£)", "Exposure DD (£)", "Best (£)", "Worst (£)",
            "Instruments", "First Session", "Sessions"]

    th_base = {"fontSize": "9px", "letterSpacing": "1px",
               "textTransform": "uppercase", "color": MUTED,
               "padding": "10px 14px", "background": CARD,
               "borderBottom": f"1px solid {BORDER}",
               "textAlign": "right", "whiteSpace": "nowrap"}
    th_left = {**th_base, "textAlign": "left"}

    def td_style(color=TEXT, align="right"):
        return {"fontSize": "11px", "color": color, "padding": "9px 14px",
                "textAlign": align, "borderBottom": f"1px solid {BORDER}",
                "whiteSpace": "nowrap"}

    header_row = html.Tr([
        html.Th(c, style=th_left if c in ["Date","Instruments","Sessions","First Session"]
                else th_base)
        for c in cols
    ])

    data_rows = []
    for _, row in df.iterrows():
        pnl     = row["P&L (£)"]
        dd      = row["Closed DD (£)"]
        wr      = row["Win %"]
        pnl_c   = UP if pnl >= 0 else DOWN
        dd_c    = DOWN if dd < -50 else (MUTED if dd < 0 else TEXT)

        # Live DD cell
        live_dd_val = row.get("Exposure DD (£)", "—")
        if isinstance(live_dd_val, (int, float)):
            live_dd_str = f'£{live_dd_val:.2f}'
            live_dd_c   = DOWN if live_dd_val < -50 else (MUTED if live_dd_val < 0 else TEXT)
        else:
            live_dd_str = str(live_dd_val)
            live_dd_c   = MUTED

        data_rows.append(html.Tr([
            html.Td(row["Date"],                           style=td_style(GOLD,  "left")),
            html.Td(f'{"+" if pnl>=0 else ""}£{pnl:.2f}', style=td_style(pnl_c)),
            html.Td(f'{"+" if row["Net (£)"]>=0 else ""}£{row["Net (£)"]:.2f}',
                    style=td_style(UP if row["Net (£)"]>=0 else DOWN)),
            html.Td(str(row["Trades"]),                    style=td_style()),
            html.Td(f'{wr:.0f}%',                          style=td_style(UP if wr>=50 else DOWN)),
            html.Td(f'£{dd:.2f}',                          style=td_style(dd_c)),
            html.Td(live_dd_str,                           style=td_style(live_dd_c)),
            html.Td(f'+£{row["Best (£)"]:.2f}',            style=td_style(UP)),
            html.Td(f'£{row["Worst (£)"]:.2f}',            style=td_style(DOWN)),
            html.Td(row["Instruments"],                    style=td_style(TEXT, "left")),
            html.Td(row["First Session"],                  style=td_style(MUTED, "left")),
            html.Td(row["Sessions"],                       style=td_style(MUTED, "left")),
        ]))

    table = html.Div(
        html.Table(
            [html.Thead(header_row), html.Tbody(data_rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        ),
        style={"overflowX": "auto"},
    )

    return table, summary_cards


# ── Journal: CSV download ─────────────────────────────────────
@callback(
    Output("journal-download", "data"),
    Input("download-btn",      "n_clicks"),
    dash.dependencies.State("live-dd-store", "data"),
    prevent_initial_call=True,
)
def download_csv(_, live_dd_data):
    df = build_daily_summary()
    if df.empty:
        return None
    if live_dd_data:
        df["Live DD (£)"] = df["Date"].map(lambda d: live_dd_data.get(d, "—"))
    return dcc.send_data_frame(df.to_csv, "daily_journal.csv", index=False)


# ── Scenarios: colour palette per scenario ───────────────────
SC_COLOURS = [
    "#00e5ff", "#f0b429", "#a8ff78", "#ff6b9d",
    "#c77dff", "#ff9800", "#00bcd4", "#e91e63",
    "#8bc34a", "#ff5722",
]

def build_scenarios(date_str):
    """
    Detect trading scenarios by clustering exits.
    A new scenario starts when there is a gap > 10 min between consecutive exits.
    This matches the pattern: burst of entries + quick closes = one dip scenario.
    """
    df_all   = pd.read_csv(DATA_FILE)
    df_all["time"] = pd.to_datetime(df_all["time"], format="ISO8601", utc=True)
    symbols  = load_symbols()

    sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
    sel_end = sel_dt + timedelta(days=1)

    openings = df_all[df_all["is_closing"] == False].copy()
    closings = df_all[
        (df_all["is_closing"] == True) &
        (df_all["time"] >= sel_dt) &
        (df_all["time"] < sel_end)
    ].copy().sort_values("time").reset_index(drop=True)

    if closings.empty:
        return pd.DataFrame()

    # Gap between consecutive exits — new scenario if gap > 10 min
    GAP_MINS = 10
    gaps = closings["time"].diff().dt.total_seconds().fillna(9999) / 60
    closings["scenario"] = (gaps > GAP_MINS).cumsum() + 1

    rows = []
    for sc_num, grp in closings.groupby("scenario"):
        grp = grp.sort_values("time")

        # Get entry times for these positions
        pos_ids  = grp["position_id"].tolist()
        entries  = openings[openings["position_id"].isin(pos_ids)]

        first_entry  = entries["time"].min() if not entries.empty else grp["time"].iloc[0]
        first_exit   = grp["time"].min()
        last_exit    = grp["time"].max()
        duration_s   = (last_exit - first_exit).total_seconds()
        if duration_s < 60:
            dur_str = f"{int(duration_s)}s"
        elif duration_s < 3600:
            dur_str = f"{int(duration_s//60)}m {int(duration_s%60)}s"
        else:
            dur_str = f"{int(duration_s//3600)}h {int((duration_s%3600)//60)}m"

        pnl      = grp["pnl"].sum()
        n        = len(grp)
        wins     = len(grp[grp["pnl"] > 0])
        best     = grp["pnl"].max()
        worst    = grp["pnl"].min()
        sym_ids  = grp["symbol_id"].unique()
        syms_str = ", ".join([symbols.get(str(s), f"ID:{s}") for s in sym_ids])
        comm     = grp["commission"].sum()

        entry_dirs = entries[entries["position_id"].isin(pos_ids)]["direction"].value_counts()
        buys  = int(entry_dirs.get("BUY",  0))
        sells = int(entry_dirs.get("SELL", 0))

        rows.append({
            "Scenario":       int(sc_num),
            "Start":          first_entry.strftime("%H:%M:%S"),
            "First Close":    first_exit.strftime("%H:%M:%S"),
            "Last Close":     last_exit.strftime("%H:%M:%S"),
            "Duration":       dur_str,
            "Trades":         n,
            "Buys":           buys,
            "Sells":          sells,
            "P&L (£)":        round(pnl, 2),
            "Commission (£)": round(comm, 2),
            "Net (£)":        round(pnl + comm, 2),
            "Win %":          round(wins / n * 100) if n else 0,
            "Best (£)":       round(best, 2),
            "Worst (£)":      round(worst, 2),
            "Instruments":    syms_str,
            "_sym_ids":       list(sym_ids),
            "_first_entry":   first_entry,
            "_last_exit":     last_exit,
        })

    return pd.DataFrame(rows)


# ── Scenarios: table + cards (instant, CSV only) ──────────────
@callback(
    Output("sc-cards",      "children"),
    Output("sc-table",      "children"),
    Output("sc-day-summary","children"),
    Output("sc-store",      "data"),
    Input("sc-date-picker", "date"),
    Input("page-store",     "data"),
)
def update_scenario_table(selected_date, page):
    if page != "scenarios":
        raise dash.exceptions.PreventUpdate
    if not selected_date:
        selected_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    df_sc = build_scenarios(selected_date)

    if df_sc.empty:
        msg = html.Div([
            html.Div("📭  No trades on this day.",
                     style={"color": MUTED, "fontSize": "14px",
                            "padding": "20px 0", "textAlign": "center"}),
        ])
        return [], msg, "No trades", {}

    n_sc      = len(df_sc)
    total_pnl = df_sc["P&L (£)"].sum()
    summary   = (f"{n_sc} scenarios  ·  {df_sc['Trades'].sum()} trades  ·  "
                 f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}')

    # Cards
    cards = []
    for i, (_, row) in enumerate(df_sc.iterrows()):
        pnl   = row["P&L (£)"]
        color = SC_COLOURS[i % len(SC_COLOURS)]
        cards.append(html.Div([
            html.Div(f'Scenario {row["Scenario"]}',
                     style={"fontSize": "9px", "letterSpacing": "2px",
                            "textTransform": "uppercase",
                            "color": color, "marginBottom": "4px"}),
            html.Div(f'{"+" if pnl>=0 else ""}£{pnl:.2f}',
                     style={"fontSize": "20px", "fontWeight": "800",
                            "color": UP if pnl >= 0 else DOWN}),
            html.Div(f'{row["Start"]} → {row["Last Close"]}',
                     style={"fontSize": "10px", "color": MUTED, "marginTop": "2px"}),
            html.Div(f'{row["Trades"]} trades · {row["Duration"]}',
                     style={"fontSize": "10px", "color": MUTED}),
            html.Div(f'{row["Buys"]}B / {row["Sells"]}S  ·  {row["Instruments"]}',
                     style={"fontSize": "10px", "color": MUTED, "marginTop": "2px"}),
        ], style={"background": CARD,
                  "border": f"1px solid {BORDER}",
                  "borderTop": f"3px solid {color}",
                  "borderRadius": "10px", "padding": "14px 18px",
                  "minWidth": "200px"}))

    # Table
    cols = ["Scenario","Start","First Close","Last Close","Duration",
            "Trades","Buys","Sells","P&L (£)","Net (£)",
            "Win %","Best (£)","Worst (£)","Instruments"]

    th = {"fontSize":"9px","letterSpacing":"1px","textTransform":"uppercase",
          "color":MUTED,"padding":"10px 14px","background":CARD,
          "borderBottom":f"1px solid {BORDER}","textAlign":"right","whiteSpace":"nowrap"}
    thl = {**th,"textAlign":"left"}

    def td(c=TEXT, align="right"):
        return {"fontSize":"11px","color":c,"padding":"9px 14px",
                "textAlign":align,"borderBottom":f"1px solid {BORDER}","whiteSpace":"nowrap"}

    hrow = html.Tr([html.Th(c, style=thl if c in
                   ["Start","First Close","Last Close","Duration","Instruments"]
                   else th) for c in cols])

    drows = []
    for i, (_, row) in enumerate(df_sc.iterrows()):
        pnl   = row["P&L (£)"]
        color = SC_COLOURS[i % len(SC_COLOURS)]
        wr    = row["Win %"]
        drows.append(html.Tr([
            html.Td(f'S{row["Scenario"]}',
                    style={**td(color,"right"),"fontWeight":"700",
                           "borderLeft":f"3px solid {color}"}),
            html.Td(row["Start"],          style=td(TEXT,"left")),
            html.Td(row["First Close"],    style=td(TEXT,"left")),
            html.Td(row["Last Close"],     style=td(TEXT,"left")),
            html.Td(row["Duration"],       style=td(MUTED,"left")),
            html.Td(str(row["Trades"]),    style=td()),
            html.Td(str(row["Buys"]),      style=td(UP)),
            html.Td(str(row["Sells"]),     style=td(DOWN)),
            html.Td(f'{"+"if pnl>=0 else""}£{pnl:.2f}', style=td(UP if pnl>=0 else DOWN)),
            html.Td(f'{"+"if row["Net (£)"]>=0 else""}£{row["Net (£)"]:.2f}',
                    style=td(UP if row["Net (£)"]>=0 else DOWN)),
            html.Td(f'{wr:.0f}%',          style=td(UP if wr>=50 else DOWN)),
            html.Td(f'+£{row["Best (£)"]:.2f}',  style=td(UP)),
            html.Td(f'£{row["Worst (£)"]:.2f}',  style=td(DOWN)),
            html.Td(row["Instruments"],    style=td(TEXT,"left")),
        ]))

    table = html.Div(
        html.Table([html.Thead(hrow), html.Tbody(drows)],
                   style={"width":"100%","borderCollapse":"collapse"}),
        style={"overflowX":"auto"},
    )

    # Store serialisable version of df
    store = df_sc.drop(columns=["_sym_ids","_first_entry","_last_exit"],
                       errors="ignore").to_dict("records")

    return cards, table, summary, store


# ── Scenarios: chart (only on button click) ───────────────────
@callback(
    Output("sc-market-chart-wrap", "children"),
    Output("sc-chart-title",       "children"),
    Output("sc-chart-btn",         "style"),
    Input("sc-chart-btn",          "n_clicks"),
    Input("sc-date-picker",        "date"),
    dash.dependencies.State("page-store", "data"),
    prevent_initial_call=True,
)
def load_scenario_chart(n_clicks, selected_date, page):
    if page != "scenarios":
        raise dash.exceptions.PreventUpdate
    # Only fetch chart if button was clicked OR if date changed after button was used
    if ctx.triggered_id == "sc-date-picker" and (n_clicks == 0):
        raise dash.exceptions.PreventUpdate
    if not selected_date:
        raise dash.exceptions.PreventUpdate

    df_sc   = build_scenarios(selected_date)
    symbols = load_symbols()

    if df_sc.empty:
        return html.Div("No scenarios to chart.",
                        style={"color": MUTED, "padding": "20px"}), "", {}

    sel_dt  = pd.Timestamp(selected_date).tz_localize("UTC")
    sel_end = sel_dt + timedelta(days=1)

    # All unique symbols traded that day across all scenarios
    all_sym_ids = []
    for _, row in df_sc.iterrows():
        for s in row["_sym_ids"]:
            if s not in all_sym_ids:
                all_sym_ids.append(s)

    # Load all raw deals for the day once
    df_raw = pd.read_csv(DATA_FILE)
    df_raw["time"] = pd.to_datetime(df_raw["time"], format="ISO8601", utc=True)
    day_raw_all = df_raw[
        (df_raw["time"] >= sel_dt) & (df_raw["time"] < sel_end)
    ].copy()

    # Build one chart per symbol, stacked
    chart_components = []

    for sym_id in all_sym_ids:
        sym_name     = symbols.get(str(sym_id), str(sym_id))
        candles      = fetch_candles_sync(sym_id, sel_dt, sel_end, period=5, minutes=5)

        day_raw      = day_raw_all[day_raw_all["symbol_id"] == sym_id].copy()
        openings_raw = day_raw[day_raw["is_closing"] == False]
        closings_raw = day_raw[day_raw["is_closing"] == True].sort_values("time").copy()

        # Assign scenario numbers by matching each close time to its scenario window
        if not closings_raw.empty:
            def assign_scenario(close_time):
                for _, sc in df_sc.iterrows():
                    if sc["_first_entry"] <= close_time <= sc["_last_exit"]:
                        return sc["Scenario"]
                return -1
            closings_raw = closings_raw.copy()
            closings_raw["scenario"] = closings_raw["time"].apply(assign_scenario)

        # Only scenarios that include this symbol
        sc_for_sym = df_sc[df_sc["_sym_ids"].apply(lambda ids: sym_id in ids)]
        if sc_for_sym.empty and closings_raw.empty:
            continue

        sym_pnl = closings_raw["pnl"].sum() if not closings_raw.empty else 0

        fig = go.Figure()

        if candles is not None and not candles.empty:
            fig.add_trace(go.Candlestick(
                x=candles["time"],
                open=candles["open"], high=candles["high"],
                low=candles["low"],   close=candles["close"],
                name=sym_name,
                increasing_line_color=UP, increasing_fillcolor=UP,
                decreasing_line_color=DOWN, decreasing_fillcolor=DOWN,
                line={"width": 1},
            ))
            add_session_boxes(fig, sel_dt)

        legend_added = set()
        for i, (_, sc_row) in enumerate(df_sc.iterrows()):
            sc_num = sc_row["Scenario"]
            color  = SC_COLOURS[i % len(SC_COLOURS)]
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

            # Only shade vrect if this scenario involves this symbol
            if sym_id not in sc_row["_sym_ids"]:
                continue

            fig.add_vrect(
                x0=sc_row["_first_entry"], x1=sc_row["_last_exit"],
                fillcolor=f"rgba({r},{g},{b},0.08)", layer="below", line_width=0
            )
            fig.add_annotation(
                x=sc_row["_first_entry"], xanchor="left",
                y=0.97, yanchor="top", yref="paper",
                text=f"S{sc_num}", showarrow=False,
                font={"size": 9, "color": color}, bgcolor="rgba(0,0,0,0)",
            )

            sc_cls = closings_raw[closings_raw["scenario"] == sc_num] if not closings_raw.empty else pd.DataFrame()
            for _, trade in sc_cls.iterrows():
                op     = openings_raw[openings_raw["position_id"] == trade["position_id"]]
                is_buy = op.iloc[0]["direction"] == "BUY" if not op.empty else True
                pnl    = trade["pnl"]

                if not op.empty:
                    lk = f"e{sc_num}_{sym_id}"
                    fig.add_trace(go.Scatter(
                        x=[op.iloc[0]["time"]], y=[op.iloc[0]["fill_price"]],
                        mode="markers",
                        marker={"symbol": "triangle-up" if is_buy else "triangle-down",
                                "size": 10, "color": color,
                                "line": {"color": BG, "width": 1}},
                        name=f"S{sc_num}", legendgroup=f"s{sc_num}",
                        showlegend=(lk not in legend_added),
                        hovertemplate=(f"S{sc_num} ENTRY {'BUY' if is_buy else 'SELL'}<br>"
                                       f"Price: {op.iloc[0]['fill_price']:.2f}<br>"
                                       f"Time: %{{x|%H:%M:%S}}<extra></extra>"),
                    ))
                    legend_added.add(lk)
                    fig.add_trace(go.Scatter(
                        x=[op.iloc[0]["time"], trade["time"]],
                        y=[op.iloc[0]["fill_price"], trade["fill_price"]],
                        mode="lines",
                        line={"color": color, "width": 1,
                              "dash": "dot" if pnl < 0 else "solid"},
                        showlegend=False, hoverinfo="skip", opacity=0.4,
                    ))

                fig.add_trace(go.Scatter(
                    x=[trade["time"]], y=[trade["fill_price"]],
                    mode="markers",
                    marker={"symbol": "x", "size": 8,
                            "color": UP if pnl >= 0 else DOWN,
                            "line": {"color": BG, "width": 1}},
                    name=f"S{sc_num} exit", legendgroup=f"s{sc_num}",
                    showlegend=False,
                    hovertemplate=(f"S{sc_num} EXIT<br>Price: {trade['fill_price']:.2f}<br>"
                                   f'P&L: {"+" if pnl>=0 else ""}£{pnl:.2f}<extra></extra>'),
                ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
            font={"family": "monospace", "color": TEXT, "size": 11},
            margin={"t": 10, "r": 40, "b": 40, "l": 10}, height=360,
            xaxis={"gridcolor": BORDER, "zerolinecolor": BORDER,
                   "tickfont": {"color": MUTED},
                   "rangeslider": {"visible": False}, "type": "date"},
            yaxis={"gridcolor": BORDER, "zerolinecolor": BORDER,
                   "tickfont": {"color": MUTED}, "side": "right"},
            legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": MUTED, "size": 10},
                    "orientation": "h", "x": 0, "y": 1.08},
            hovermode="x unified",
            hoverlabel={"bgcolor": CARD, "font": {"color": TEXT, "family": "monospace"}},
        )

        pnl_str = f'{"+" if sym_pnl>=0 else ""}£{sym_pnl:.2f}'
        chart_components.append(html.Div([
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "10px"},
            children=[
                html.Span(sym_name, style={"fontSize": "14px", "fontWeight": "800",
                                            "color": GOLD}),
                html.Span(pnl_str, style={"fontSize": "14px", "fontWeight": "700",
                                           "color": UP if sym_pnl >= 0 else DOWN}),
            ]),
            dcc.Graph(figure=fig,
                      config={"displayModeBar": True,
                               "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                               "displaylogo": False},
                      style={"height": "360px"}),
        ], style={"marginBottom": "16px"}))

    if not chart_components:
        chart_components = [html.Div("No chart data available.",
                                     style={"color": MUTED, "padding": "20px"})]

    title = f"5m candles  ·  {len(all_sym_ids)} symbol(s)  ·  {len(df_sc)} scenarios"

    btn_style = {"fontSize": "11px", "padding": "6px 14px", "background": UP,
                 "color": BG, "border": f"1px solid {UP}",
                 "borderRadius": "6px", "cursor": "pointer", "fontWeight": "700"}

    return html.Div(chart_components), title, btn_style


# ── Scenarios: CSV download ───────────────────────────────────
@callback(
    Output("sc-download",    "data"),
    Input("sc-download-btn", "n_clicks"),
    dash.dependencies.State("sc-store",      "data"),
    prevent_initial_call=True,
)
def download_scenarios(_, store_data):
    if not store_data:
        return None
    df = pd.DataFrame(store_data)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return dcc.send_data_frame(df.to_csv, f"scenarios_{date_str}.csv", index=False)


# ── Journal: build daily summary dataframe ───────────────────
def calc_exposure_drawdown(date_str, all_df):
    """
    Maximum Adverse Exposure — uses fill prices from all deals as price checkpoints.

    For each open position, at every price event during its lifetime,
    we calculate the worst the position went against us (using the lowest
    price seen for BUYs, highest for SELLs). We sum across all simultaneously
    open positions to find the worst total floating loss at any point.

    This is purely from the CSV — no API calls needed.
    """
    date_utc  = pd.Timestamp(date_str).tz_localize("UTC")
    date_end  = date_utc + pd.Timedelta(days=1)

    day_all   = all_df[(all_df["time"] >= date_utc) & (all_df["time"] < date_end)].copy()
    if day_all.empty:
        return None

    openings   = day_all[day_all["is_closing"] == False]
    closings   = day_all[day_all["is_closing"] == True]
    all_prices = day_all[["time", "symbol_id", "fill_price"]].copy()

    # Build positions with scale factor derived from actual P&L
    positions = []
    for _, cl in closings.iterrows():
        op = openings[openings["position_id"] == cl["position_id"]]
        if op.empty:
            continue
        op         = op.iloc[0]
        price_diff = cl["fill_price"] - op["fill_price"]
        if op["direction"] == "SELL":
            price_diff = -price_diff
        vol    = op["volume"]
        scale  = (cl["pnl"] / (price_diff * vol)
                  if (price_diff != 0 and vol != 0) else 1.0)
        positions.append({
            "symbol_id":   cl["symbol_id"],
            "direction":   op["direction"],
            "volume":      vol,
            "entry_price": op["fill_price"],
            "entry_time":  op["time"],
            "exit_time":   cl["time"],
            "scale":       scale,
        })

    if not positions:
        return None

    pos_df = pd.DataFrame(positions)

    # Events = every fill_price timestamp during the day
    event_times = sorted(set(all_prices["time"].tolist()))
    if not event_times:
        return None

    worst_exposure = 0.0

    for t in event_times:
        open_pos = pos_df[
            (pos_df["entry_time"] <= t) & (pos_df["exit_time"] > t)
        ]
        if open_pos.empty:
            continue

        total_float = 0.0
        for _, pos in open_pos.iterrows():
            # Worst price seen for this symbol from entry up to now
            sym_px = all_prices[
                (all_prices["symbol_id"] == pos["symbol_id"]) &
                (all_prices["time"] >= pos["entry_time"]) &
                (all_prices["time"] <= t)
            ]["fill_price"]

            if sym_px.empty:
                continue

            if pos["direction"] == "BUY":
                worst_price = sym_px.min()
                adverse     = worst_price - pos["entry_price"]
            else:
                worst_price = sym_px.max()
                adverse     = pos["entry_price"] - worst_price

            total_float += adverse * pos["volume"] * pos["scale"]

        if total_float < worst_exposure:
            worst_exposure = total_float

    return round(worst_exposure, 2) if worst_exposure < 0 else 0.0


def build_daily_summary():
    """Aggregate all closing trades into per-day rows."""
    import math
    df_all  = pd.read_csv(DATA_FILE)
    df_all["time"] = pd.to_datetime(df_all["time"], format="ISO8601", utc=True)
    symbols = load_symbols()
    closing = df_all[df_all["is_closing"] == True].copy()
    if closing.empty:
        return pd.DataFrame()
    closing["date"] = closing["time"].dt.date

    def get_sessions_for_hour(hour):
        found = []
        for s in SESSIONS:
            st, en = s["start"], s["end"]
            if st < en:
                if st <= hour < en: found.append(s["name"])
            else:
                if hour >= st or hour < en: found.append(s["name"])
        return found

    rows = []
    for date, day_df in closing.groupby("date"):
        day_s      = day_df.sort_values("time")
        total_pnl  = day_s["pnl"].sum()
        total_comm = day_s["commission"].sum()
        n_trades   = len(day_s)
        wins       = len(day_s[day_s["pnl"] > 0])
        best       = day_s["pnl"].max()
        worst      = day_s["pnl"].min()

        # Closed-trade drawdown (fast — from CSV only)
        day_s = day_s.copy()
        day_s["cum_pnl"] = day_s["pnl"].cumsum()
        running_max = day_s["cum_pnl"].cummax()
        max_dd      = (day_s["cum_pnl"] - running_max).min()

        # Instruments
        sym_ids     = day_s["symbol_id"].unique()
        instruments = ", ".join([symbols.get(str(s), f"ID:{s}") for s in sym_ids])

        # Sessions touched
        all_hours = set(day_s["time"].dt.hour.tolist())
        seen_sess = []
        for h in sorted(all_hours):
            for s in get_sessions_for_hour(h):
                if s not in seen_sess: seen_sess.append(s)

        # First trade session
        first_hour    = day_s["time"].iloc[0].hour
        first_session = ", ".join(get_sessions_for_hour(first_hour)) or "Off-hours"

        rows.append({
            "Date":              str(date),
            "P&L (£)":           round(total_pnl, 2),
            "Commission (£)":    round(total_comm, 2),
            "Net (£)":           round(total_pnl + total_comm, 2),
            "Trades":            n_trades,
            "Wins":              wins,
            "Win %":             round(wins / n_trades * 100, 1) if n_trades else 0,
            "Best (£)":          round(best, 2),
            "Worst (£)":         round(worst, 2),
            "Closed DD (£)":     round(max_dd, 2),
            "Live DD (£)":       "—",   # populated on demand
            "Instruments":       instruments,
            "First Session":     first_session,
            "Sessions":          ", ".join(seen_sess),
        })

    return pd.DataFrame(rows)


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
        return {"fontSize": "11px", "padding": "5px 12px",
                "background": GOLD if active else CARD,
                "color": BG if active else MUTED,
                "border": f"1px solid {GOLD if active else BORDER}",
                "borderRadius": "6px", "cursor": "pointer",
                "fontWeight": "700" if active else "400"}
    return (sort_key,
            btn_style(sort_key == "date"),
            btn_style(sort_key == "pnl"),
            btn_style(sort_key == "trades"))


if __name__ == "__main__":
    print(f"\n  {SYMBOL} Trades Dashboard v{APP_VERSION}")
    print(f"  http://127.0.0.1:8050\n")
    app.run(debug=True)
