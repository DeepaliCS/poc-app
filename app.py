# app.py
# ── Proof of Concept App ──────────────────────────────────────
# Version: 1.2.0 — added min/max tracker + sparkline history chart

import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import plotly.graph_objects as go
from datetime import datetime

APP_VERSION = "1.2.0"

app = dash.Dash(__name__, title="POC App")

THEMES = {
    "dark":  {"bg": "#0f0f0f", "card": "#1a1a1a", "border": "#2a2a2a",
              "text": "#e0e0e0", "muted": "#666666", "accent": "#00e5ff"},
    "green": {"bg": "#0a0f0a", "card": "#111a11", "border": "#1a2a1a",
              "text": "#d0e8d0", "muted": "#4a664a", "accent": "#00ff88"},
    "amber": {"bg": "#0f0d08", "card": "#1a1708", "border": "#2a2408",
              "text": "#e8e0c8", "muted": "#665a30", "accent": "#ffb300"},
}

def make_sparkline(history, accent, border):
    if len(history) < 2:
        fig = go.Figure()
    else:
        fig = go.Figure(go.Scatter(
            x=list(range(len(history))),
            y=history,
            mode="lines",
            line={"color": accent, "width": 2, "shape": "spline"},
            fill="tozeroy",
            fillcolor=accent.replace(")", ",0.08)").replace("rgb", "rgba") if "rgb" in accent else accent + "14",
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        margin={"t": 0, "r": 0, "b": 0, "l": 0},
        height=60,
        xaxis={"visible": False},
        yaxis={"visible": False},
        showlegend=False,
    )
    return fig

app.layout = html.Div(id="root", style={
    "background": "#0f0f0f", "minHeight": "100vh",
    "display": "flex", "flexDirection": "column",
    "alignItems": "center", "justifyContent": "center",
    "fontFamily": "monospace", "color": "#e0e0e0"
}, children=[
    html.Div(style={
        "background": "#1a1a1a", "border": "1px solid #2a2a2a",
        "borderRadius": "16px", "padding": "40px",
        "width": "480px", "textAlign": "center"
    }, children=[

        html.Div("POC APP", style={"fontSize": "11px", "letterSpacing": "4px",
                                    "color": "#666", "marginBottom": "6px"}),
        html.Div(f"v{APP_VERSION}", style={"fontSize": "22px", "fontWeight": "800",
                                           "color": "#00e5ff", "marginBottom": "20px"}),

        # Theme switcher
        html.Div(style={"display": "flex", "gap": "8px",
                        "justifyContent": "center", "marginBottom": "28px"},
        children=[
            html.Button("Dark",  id="theme-dark",  n_clicks=0,
                        style={"fontSize": "11px", "padding": "4px 12px", "background": "#1a1a1a",
                               "color": "#00e5ff", "border": "1px solid #00e5ff",
                               "borderRadius": "6px", "cursor": "pointer"}),
            html.Button("Green", id="theme-green", n_clicks=0,
                        style={"fontSize": "11px", "padding": "4px 12px", "background": "#1a1a1a",
                               "color": "#666", "border": "1px solid #2a2a2a",
                               "borderRadius": "6px", "cursor": "pointer"}),
            html.Button("Amber", id="theme-amber", n_clicks=0,
                        style={"fontSize": "11px", "padding": "4px 12px", "background": "#1a1a1a",
                               "color": "#666", "border": "1px solid #2a2a2a",
                               "borderRadius": "6px", "cursor": "pointer"}),
        ]),

        # Counter
        html.Div(id="counter-display",
                 style={"fontSize": "80px", "fontWeight": "800",
                        "color": "#e0e0e0", "lineHeight": "1", "marginBottom": "4px"}),

        # Click rate
        html.Div(id="rate-display",
                 style={"fontSize": "11px", "color": "#666", "marginBottom": "20px"}),

        # ── NEW: Min / Max stat pills ──────────────────────────
        html.Div(id="minmax-display",
                 style={"display": "flex", "gap": "10px", "justifyContent": "center",
                        "marginBottom": "20px"}),

        # ── NEW: Sparkline chart ───────────────────────────────
        html.Div(style={"marginBottom": "24px", "borderRadius": "8px",
                        "overflow": "hidden", "border": "1px solid #2a2a2a"},
        children=[
            html.Div("counter history", style={"fontSize": "9px", "letterSpacing": "2px",
                                                "textTransform": "uppercase", "color": "#444",
                                                "padding": "8px 12px 0"}),
            dcc.Graph(id="sparkline", config={"displayModeBar": False},
                      style={"height": "60px"},
                      figure=make_sparkline([], "#00e5ff", "#2a2a2a")),
        ]),

        # Buttons
        html.Div(style={"display": "flex", "gap": "12px",
                        "justifyContent": "center", "marginBottom": "28px"},
        children=[
            html.Button("−", id="btn-dec", n_clicks=0,
                        style={"fontSize": "24px", "width": "64px", "height": "64px",
                               "background": "#1a1a1a", "color": "#e0e0e0",
                               "border": "1px solid #2a2a2a", "borderRadius": "12px",
                               "cursor": "pointer"}),
            html.Button("Reset", id="btn-reset", n_clicks=0,
                        style={"fontSize": "13px", "padding": "0 20px", "height": "64px",
                               "background": "#1a1a1a", "color": "#666",
                               "border": "1px solid #2a2a2a", "borderRadius": "12px",
                               "cursor": "pointer"}),
            html.Button("+", id="btn-inc", n_clicks=0,
                        style={"fontSize": "24px", "width": "64px", "height": "64px",
                               "background": "#00e5ff", "color": "#0f0f0f",
                               "border": "none", "borderRadius": "12px",
                               "cursor": "pointer", "fontWeight": "800"}),
        ]),

        # Activity log
        html.Div(style={"textAlign": "left", "borderTop": "1px solid #2a2a2a",
                        "paddingTop": "16px"},
        children=[
            html.Div("Activity log", style={"fontSize": "10px", "letterSpacing": "2px",
                                             "textTransform": "uppercase", "color": "#666",
                                             "marginBottom": "8px"}),
            html.Div(id="activity-log",
                     style={"fontSize": "11px", "color": "#666", "height": "80px",
                            "overflowY": "auto", "display": "flex",
                            "flexDirection": "column", "gap": "4px"}),
        ]),
    ]),

    html.Div(f"version {APP_VERSION}  ·  edit app.py to make changes",
             style={"marginTop": "20px", "fontSize": "11px", "color": "#444"}),

    # State stores
    dcc.Store(id="counter-store", data=0),
    dcc.Store(id="log-store",     data=[]),
    dcc.Store(id="theme-store",   data="dark"),
    dcc.Store(id="clicks-store",  data={"count": 0, "start": None}),
    dcc.Store(id="history-store", data=[0]),
    dcc.Store(id="minmax-store",  data={"min": 0, "max": 0}),
])


@callback(
    Output("root", "style"),
    Output("theme-store", "data"),
    Input("theme-dark",  "n_clicks"),
    Input("theme-green", "n_clicks"),
    Input("theme-amber", "n_clicks"),
    prevent_initial_call=True,
)
def switch_theme(*_):
    tk = {"theme-dark": "dark", "theme-green": "green",
          "theme-amber": "amber"}.get(ctx.triggered_id, "dark")
    t = THEMES[tk]
    return {"background": t["bg"], "minHeight": "100vh", "display": "flex",
            "flexDirection": "column", "alignItems": "center",
            "justifyContent": "center", "fontFamily": "monospace",
            "color": t["text"]}, tk


@callback(
    Output("counter-display", "children"),
    Output("counter-store",   "data"),
    Output("log-store",       "data"),
    Output("activity-log",    "children"),
    Output("clicks-store",    "data"),
    Output("rate-display",    "children"),
    Output("history-store",   "data"),
    Output("minmax-store",    "data"),
    Output("sparkline",       "figure"),
    Output("minmax-display",  "children"),
    Input("btn-inc",   "n_clicks"),
    Input("btn-dec",   "n_clicks"),
    Input("btn-reset", "n_clicks"),
    State("counter-store", "data"),
    State("log-store",     "data"),
    State("clicks-store",  "data"),
    State("history-store", "data"),
    State("minmax-store",  "data"),
    State("theme-store",   "data"),
    prevent_initial_call=True,
)
def handle_buttons(inc, dec, reset, count, log, clicks, history, minmax, theme_key):
    triggered = ctx.triggered_id
    ts  = datetime.now().strftime("%H:%M:%S")
    now = datetime.now().timestamp()
    t   = THEMES[theme_key]

    if triggered == "btn-inc":
        count += 1
        log.append(f"{ts}  +1  →  {count}")
    elif triggered == "btn-dec":
        count -= 1
        log.append(f"{ts}  -1  →  {count}")
    elif triggered == "btn-reset":
        log.append(f"{ts}  reset  →  0")
        count = 0

    # History for sparkline (keep last 40 points)
    history.append(count)
    history = history[-40:]

    # Min / max
    minmax["min"] = min(minmax["min"], count)
    minmax["max"] = max(minmax["max"], count)

    # Click rate
    if clicks["start"] is None:
        clicks = {"count": 1, "start": now}
    else:
        clicks["count"] += 1
    elapsed   = max(now - (clicks["start"] or now), 1)
    rate      = round(clicks["count"] / elapsed, 2)
    rate_text = f"{rate} clicks/sec  ·  {clicks['count']} total"

    log      = log[-6:]
    log_items = [html.Div(e) for e in reversed(log)]

    # Sparkline
    spark = make_sparkline(history, t["accent"], t["border"])

    # Min/max pills
    pill_style = lambda c: {
        "fontSize": "11px", "padding": "4px 14px",
        "borderRadius": "20px", "border": f"1px solid {t['border']}",
        "color": c, "background": t["card"],
    }
    minmax_pills = [
        html.Div([html.Span("min  ", style={"color": t["muted"]}),
                  html.Span(str(minmax["min"]), style={"color": "#ff6b6b", "fontWeight": "700"})],
                 style=pill_style("#ff6b6b")),
        html.Div([html.Span("now  ", style={"color": t["muted"]}),
                  html.Span(str(count), style={"color": t["accent"], "fontWeight": "700"})],
                 style=pill_style(t["accent"])),
        html.Div([html.Span("max  ", style={"color": t["muted"]}),
                  html.Span(str(minmax["max"]), style={"color": "#a8ff78", "fontWeight": "700"})],
                 style=pill_style("#a8ff78")),
    ]

    return (str(count), count, log, log_items, clicks,
            rate_text, history, minmax, spark, minmax_pills)


@callback(
    Output("counter-display", "children", allow_duplicate=True),
    Input("counter-store", "data"),
    prevent_initial_call="initial_duplicate",
)
def init_display(count):
    return str(count)


if __name__ == "__main__":
    print(f"\n  POC App v{APP_VERSION}")
    print("  http://127.0.0.1:8050\n")
    app.run(debug=True)
