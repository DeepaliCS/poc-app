# app.py  v2.2.0 — timeframe selector added
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, callback, Input, Output
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

SYMBOL      = os.getenv("CTRADER_SYMBOL", "XAUUSD")
DATA_FILE   = BASE_DIR / "data" / "trades.csv"
APP_VERSION = "2.2.0"

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
    {"label": "All", "days": 9999},
]

app = Dash(__name__, title=f"{SYMBOL} Trades")

def load_trades():
    if not DATA_FILE.exists():
        return None
    df = pd.read_csv(DATA_FILE)
    df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    df = df[df["is_closing"] == True].copy()
    return df if not df.empty else None

def stat_card(label, value, color=TEXT, sub=None):
    return html.Div([
        html.Div(label, style={"fontSize": "9px", "letterSpacing": "2px",
                               "textTransform": "uppercase",
                               "color": MUTED, "marginBottom": "6px"}),
        html.Div(value, style={"fontSize": "22px", "fontWeight": "800", "color": color}),
        html.Div(sub, style={"fontSize": "10px", "color": MUTED, "marginTop": "2px"}) if sub else None,
    ], style={"background": CARD, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "16px 20px"})

def tf_button(label, active=False):
    return html.Button(label, id=f"tf-{label}",
        n_clicks=0,
        style={
            "fontSize": "11px", "padding": "6px 14px",
            "background": GOLD if active else CARD,
            "color": BG if active else MUTED,
            "border": f"1px solid {GOLD if active else BORDER}",
            "borderRadius": "6px", "cursor": "pointer",
            "fontWeight": "700" if active else "400",
        })

app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh", "padding": "28px",
           "fontFamily": "monospace", "color": TEXT},
    children=[

        # Header
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                        "alignItems": "flex-end", "marginBottom": "20px",
                        "paddingBottom": "20px", "borderBottom": f"1px solid {BORDER}"},
        children=[
            html.Div([
                html.Span(SYMBOL, style={"fontSize": "24px", "fontWeight": "800",
                                         "color": GOLD, "letterSpacing": "2px"}),
                html.Span("  TRADE HISTORY",
                          style={"fontSize": "10px", "color": MUTED, "letterSpacing": "3px"}),
            ]),
            html.Div([
                html.Div(id="last-updated",
                         style={"fontSize": "10px", "color": MUTED, "textAlign": "right",
                                "marginBottom": "6px"}),
                html.Button("⟳ Refresh Data", id="refresh-btn", n_clicks=0,
                            style={"fontSize": "11px", "padding": "6px 16px",
                                   "background": CARD, "color": TEXT,
                                   "border": f"1px solid {BORDER}",
                                   "borderRadius": "6px", "cursor": "pointer"}),
            ]),
        ]),

        # ── Timeframe selector ────────────────────────────────
        html.Div(style={"display": "flex", "alignItems": "center",
                        "gap": "8px", "marginBottom": "20px"},
        children=[
            html.Div("Period:", style={"fontSize": "10px", "color": MUTED,
                                       "letterSpacing": "1px", "marginRight": "4px"}),
            *[tf_button(tf["label"], active=(tf["label"] == "1W"))
              for tf in TIMEFRAMES],
        ]),

        # Stat cards
        html.Div(id="stat-cards",
                 style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
                        "gap": "12px", "marginBottom": "20px"}),

        # Cumulative P&L
        html.Div([
            html.Div(id="pnl-title",
                     style={"fontSize": "9px", "letterSpacing": "2px",
                            "textTransform": "uppercase", "color": MUTED,
                            "marginBottom": "12px"}),
            dcc.Graph(id="pnl-chart", config={"displayModeBar": False},
                      style={"height": "280px"}),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"}),

        # Bar + Donut
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                        "gap": "16px", "marginBottom": "16px"},
        children=[
            html.Div([
                html.Div("P&L per trade",
                         style={"fontSize": "9px", "letterSpacing": "2px",
                                "textTransform": "uppercase", "color": MUTED,
                                "marginBottom": "12px"}),
                dcc.Graph(id="bar-chart", config={"displayModeBar": False},
                          style={"height": "220px"}),
            ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                      "borderRadius": "10px", "padding": "20px"}),
            html.Div([
                html.Div("Buy vs Sell",
                         style={"fontSize": "9px", "letterSpacing": "2px",
                                "textTransform": "uppercase", "color": MUTED,
                                "marginBottom": "12px"}),
                dcc.Graph(id="donut-chart", config={"displayModeBar": False},
                          style={"height": "220px"}),
            ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                      "borderRadius": "10px", "padding": "20px"}),
        ]),

        # Trade table
        html.Div([
            html.Div("Trade log",
                     style={"fontSize": "9px", "letterSpacing": "2px",
                            "textTransform": "uppercase", "color": MUTED,
                            "marginBottom": "12px"}),
            html.Div(id="trade-table"),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px"}),

        dcc.Store(id="tf-store", data="1W"),
        dcc.Interval(id="interval", interval=60_000, n_intervals=0),
    ]
)

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
               "tickfont": {"color": MUTED}, "side": "right",
               "tickprefix": "£"},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": MUTED}},
        hovermode="x unified",
        hoverlabel={"bgcolor": CARD, "font": {"color": TEXT, "family": "monospace"}},
    )

# ── Timeframe button → store ──────────────────────────────────
@callback(
    Output("tf-store", "data"),
    *[Input(f"tf-{tf['label']}", "n_clicks") for tf in TIMEFRAMES],
    prevent_initial_call=True,
)
def set_timeframe(*_):
    from dash import ctx
    triggered = ctx.triggered_id  # e.g. "tf-2W"
    return triggered.replace("tf-", "") if triggered else "1W"

# ── Update button styles ──────────────────────────────────────
@callback(
    *[Output(f"tf-{tf['label']}", "style") for tf in TIMEFRAMES],
    Input("tf-store", "data"),
)
def update_btn_styles(active_tf):
    styles = []
    for tf in TIMEFRAMES:
        active = (tf["label"] == active_tf)
        styles.append({
            "fontSize": "11px", "padding": "6px 14px",
            "background": GOLD if active else CARD,
            "color": BG if active else MUTED,
            "border": f"1px solid {GOLD if active else BORDER}",
            "borderRadius": "6px", "cursor": "pointer",
            "fontWeight": "700" if active else "400",
        })
    return styles

# ── Main data callback ────────────────────────────────────────
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
    Input("refresh-btn",   "n_clicks"),
)
def update(active_tf, _i, _r):
    df_all = load_trades()

    if df_all is None:
        empty = empty_fig("No trade data — run fetch_data.py first")
        cards = [stat_card("No data", "—") for _ in range(5)]
        msg   = html.Div("No data.", style={"color": MUTED, "fontSize": "12px"})
        return cards, empty, empty, empty, msg, "No data", "Cumulative P&L"

    # ── Filter by selected timeframe ──────────────────────────
    days = next((t["days"] for t in TIMEFRAMES if t["label"] == active_tf), 7)
    if days < 9999:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        df = df_all[df_all["time"] >= cutoff].copy()
    else:
        df = df_all.copy()

    if df.empty:
        empty = empty_fig(f"No trades in the last {active_tf}")
        cards = [stat_card(f"No trades ({active_tf})", "—") for _ in range(5)]
        msg   = html.Div(f"No trades found in this period.",
                         style={"color": MUTED, "fontSize": "12px"})
        updated = f"Updated {datetime.now().strftime('%H:%M:%S')}"
        return cards, empty, empty, empty, msg, updated, f"Cumulative P&L · {active_tf}"

    # ── Stats ──────────────────────────────────────────────────
    total_pnl = df["pnl"].sum()
    wins      = df[df["pnl"] > 0]
    losses    = df[df["pnl"] < 0]
    win_rate  = len(wins) / len(df) * 100 if len(df) else 0
    pnl_color = UP if total_pnl >= 0 else DOWN

    # Daily average
    if days < 9999:
        actual_days = max((df["time"].max() - df["time"].min()).days, 1)
        daily_avg   = total_pnl / max(actual_days, 1)
        sub_pnl     = f"£{daily_avg:+.2f}/day avg"
    else:
        sub_pnl = f"{len(df)} total trades"

    cards = [
        stat_card("Total P&L",
                  f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}',
                  pnl_color, sub_pnl),
        stat_card("Trades", str(len(df)), TEXT,
                  f"{len(wins)}W  {len(losses)}L"),
        stat_card("Win rate", f"{win_rate:.1f}%",
                  UP if win_rate >= 50 else DOWN),
        stat_card("Best",  f'+£{df["pnl"].max():.2f}', UP),
        stat_card("Worst", f'£{df["pnl"].min():.2f}',  DOWN),
    ]

    df = df.sort_values("time").reset_index(drop=True)
    df["cum_pnl"] = df["pnl"].cumsum()

    # ── Cumulative P&L ────────────────────────────────────────
    pnl_fig = go.Figure()
    # Zero reference line first (so it sits behind)
    pnl_fig.add_hline(y=0, line_color=BORDER, line_width=1)
    pnl_fig.add_trace(go.Scatter(
        x=df["time"], y=df["cum_pnl"],
        mode="lines+markers",
        line={"color": GOLD, "width": 2, "shape": "spline"},
        marker={"size": 5,
                "color": [UP if v >= 0 else DOWN for v in df["cum_pnl"]]},
        fill="tozeroy",
        fillcolor="rgba(240,180,41,0.07)",
        hovertemplate="%{x|%d %b %H:%M}<br>£%{y:.2f}<extra></extra>",
    ))
    pnl_fig.update_layout(**base_layout())

    # ── Per-trade bars ────────────────────────────────────────
    bar_fig = go.Figure(go.Bar(
        x=df["time"], y=df["pnl"],
        marker={"color": [UP if p >= 0 else DOWN for p in df["pnl"]],
                "opacity": 0.85},
        hovertemplate="%{x|%d %b %H:%M}<br>£%{y:.2f}<extra></extra>",
    ))
    bar_fig.update_layout(**base_layout())

    # ── Donut ─────────────────────────────────────────────────
    buys  = len(df[df["direction"] == "BUY"])
    sells = len(df[df["direction"] == "SELL"])
    donut_fig = go.Figure(go.Pie(
        values=[buys, sells] if (buys + sells) > 0 else [1, 1],
        labels=["Buy", "Sell"], hole=0.62,
        marker={"colors": [UP, DOWN]},
        textinfo="percent+label",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    donut_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "monospace", "color": TEXT, "size": 11},
        margin={"t": 10, "r": 10, "b": 10, "l": 10},
        showlegend=False,
        annotations=[{"text": f"{len(df)}<br>trades", "x": 0.5, "y": 0.5,
                      "showarrow": False,
                      "font": {"size": 14, "color": TEXT},
                      "xref": "paper", "yref": "paper"}],
    )

    # ── Table ─────────────────────────────────────────────────
    th  = {"fontSize": "9px", "letterSpacing": "1px", "textTransform": "uppercase",
           "color": MUTED, "padding": "8px 12px",
           "borderBottom": f"1px solid {BORDER}", "textAlign": "right",
           "background": CARD}
    thl = {**th, "textAlign": "left"}
    def td(c=TEXT):
        return {"fontSize": "11px", "color": c, "padding": "8px 12px",
                "textAlign": "right", "borderBottom": f"1px solid {BORDER}"}
    tdl = lambda c=TEXT: {**td(c), "textAlign": "left"}

    rows = [html.Tr([
        html.Th("Time",       style=thl),
        html.Th("Side",       style=th),
        html.Th("Volume",     style=th),
        html.Th("Fill price", style=th),
        html.Th("P&L",        style=th),
    ])]
    for _, row in df.sort_values("time", ascending=False).head(30).iterrows():
        pc    = UP if row["pnl"] >= 0 else DOWN
        dir_c = UP if row["direction"] == "BUY" else DOWN
        rows.append(html.Tr([
            html.Td(row["time"].strftime("%d %b  %H:%M"), style=tdl()),
            html.Td(row["direction"],                      style=td(dir_c)),
            html.Td(f'{row["volume"]:.2f}',                style=td()),
            html.Td(f'{row["fill_price"]:.2f}',            style=td()),
            html.Td(f'{"+" if row["pnl"]>=0 else ""}£{row["pnl"]:.2f}', style=td(pc)),
        ]))

    table   = html.Table(rows, style={"width": "100%", "borderCollapse": "collapse"})
    updated = (f"Updated {datetime.now().strftime('%H:%M:%S')}  ·  "
               f"{len(df)} trades  ·  "
               f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}')
    title   = f"Cumulative P&L · {active_tf}"

    return cards, pnl_fig, bar_fig, donut_fig, table, updated, title


if __name__ == "__main__":
    print(f"\n  {SYMBOL} Trades Dashboard v{APP_VERSION}")
    print(f"  http://127.0.0.1:8050\n")
    app.run(debug=True)
