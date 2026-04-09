# dashboard/floating_pnl.py
# Floating P&L time-series generator.
# Extracted from app.py — powers the downloadable floating P&L CSV.

import pandas as pd
from datetime import timedelta

from dashboard.helpers import DATA_FILE, load_symbols


def build_floating_pnl(date_str, data_file=None):
    """
    Generate a time-series of floating P&L for every position on a given day.

    For each price event while a position is open:
      BUY  → float = (current_price - entry_price) * volume * scale
      SELL → float = (entry_price - current_price) * volume * scale

    Returns a DataFrame or empty DataFrame if no data for that date.
    Accepts optional data_file path for testing.
    """
    _path = data_file if data_file is not None else DATA_FILE

    df_all = pd.read_csv(_path)
    df_all["time"] = pd.to_datetime(df_all["time"], format="ISO8601", utc=True)
    symbols = load_symbols()

    sel_dt  = pd.Timestamp(date_str).tz_localize("UTC")
    sel_end = sel_dt + timedelta(days=1)

    day_all = df_all[
        (df_all["time"] >= sel_dt) & (df_all["time"] < sel_end)
    ].copy()

    if day_all.empty:
        return pd.DataFrame()

    openings   = day_all[day_all["is_closing"] == False].copy()
    closings   = day_all[day_all["is_closing"] == True].copy().sort_values("time").reset_index(drop=True)
    all_prices = day_all[["time", "symbol_id", "fill_price"]].copy()

    if closings.empty:
        return pd.DataFrame()

    # Assign scenarios (same 10-min gap logic as build_scenarios)
    gaps = closings["time"].diff().dt.total_seconds().fillna(9999) / 60
    closings["scenario"] = (gaps > 10).cumsum() + 1

    positions = []
    for _, cl in closings.iterrows():
        op = openings[openings["position_id"] == cl["position_id"]]
        if op.empty:
            continue
        op = op.iloc[0]
        price_diff = cl["fill_price"] - op["fill_price"]
        if op["direction"] == "SELL":
            price_diff = -price_diff
        vol   = op["volume"]
        scale = (cl["pnl"] / (price_diff * vol)
                 if (price_diff != 0 and vol != 0) else 1.0)
        positions.append({
            "scenario":    cl["scenario"],
            "position_id": cl["position_id"],
            "symbol_id":   cl["symbol_id"],
            "symbol":      symbols.get(str(cl["symbol_id"]), str(cl["symbol_id"])),
            "direction":   op["direction"],
            "entry_price": op["fill_price"],
            "exit_price":  cl["fill_price"],
            "closed_pnl":  cl["pnl"],
            "entry_time":  op["time"],
            "exit_time":   cl["time"],
            "volume":      vol,
            "scale":       scale,
        })

    if not positions:
        return pd.DataFrame()

    pos_df      = pd.DataFrame(positions)
    event_times = sorted(all_prices["time"].unique())
    rows        = []

    for t in event_times:
        open_pos = pos_df[
            (pos_df["entry_time"] <= t) & (pos_df["exit_time"] > t)
        ]
        if open_pos.empty:
            continue

        scenario_totals = {}
        pos_floats      = {}

        for _, pos in open_pos.iterrows():
            sym_px = all_prices[
                (all_prices["symbol_id"] == pos["symbol_id"]) &
                (all_prices["time"] >= pos["entry_time"]) &
                (all_prices["time"] <= t)
            ]["fill_price"]

            current_price = sym_px.iloc[-1] if not sym_px.empty else pos["entry_price"]

            if pos["direction"] == "BUY":
                float_pnl = (current_price - pos["entry_price"]) * pos["volume"] * pos["scale"]
            else:
                float_pnl = (pos["entry_price"] - current_price) * pos["volume"] * pos["scale"]

            pos_floats[pos["position_id"]] = (current_price, round(float_pnl, 2))
            sc = pos["scenario"]
            scenario_totals[sc] = scenario_totals.get(sc, 0) + float_pnl

        for _, pos in open_pos.iterrows():
            if pos["position_id"] not in pos_floats:
                continue
            current_price, float_pnl = pos_floats[pos["position_id"]]
            sc = pos["scenario"]
            rows.append({
                "date":                 date_str,
                "scenario":             int(sc),
                "position_id":          pos["position_id"],
                "symbol":               pos["symbol"],
                "direction":            pos["direction"],
                "entry_price":          round(pos["entry_price"], 5),
                "exit_price":           round(pos["exit_price"], 5),
                "closed_pnl":           round(pos["closed_pnl"], 2),
                "time":                 t.strftime("%Y-%m-%d %H:%M:%S"),
                "price_at_time":        round(current_price, 5),
                "position_float_pnl":   float_pnl,
                "scenario_total_float": round(scenario_totals[sc], 2),
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values(
        ["scenario", "time", "position_id"]
    ).reset_index(drop=True)
