# app.py  v2.1.0 — columns matched to fetch_data.py output
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, callback, Input, Output
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

SYMBOL      = os.getenv("CTRADER_SYMBOL", "XAUUSD")
DATA_FILE   = BASE_DIR / "data" / "trades.csv"
APP_VERSION = "2.1.0"

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

# ── Load & filter to closing deals only ───────────────────────
def load_trades():
    if not DATA_FILE.exists():
        return None
    df = pd.read_csv(DATA_FILE, parse_dates=["time"])
    # Only closing deals have real P&L
    df = df[df["is_closing"] == True].copy()
    return df if not df.empty else None

def stat_card(label, value, color=TEXT, sub=None):
    return html.Div([
        html.Div(label, style={"fontSize": "9px", "letterSpacing": "2px",
                               "textTransform": "uppercase",
                               "color": MUTED, "marginBottom": "6px"}),
        html.Div(value, style={"fontSize": "22px", "fontWeight": "800", "color": color}),
        html.Div(sub,   style={"fontSize": "10px", "color": MUTED, "marginTop": "2px"}) if sub else None,
    ], style={"background": CARD, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "16px 20px"})

app.layout = html.Div(
    style={"background": BG, "minHeight": "100vh", "padding": "28px",
           "fontFamily": "monospace", "color": TEXT},
    children=[

        # Header
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
                html.Div(id="last-updated",
                         style={"fontSize": "10px", "color": MUTED, "textAlign": "right"}),
                html.Button("⟳ Refresh", id="refresh-btn", n_clicks=0,
                            style={"marginTop": "6px", "fontSize": "11px",
                                   "padding": "6px 16px", "background": CARD,
                                   "color": TEXT, "border": f"1px solid {BORDER}",
                                   "borderRadius": "6px", "cursor": "pointer"}),
            ]),
        ]),

        # Stat cards row
        html.Div(id="stat-cards",
                 style={"display": "grid", "gridTemplateColumns": "repeat(5,1fr)",
                        "gap": "12px", "marginBottom": "20px"}),

        # Cumulative P&L
        html.Div([
            html.Div("Cumulative P&L",
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
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PANEL,
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
        empty = empty_fig("No trade data — run fetch_data.py first")
        cards = [stat_card("No data", "—") for _ in range(5)]
        msg   = html.Div("No data loaded.",
                         style={"color": MUTED, "fontSize": "12px", "padding": "20px 0"})
        return cards, empty, empty, empty, msg, "No data"

    # ── Stats ──────────────────────────────────────────────────
    total_pnl   = df["pnl"].sum()
    wins        = df[df["pnl"] > 0]
    losses      = df[df["pnl"] < 0]
    win_rate    = len(wins) / len(df) * 100 if len(df) else 0
    pnl_color   = UP if total_pnl >= 0 else DOWN

    cards = [
        stat_card("Total P&L",
                  f'{"+" if total_pnl>=0 else ""}£{total_pnl:.2f}',
                  pnl_color),
        stat_card("Trades", str(len(df)), TEXT,
                  f"{len(wins)}W  {len(losses)}L"),
        stat_card("Win rate", f"{win_rate:.1f}%",
                  UP if win_rate >= 50 else DOWN),
        stat_card("Best",  f'+£{df["pnl"].max():.2f}', UP),
        stat_card("Worst", f'£{df["pnl"].min():.2f}',  DOWN),
    ]

    # ── Sort by time ───────────────────────────────────────────
    df = df.sort_values("time").reset_index(drop=True)
    df["cum_pnl"] = df["pnl"].cumsum()

    # ── Cumulative P&L line ────────────────────────────────────
    pnl_fig = go.Figure()
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
    pnl_fig.add_hline(y=0, line_color=BORDER, line_width=1)
    pnl_fig.update_layout(**base_layout())

    # ── Per-trade bar ──────────────────────────────────────────
    bar_fig = go.Figure(go.Bar(
        x=df["time"], y=df["pnl"],
        marker={"color": [UP if p >= 0 else DOWN for p in df["pnl"]],
                "opacity": 0.85},
        hovertemplate="%{x|%d %b %H:%M}<br>£%{y:.2f}<extra></extra>",
    ))
    bar_fig.update_layout(**base_layout())

    # ── Buy / Sell donut ───────────────────────────────────────
    buys  = len(df[df["direction"] == "BUY"])
    sells = len(df[df["direction"] == "SELL"])
    donut_fig = go.Figure(go.Pie(
        values=[buys, sells] if (buys + sells) > 0 else [1, 1],
        labels=["Buy", "Sell"],
        hole=0.62,
        marker={"colors": [UP, DOWN]},
        textinfo="percent+label",
        hovertemplate="%{label}: %{value} trades<extra></extra>",
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

    # ── Trade table ────────────────────────────────────────────
    th = {"fontSize": "9px", "letterSpacing": "1px", "textTransform": "uppercase",
          "color": MUTED, "padding": "8px 12px",
          "borderBottom": f"1px solid {BORDER}", "textAlign": "right",
          "background": CARD}
    thl = {**th, "textAlign": "left"}

    def td(color=TEXT):
        return {"fontSize": "11px", "color": color, "padding": "8px 12px",
                "textAlign": "right", "borderBottom": f"1px solid {BORDER}"}
    tdl = lambda c=TEXT: {**td(c), "textAlign": "left"}

    rows = [html.Tr([
        html.Th("Time",      style=thl),
        html.Th("Side",      style=th),
        html.Th("Volume",    style=th),
        html.Th("Fill price",style=th),
        html.Th("P&L",       style=th),
    ])]

    for _, row in df.sort_values("time", ascending=False).head(25).iterrows():
        pc  = UP if row["pnl"] >= 0 else DOWN
        dir_c = UP if row["direction"] == "BUY" else DOWN
        pnl_str = f'{"+" if row["pnl"]>=0 else ""}£{row["pnl"]:.2f}'
        rows.append(html.Tr([
            html.Td(row["time"].strftime("%d %b  %H:%M"), style=tdl()),
            html.Td(row["direction"],                      style=td(dir_c)),
            html.Td(f'{row["volume"]:.2f}',                style=td()),
            html.Td(f'{row["fill_price"]:.2f}',            style=td()),
            html.Td(pnl_str,                               style=td(pc)),
        ]))

    table   = html.Table(rows, style={"width": "100%", "borderCollapse": "collapse"})
    updated = (f"Updated {datetime.now().strftime('%H:%M:%S')}  ·  "
               f"{len(df)} closed trades  ·  "
               f'Total P&L: {"+" if total_pnl>=0 else ""}£{total_pnl:.2f}')

    return cards, pnl_fig, bar_fig, donut_fig, table, updated


if __name__ == "__main__":
    print(f"\n  {SYMBOL} Trades Dashboard v{APP_VERSION}")
    print(f"  http://127.0.0.1:8050\n")
    app.run(debug=True)
