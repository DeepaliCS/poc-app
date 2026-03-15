# app.py  v2.3.0 — two-page app: overview + daily trade view
import os, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.graph_objects as go
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
GOLD   = "#f0b429"
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
            html.Span(SYMBOL, style={"fontSize": "22px", "fontWeight": "800",
                                      "color": GOLD, "letterSpacing": "2px"}),
            html.Span("  TRADE HISTORY",
                      style={"fontSize": "10px", "color": MUTED, "letterSpacing": "3px"}),
        ]),
        html.Div(style={"display": "flex", "gap": "8px"}, children=[
            nav_btn("📊  Overview",    "nav-overview", active=(active_page=="overview")),
            nav_btn("📅  Daily View",  "nav-daily",    active=(active_page=="daily")),
            nav_btn("🕯  Market View", "nav-market",   active=(active_page=="market")),
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

# ── Page 3: Market View ───────────────────────────────────────
CANDLE_TFS = [
    {"label": "5m",  "minutes": 5,   "period": 5},
    {"label": "15m", "minutes": 15,  "period": 6},
    {"label": "1h",  "minutes": 60,  "period": 8},
]

page_market = html.Div(id="page-market", children=[
    header("market"),

    # Controls row
    html.Div(style={"display": "flex", "alignItems": "center", "gap": "16px",
                    "marginBottom": "24px", "background": PANEL,
                    "border": f"1px solid {BORDER}",
                    "borderRadius": "10px", "padding": "16px 20px"},
    children=[
        html.Div("Date:", style={"fontSize": "10px", "color": MUTED,
                                  "letterSpacing": "2px", "textTransform": "uppercase"}),
        dcc.DatePickerSingle(
            id="market-date-picker",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            display_format="DD MMM YYYY",
        ),
        html.Div("Timeframe:", style={"fontSize": "10px", "color": MUTED,
                                       "letterSpacing": "2px", "textTransform": "uppercase",
                                       "marginLeft": "16px"}),
        html.Div(style={"display": "flex", "gap": "6px"}, children=[
            html.Button(tf["label"], id=f"ctf-{tf['label']}", n_clicks=0,
                        style={"fontSize": "11px", "padding": "5px 12px",
                               "background": GOLD if tf["label"] == "5m" else CARD,
                               "color": BG if tf["label"] == "5m" else MUTED,
                               "border": f"1px solid {GOLD if tf['label'] == '5m' else BORDER}",
                               "borderRadius": "6px", "cursor": "pointer",
                               "fontWeight": "700" if tf["label"] == "5m" else "400"})
            for tf in CANDLE_TFS
        ]),
        html.Div(id="market-day-summary",
                 style={"fontSize": "11px", "color": MUTED, "marginLeft": "auto"}),
    ]),

    # Loading indicator + charts
    dcc.Loading(
        id="market-loading",
        type="circle",
        color=GOLD,
        children=html.Div(id="market-charts"),
    ),

    dcc.Store(id="ctf-store", data="5m"),
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
    Output("page-store",   "data"),
    Input("nav-overview",  "n_clicks"),
    Input("nav-daily",     "n_clicks"),
    Input("nav-market",    "n_clicks"),
    prevent_initial_call=True,
)
def switch_page(*_):
    triggered = ctx.triggered_id
    if triggered == "nav-daily":   return "daily"
    if triggered == "nav-market":  return "market"
    return "overview"

@callback(
    Output("page-content", "children"),
    Input("page-store",    "data"),
)
def render_page(page):
    if page == "daily":  return page_daily
    if page == "market": return page_market
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
@callback(
    Output("ctf-store", "data"),
    *[Input(f"ctf-{tf['label']}", "n_clicks") for tf in CANDLE_TFS],
    prevent_initial_call=True,
)
def set_ctf(*_):
    return ctx.triggered_id.replace("ctf-", "") if ctx.triggered_id else "5m"

@callback(
    *[Output(f"ctf-{tf['label']}", "style") for tf in CANDLE_TFS],
    Input("ctf-store", "data"),
)
def update_ctf_styles(active):
    return [{
        "fontSize": "11px", "padding": "5px 12px",
        "background": GOLD if tf["label"] == active else CARD,
        "color": BG if tf["label"] == active else MUTED,
        "border": f"1px solid {GOLD if tf['label'] == active else BORDER}",
        "borderRadius": "6px", "cursor": "pointer",
        "fontWeight": "700" if tf["label"] == active else "400",
    } for tf in CANDLE_TFS]

# ── Market view: main chart callback ─────────────────────────
@callback(
    Output("market-charts",      "children"),
    Output("market-day-summary", "children"),
    Input("market-date-picker",  "date"),
    Input("ctf-store",           "data"),
)
def update_market(selected_date, tf_label):
    if not selected_date:
        return html.Div("Pick a date.", style={"color": MUTED}), ""

    df_all  = load_trades()
    symbols = load_symbols()
    if df_all is None:
        return html.Div("No trade data.", style={"color": MUTED}), ""

    sel_dt  = pd.to_datetime(selected_date).tz_localize("UTC")
    sel_end = sel_dt + timedelta(days=1)
    df_day  = df_all[(df_all["time"] >= sel_dt) & (df_all["time"] < sel_end)].copy()

    if df_day.empty:
        return html.Div([
            html.Div("📭  No trades on this day.",
                     style={"color": MUTED, "fontSize": "14px",
                            "padding": "40px", "textAlign": "center"}),
        ]), "No trades this day"

    tf_info   = next((t for t in CANDLE_TFS if t["label"] == tf_label), CANDLE_TFS[0])
    period    = tf_info["period"]
    minutes   = tf_info["minutes"]

    # Fetch candles from cTrader for each symbol traded that day
    charts = []
    total_pnl = df_day["pnl"].sum()
    sym_ids   = df_day["symbol_id"].unique()

    summary = (f"{len(df_day)} trades  ·  "
               f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}  ·  '
               f"{len(sym_ids)} symbol(s)  ·  {tf_label} candles")

    for sym_id in sym_ids:
        df_sym   = df_day[df_day["symbol_id"] == sym_id].copy()
        sym_name = get_symbol_name(sym_id, symbols)
        sym_pnl  = df_sym["pnl"].sum()

        # Fetch OHLCV from cTrader
        candles = fetch_candles_sync(sym_id, sel_dt, sel_end, period, minutes)

        if candles is None or candles.empty:
            charts.append(html.Div([
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "marginBottom": "12px"},
                children=[
                    html.Span(sym_name, style={"fontSize": "16px", "fontWeight": "800",
                                               "color": GOLD}),
                    html.Span(f'{"+" if sym_pnl>=0 else ""}£{sym_pnl:.2f}',
                              style={"fontSize": "16px", "fontWeight": "800",
                                     "color": UP if sym_pnl>=0 else DOWN}),
                ]),
                html.Div(f"Could not fetch {tf_label} candles for {sym_name}.",
                         style={"color": MUTED, "fontSize": "12px", "padding": "20px 0"}),
            ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                      "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"}))
            continue

        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=candles["time"],
            open=candles["open"], high=candles["high"],
            low=candles["low"],   close=candles["close"],
            name=sym_name,
            increasing_line_color=UP,   increasing_fillcolor=UP,
            decreasing_line_color=DOWN, decreasing_fillcolor=DOWN,
            line={"width": 1},
        ))

        # Trade entry markers
        for _, trade in df_sym.iterrows():
            is_buy = trade["direction"] == "BUY"
            color  = UP if is_buy else DOWN
            symbol = "triangle-up" if is_buy else "triangle-down"
            label  = f'{"+" if trade["pnl"]>=0 else ""}£{trade["pnl"]:.2f}'

            fig.add_trace(go.Scatter(
                x=[trade["time"]],
                y=[trade["fill_price"]],
                mode="markers+text",
                marker={"symbol": symbol, "size": 14, "color": color,
                        "line": {"color": BG, "width": 1}},
                text=[label],
                textposition="top center" if is_buy else "bottom center",
                textfont={"size": 9, "color": color},
                name=trade["direction"],
                showlegend=False,
                hovertemplate=(
                    f"{trade['direction']}<br>"
                    f"Price: {trade['fill_price']:.2f}<br>"
                    f"P&L: {label}<br>"
                    f"Vol: {trade['volume']:.2f}<extra></extra>"
                ),
            ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
            font={"family": "monospace", "color": TEXT, "size": 11},
            margin={"t": 10, "r": 40, "b": 40, "l": 10},
            height=320,
            xaxis={
                "gridcolor": BORDER, "zerolinecolor": BORDER,
                "tickfont": {"color": MUTED},
                "rangeslider": {"visible": False},
                "type": "date",
            },
            yaxis={
                "gridcolor": BORDER, "zerolinecolor": BORDER,
                "tickfont": {"color": MUTED}, "side": "right",
            },
            legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": MUTED}},
            hovermode="x unified",
            hoverlabel={"bgcolor": CARD, "font": {"color": TEXT, "family": "monospace"}},
        )

        charts.append(html.Div([
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "12px"},
            children=[
                html.Div([
                    html.Span(sym_name, style={"fontSize": "16px", "fontWeight": "800",
                                               "color": GOLD}),
                    html.Span(f"  {tf_label} candles  ·  {len(df_sym)} trades",
                              style={"fontSize": "10px", "color": MUTED, "marginLeft": "8px"}),
                ]),
                html.Div(f'{"+" if sym_pnl>=0 else ""}£{sym_pnl:.2f}',
                         style={"fontSize": "18px", "fontWeight": "800",
                                "color": UP if sym_pnl>=0 else DOWN}),
            ]),
            dcc.Graph(figure=fig, config={"displayModeBar": True,
                                           "modeBarButtonsToRemove": ["lasso2d","select2d"],
                                           "displaylogo": False}),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"}))

    return html.Div(charts), summary


def digits_from_raw(raw_value, symbol_id):
    """Find correct price divisor by matching raw bar value to known fill_price."""
    import math
    df = load_trades()
    if df is not None:
        sym_trades = df[df["symbol_id"] == symbol_id]
        if not sym_trades.empty and raw_value > 0:
            target = sym_trades["fill_price"].median()
            if target > 0:
                d = round(math.log10(raw_value / target))
                d = max(0, min(d, 10))
                print(f"  → digits={d}, price≈{raw_value/(10**d):.2f} (target={target:.2f})")
                return d
    # Fallback: find divisor landing in 10–500,000
    for d in range(10):
        if 10 < raw_value / (10**d) < 500_000:
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

    done_event.wait(timeout=30)
    return state["candles"]


if __name__ == "__main__":
    print(f"\n  {SYMBOL} Trades Dashboard v{APP_VERSION}")
    print(f"  http://127.0.0.1:8050\n")
    app.run(debug=True)
