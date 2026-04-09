# dashboard/helpers.py
# Shared utility functions used across all dashboard pages.
# Extracted from app.py — do not duplicate these here and in app.py.

import os
import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from dotenv import load_dotenv
from dash import html

BASE_DIR     = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_FILE    = BASE_DIR / "data" / "trades.csv"
SYMBOLS_FILE = BASE_DIR / "data" / "symbols.json"

# ── Colour palette (single source of truth) ───────────────────
BG     = "#0a0a0a"
PANEL  = "#111111"
CARD   = "#161616"
BORDER = "#222222"
TEXT   = "#e0e0e0"
MUTED  = "#555555"
GOLD   = "#7eb8f7"
UP     = "#26a69a"
DOWN   = "#ef5350"


def load_trades():
    """Load closing trades from CSV. Returns DataFrame or None if no data."""
    if not DATA_FILE.exists():
        return None
    df = pd.read_csv(DATA_FILE)
    df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    df = df[df["is_closing"] == True].copy()
    return df if not df.empty else None


def load_symbols():
    """Load symbol ID → name map from JSON. Returns empty dict if missing."""
    if not SYMBOLS_FILE.exists():
        return {}
    with open(SYMBOLS_FILE) as f:
        return json.load(f)


def get_symbol_name(symbol_id, symbols):
    """Return human-readable symbol name for a given ID."""
    return symbols.get(str(symbol_id), f"Symbol {symbol_id}")


def stat_card(label, value, color=TEXT, sub=None):
    """Render a stat card for the overview and mobile pages."""
    return html.Div([
        html.Div(label, style={"fontSize": "9px", "letterSpacing": "2px",
                               "textTransform": "uppercase",
                               "color": MUTED, "marginBottom": "6px"}),
        html.Div(value, style={"fontSize": "22px", "fontWeight": "800", "color": color}),
        html.Div(sub, style={"fontSize": "10px", "color": MUTED, "marginTop": "2px"}) if sub else None,
    ], style={"background": CARD, "border": f"1px solid {BORDER}",
              "borderRadius": "10px", "padding": "16px 20px"})


def empty_fig(msg="No data"):
    """Return an empty Plotly figure with a centred message."""
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
    """Return shared Plotly layout dict used across all charts."""
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
