# dashboard/journal.py
# Journal page logic — daily summary and exposure drawdown.
# Extracted from app.py.

import pandas as pd
from datetime import timedelta

from dashboard.helpers import DATA_FILE, load_symbols

# ── Session definitions (UTC hours) ──────────────────────────
SESSIONS = [
    {"name": "Sydney",   "start": 21, "end": 6},
    {"name": "Tokyo",    "start": 0,  "end": 9},
    {"name": "London",   "start": 8,  "end": 17},
    {"name": "New York", "start": 13, "end": 22},
]


def get_sessions_for_hour(hour):
    """Return list of session names active at the given UTC hour."""
    found = []
    for s in SESSIONS:
        st, en = s["start"], s["end"]
        if st < en:
            if st <= hour < en:
                found.append(s["name"])
        else:
            if hour >= st or hour < en:
                found.append(s["name"])
    return found


def calc_exposure_drawdown(date_str, all_df):
    """
    Maximum Adverse Exposure for a given day.
    Uses fill prices from all deals as price checkpoints.

    For each open position at every price event during its lifetime,
    calculates the worst simultaneous floating loss across all open positions.
    Returns 0.0 if no adverse exposure, None if no data for that day.
    """
    date_utc = pd.Timestamp(date_str).tz_localize("UTC")
    date_end = date_utc + pd.Timedelta(days=1)

    day_all = all_df[
        (all_df["time"] >= date_utc) & (all_df["time"] < date_end)
    ].copy()

    if day_all.empty:
        return None

    openings   = day_all[day_all["is_closing"] == False]
    closings   = day_all[day_all["is_closing"] == True]
    all_prices = day_all[["time", "symbol_id", "fill_price"]].copy()

    positions = []
    for _, cl in closings.iterrows():
        op = openings[openings["position_id"] == cl["position_id"]]
        if op.empty:
            continue
        op         = op.iloc[0]
        price_diff = cl["fill_price"] - op["fill_price"]
        if op["direction"] == "SELL":
            price_diff = -price_diff
        vol   = op["volume"]
        scale = (cl["pnl"] / (price_diff * vol)
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

    pos_df      = pd.DataFrame(positions)
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
            sym_px = all_prices[
                (all_prices["symbol_id"] == pos["symbol_id"]) &
                (all_prices["time"] >= pos["entry_time"]) &
                (all_prices["time"] <= t)
            ]["fill_price"]

            if sym_px.empty:
                continue

            if pos["direction"] == "BUY":
                adverse = sym_px.min() - pos["entry_price"]
            else:
                adverse = pos["entry_price"] - sym_px.max()

            total_float += adverse * pos["volume"] * pos["scale"]

        if total_float < worst_exposure:
            worst_exposure = total_float

    return round(worst_exposure, 2) if worst_exposure < 0 else 0.0


def build_daily_summary(data_file=None):
    """
    Aggregate all closing trades into per-day rows.
    Returns a DataFrame with one row per trading day.

    Accepts optional data_file path for testing.
    """
    _path = data_file if data_file is not None else DATA_FILE

    df_all = pd.read_csv(_path)
    df_all["time"] = pd.to_datetime(df_all["time"], format="ISO8601", utc=True)
    symbols = load_symbols()
    closing = df_all[df_all["is_closing"] == True].copy()

    if closing.empty:
        return pd.DataFrame()

    closing["date"] = closing["time"].dt.date

    rows = []
    for date, day_df in closing.groupby("date"):
        day_s      = day_df.sort_values("time")
        total_pnl  = day_s["pnl"].sum()
        total_comm = day_s["commission"].sum()
        n_trades   = len(day_s)
        wins       = len(day_s[day_s["pnl"] > 0])
        best       = day_s["pnl"].max()
        worst      = day_s["pnl"].min()

        day_s = day_s.copy()
        day_s["cum_pnl"] = day_s["pnl"].cumsum()
        running_max = day_s["cum_pnl"].cummax()
        max_dd      = (day_s["cum_pnl"] - running_max).min()

        sym_ids     = day_s["symbol_id"].unique()
        instruments = ", ".join([symbols.get(str(s), f"ID:{s}") for s in sym_ids])

        all_hours = set(day_s["time"].dt.hour.tolist())
        seen_sess = []
        for h in sorted(all_hours):
            for s in get_sessions_for_hour(h):
                if s not in seen_sess:
                    seen_sess.append(s)

        first_hour    = day_s["time"].iloc[0].hour
        first_session = ", ".join(get_sessions_for_hour(first_hour)) or "Off-hours"

        rows.append({
            "Date":           str(date),
            "P&L (£)":        round(total_pnl, 2),
            "Commission (£)": round(total_comm, 2),
            "Net (£)":        round(total_pnl + total_comm, 2),
            "Trades":         n_trades,
            "Wins":           wins,
            "Win %":          round(wins / n_trades * 100, 1) if n_trades else 0,
            "Best (£)":       round(best, 2),
            "Worst (£)":      round(worst, 2),
            "Closed DD (£)":  round(max_dd, 2),
            "Live DD (£)":    "—",
            "Instruments":    instruments,
            "First Session":  first_session,
            "Sessions":       ", ".join(seen_sess),
        })

    return pd.DataFrame(rows)
