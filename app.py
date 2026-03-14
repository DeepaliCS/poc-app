# app.py
# ── cTrader Trades Dashboard ──────────────────────────────────
# Version: 2.0.0

import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, callback, Input, Output
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

SYMBOL    = os.getenv("CTRADER_SYMBOL", "XAUUSD")
DATA_FILE = BASE_DIR / "data" / "trades.csv"
APP_VERSION = "2.0.0"

BG     = "#0a0a0a"
PANEL  = "#111111"
CARD   = "#161616"
BORDER = "#222222"
TEXT   = "#e0e0e0"
MUTED  = "#555555"
GOLD   = "#f0b429"
UP     = "#26a69a"
DOWN   = "#ef5350"

app = Dash(__name__, title=f"{SYMBOL} Trades")

def load_trades():
    if not DATA_FILE.exists():
        return None
    df = pd.read_csv(DATA_FILE, parse_dates=["open_time", "close_time"])
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

app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh", "padding": "28px",
           "fontFamily": "monospace", "color": TEXT},
    children=[
        html.Div(style={"display": "flex", "justifyContent": "space-between",
                        "alignItems": "flex-end", "marginBottom": "28px",
                        "paddingBottom": "20px", "borderBottom": f"1px solid {BORDER}"},
        children=[
            html.Div([
                html.Span(SYMBOL, style={"fontSize": "24px", "fontWeight": "800",
                                         "color": GOLD, "letterSpacing": "2px"}),
                html.Span("  TRADES · PAST 7 DAYS",
                          style={"fontSize": "10px", "color": MUTED, "letterSpacing": "3px"}),
            ]),
            html.Div([
                html.Div(id="last-updated", style={"fontSize": "10px", "color": MUTED, "textAlign": "right"}),
                html.Button("⟳ Refresh", id="refresh-btn", n_clicks=0,
                            style={"marginTop": "6px", "fontSize": "11px", "padding": "6px 16px",
                                   "background": CARD, "color": TEXT,
                                   "border": f"1px solid {BORDER}",
                                   "borderRadius": "6px", "cursor": "pointer"}),
            ]),
        ]),
        html.Div(id="stat-cards",
                 style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
                        "gap": "12px", "marginBottom": "20px"}),
        html.Div([
            html.Div("Cumulative P&L", style={"fontSize": "9px", "letterSpacing": "2px",
                                               "textTransform": "uppercase",
                                               "color": MUTED, "marginBottom": "12px"}),
            dcc.Graph(id="pnl-chart", config={"displayModeBar": False}, style={"height": "280px"}),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"}),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                        "gap": "16px", "marginBottom": "16px"},
        children=[
            html.Div([
                html.Div("P&L per trade", style={"fontSize": "9px", "letterSpacing": "2px",
                                                  "textTransform": "uppercase",
                                                  "color": MUTED, "marginBottom": "12px"}),
                dcc.Graph(id="bar-chart", config={"displayModeBar": False}, style={"height": "220px"}),
            ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                      "borderRadius": "10px", "padding": "20px"}),
            html.Div([
                html.Div("Buy vs Sell", style={"fontSize": "9px", "letterSpacing": "2px",
                                               "textTransform": "uppercase",
                                               "color": MUTED, "marginBottom": "12px"}),
                dcc.Graph(id="donut-chart", config={"displayModeBar": False}, style={"height": "220px"}),
            ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                      "borderRadius": "10px", "padding": "20px"}),
        ]),
        html.Div([
            html.Div("Trade log", style={"fontSize": "9px", "letterSpacing": "2px",
                                          "textTransform": "uppercase",
                                          "color": MUTED, "marginBottom": "12px"}),
            html.Div(id="trade-table"),
        ], style={"background": PANEL, "border": f"1px solid {BORDER}",
                  "borderRadius": "10px", "padding": "20px"}),
        dcc.Interval(id="interval", interval=60_000, n_intervals=0),
    ]
)

def empty_fig():
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
        annotations=[{"text": "No data — run fetch_data.py first",
                      "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
                      "showarrow": False, "font": {"size": 13, "color": MUTED}}],
        xaxis={"visible": False}, yaxis={"visible": False},
        margin={"t": 0, "r": 0, "b": 0, "l": 0},
    )
    return fig

def base_layout():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
        font={"family": "monospace", "color": TEXT, "size": 11},
        margin={"t": 10, "r": 10, "b": 40, "l": 60},
        xaxis={"gridcolor": BORDER, "zerolinecolor": BORDER, "tickfont": {"color": MUTED}},
        yaxis={"gridcolor": BORDER, "zerolinecolor": BORDER,
               "tickfont": {"color": MUTED}, "side": "right"},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": MUTED}},
        hovermode="x unified",
        hoverlabel={"bgcolor": CARD, "font": {"color": TEXT, "family": "monospace"}},
    )

@callback(
    Output("stat-cards",   "children"),
    Output("pnl-chart",    "figure"),
    Output("bar-chart",    "figure"),
    Output("donut-chart",  "figure"),
    Output("trade-table",  "children"),
    Output("last-updated", "children"),
    Input("interval",      "n_intervals"),
    Input("refresh-btn",   "n_clicks"),
)
def update(_i, _r):
    df = load_trades()
    if df is None:
        empty = empty_fig()
        cards = [stat_card("No data", "—") for _ in range(5)]
        no_data = html.Div("Run fetch_data.py to load your trades.",
                           style={"color": MUTED, "fontSize": "12px", "padding": "20px 0"})
        return cards, empty, empty, empty, no_data, "No data loaded"

    total_pnl   = df["pnl"].sum()
    win_trades  = df[df["pnl"] > 0]
    loss_trades = df[df["pnl"] < 0]
    win_rate    = len(win_trades) / len(df) * 100 if len(df) else 0
    pnl_color   = UP if total_pnl >= 0 else DOWN
    sym         = "+" if total_pnl >= 0 else ""

    cards = [
        stat_card("Total P&L",   f"{sym}£{total_pnl:.2f}", pnl_color),
        stat_card("Trades",      str(len(df)), TEXT, f"{len(win_trades)}W  {len(loss_trades)}L"),
        stat_card("Win rate",    f"{win_rate:.1f}%", UP if win_rate >= 50 else DOWN),
        stat_card("Best trade",  f"+£{df['pnl'].max():.2f}", UP),
        stat_card("Worst trade", f"£{df['pnl'].min():.2f}", DOWN),
    ]

    df_s = df.sort_values("close_time").reset_index(drop=True)
    df_s["cum_pnl"] = df_s["pnl"].cumsum()

    pnl_fig = go.Figure()
    pnl_fig.add_trace(go.Scatter(
        x=df_s["close_time"], y=df_s["cum_pnl"],
        mode="lines+markers",
        line={"color": GOLD, "width": 2, "shape": "spline"},
        marker={"size": 5, "color": GOLD},
        fill="tozeroy", fillcolor="rgba(240,180,41,0.07)",
        hovertemplate="£%{y:.2f}<extra></extra>",
    ))
    pnl_fig.add_hline(y=0, line_color=BORDER, line_width=1)
    ly = base_layout(); ly["yaxis"]["tickprefix"] = "£"
    pnl_fig.update_layout(**ly)

    bar_colors = [UP if p >= 0 else DOWN for p in df_s["pnl"]]
    bar_fig = go.Figure(go.Bar(
        x=list(range(len(df_s))), y=df_s["pnl"],
        marker={"color": bar_colors, "opacity": 0.85},
        hovertemplate="Trade %{x}<br>£%{y:.2f}<extra></extra>",
    ))
    ly2 = base_layout(); ly2["yaxis"]["tickprefix"] = "£"
    bar_fig.update_layout(**ly2)

    buys  = len(df[df["direction"] == "BUY"])
    sells = len(df[df["direction"] == "SELL"])
    donut_fig = go.Figure(go.Pie(
        values=[buys, sells], labels=["Buy", "Sell"],
        hole=0.6, marker={"colors": [UP, DOWN]}, textinfo="percent",
    ))
    donut_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "monospace", "color": TEXT, "size": 11},
        margin={"t": 10, "r": 10, "b": 10, "l": 10},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": MUTED}},
        annotations=[{"text": f"{len(df)}<br>trades", "x": 0.5, "y": 0.5,
                      "showarrow": False, "font": {"size": 14, "color": TEXT},
                      "xref": "paper", "yref": "paper"}],
    )

    h  = {"fontSize": "9px", "letterSpacing": "1px", "textTransform": "uppercase",
          "color": MUTED, "padding": "8px 12px",
          "borderBottom": f"1px solid {BORDER}", "textAlign": "right"}
    hl = {**h, "textAlign": "left"}
    def cell(color=TEXT):
        return {"fontSize": "11px", "color": color, "padding": "8px 12px",
                "textAlign": "right", "borderBottom": f"1px solid {BORDER}"}

    rows = [html.Tr([
        html.Th("Time",      style=hl),
        html.Th("Direction", style=h),
        html.Th("Volume",    style=h),
        html.Th("Open",      style=h),
        html.Th("Close",     style=h),
        html.Th("P&L",       style=h),
    ])]
    for _, row in df_s.sort_values("close_time", ascending=False).head(20).iterrows():
        pc = UP if row["pnl"] >= 0 else DOWN
        rows.append(html.Tr([
            html.Td(row["close_time"].strftime("%d %b %H:%M"),
                    style={**cell(), "textAlign": "left"}),
            html.Td(row["direction"],
                    style=cell(UP if row["direction"] == "BUY" else DOWN)),
            html.Td(f'{row["volume"]:.2f}',     style=cell()),
            html.Td(f'{row["open_price"]:.2f}', style=cell()),
            html.Td(f'{row["close_price"]:.2f}',style=cell()),
            html.Td(f'{"+" if row["pnl"]>=0 else ""}£{row["pnl"]:.2f}', style=cell(pc)),
        ]))

    table   = html.Table(rows, style={"width": "100%", "borderCollapse": "collapse"})
    updated = f"Updated {datetime.now().strftime('%H:%M:%S')}  ·  {len(df)} trades"
    return cards, pnl_fig, bar_fig, donut_fig, table, updated

if __name__ == "__main__":
    print(f"\n  {SYMBOL} Trades Dashboard v{APP_VERSION}")
    print("  http://127.0.0.1:8050\n")
    app.run(debug=True)
