# app.py
# ── Proof of Concept App ──────────────────────────────────────
# A simple Dash app we'll use to practice making and tracking changes.
# Version: 1.0.0

import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
from datetime import datetime

APP_VERSION = "1.0.0"

app = dash.Dash(__name__, title="POC App")

BG      = "#0f0f0f"
CARD    = "#1a1a1a"
BORDER  = "#2a2a2a"
TEXT    = "#e0e0e0"
MUTED   = "#666666"
ACCENT  = "#00e5ff"

app.layout = html.Div(style={"background": BG, "minHeight": "100vh",
                              "display": "flex", "flexDirection": "column",
                              "alignItems": "center", "justifyContent": "center",
                              "fontFamily": "monospace", "color": TEXT},
children=[
    html.Div(style={"background": CARD, "border": f"1px solid {BORDER}",
                    "borderRadius": "16px", "padding": "48px",
                    "width": "480px", "textAlign": "center"},
    children=[

        html.Div("POC APP", style={"fontSize": "11px", "letterSpacing": "4px",
                                    "color": MUTED, "marginBottom": "8px"}),
        html.Div(f"v{APP_VERSION}", style={"fontSize": "28px", "fontWeight": "800",
                                           "color": ACCENT, "marginBottom": "40px"}),

        # Counter display
        html.Div(id="counter-display",
                 style={"fontSize": "80px", "fontWeight": "800",
                        "color": TEXT, "lineHeight": "1", "marginBottom": "32px"}),

        # Buttons
        html.Div(style={"display": "flex", "gap": "12px", "justifyContent": "center",
                        "marginBottom": "32px"},
        children=[
            html.Button("−", id="btn-dec", n_clicks=0,
                        style={"fontSize": "24px", "width": "64px", "height": "64px",
                               "background": CARD, "color": TEXT,
                               "border": f"1px solid {BORDER}", "borderRadius": "12px",
                               "cursor": "pointer"}),
            html.Button("Reset", id="btn-reset", n_clicks=0,
                        style={"fontSize": "13px", "padding": "0 20px", "height": "64px",
                               "background": CARD, "color": MUTED,
                               "border": f"1px solid {BORDER}", "borderRadius": "12px",
                               "cursor": "pointer"}),
            html.Button("+", id="btn-inc", n_clicks=0,
                        style={"fontSize": "24px", "width": "64px", "height": "64px",
                               "background": ACCENT, "color": BG,
                               "border": "none", "borderRadius": "12px",
                               "cursor": "pointer", "fontWeight": "800"}),
        ]),

        # Activity log
        html.Div(style={"textAlign": "left", "borderTop": f"1px solid {BORDER}",
                        "paddingTop": "20px"},
        children=[
            html.Div("Activity log", style={"fontSize": "10px", "letterSpacing": "2px",
                                             "textTransform": "uppercase", "color": MUTED,
                                             "marginBottom": "10px"}),
            html.Div(id="activity-log",
                     style={"fontSize": "11px", "color": MUTED,
                            "height": "80px", "overflowY": "auto",
                            "display": "flex", "flexDirection": "column", "gap": "4px"}),
        ]),
    ]),

    html.Div(f"version {APP_VERSION}  ·  edit app.py to make changes",
             style={"marginTop": "24px", "fontSize": "11px", "color": MUTED}),

    # Hidden state stores
    dcc.Store(id="counter-store", data=0),
    dcc.Store(id="log-store",     data=[]),
])


@callback(
    Output("counter-store", "data"),
    Output("log-store",     "data"),
    Input("btn-inc",   "n_clicks"),
    Input("btn-dec",   "n_clicks"),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True,
)
def update_counter(inc, dec, reset):
    from dash import ctx
    from dash.exceptions import PreventUpdate

    store_data   = dash.callback_context.states if hasattr(dash.callback_context, "states") else {}
    triggered_id = ctx.triggered_id

    # Read current value via pattern (workaround for stateless callbacks)
    # We pass count through the log length as a proxy — simpler: use State
    return dash.no_update, dash.no_update


# Proper callback with State
from dash import State

@callback(
    Output("counter-display", "children"),
    Output("counter-store",   "data",    allow_duplicate=True),
    Output("log-store",       "data",    allow_duplicate=True),
    Output("activity-log",    "children"),
    Input("btn-inc",    "n_clicks"),
    Input("btn-dec",    "n_clicks"),
    Input("btn-reset",  "n_clicks"),
    State("counter-store", "data"),
    State("log-store",     "data"),
    prevent_initial_call=True,
)
def handle_buttons(inc, dec, reset, count, log):
    from dash import ctx
    triggered = ctx.triggered_id
    ts = datetime.now().strftime("%H:%M:%S")

    if triggered == "btn-inc":
        count += 1
        log.append(f"{ts}  +1  →  {count}")
    elif triggered == "btn-dec":
        count -= 1
        log.append(f"{ts}  -1  →  {count}")
    elif triggered == "btn-reset":
        log.append(f"{ts}  reset  →  0")
        count = 0

    log = log[-6:]   # keep last 6 entries

    log_items = [html.Div(entry) for entry in reversed(log)]

    return str(count), count, log, log_items


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
