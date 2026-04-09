# dashboard/scenarios.py
# Scenario detection and exposure drawdown calculation.
# Extracted from app.py — these functions power the Scenarios page.

import math
import pandas as pd
from datetime import timedelta
from pathlib import Path

from dashboard.helpers import DATA_FILE, load_symbols

# ── Scenario colour palette ───────────────────────────────────
SC_COLOURS = [
    "#00e5ff", "#f0b429", "#a8ff78", "#ff6b9d",
    "#c77dff", "#ff9800", "#00bcd4", "#e91e63",
    "#8bc34a", "#ff5722",
]


def calc_scenario_exposure(pos_ids, openings, closings_grp, all_prices):
    """
    Calculate max exposure drawdown for a single scenario.
    Uses fill prices as price checkpoints to find the worst
    simultaneous floating loss across all open positions.
    """
    positions = []
    for _, cl in closings_grp.iterrows():
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
            "symbol_id":   cl["symbol_id"],
            "direction":   op["direction"],
            "volume":      vol,
            "entry_price": op["fill_price"],
            "entry_time":  op["time"],
            "exit_time":   cl["time"],
            "scale":       scale,
        })

    if not positions:
        return 0.0

    pos_df      = pd.DataFrame(positions)
    event_times = sorted(set(all_prices["time"].tolist()))
    worst       = 0.0

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
        if total_float < worst:
            worst = total_float

    return round(worst, 2) if worst < 0 else 0.0


def build_scenarios(date_str, data_file=None):
    """
    Detect trading scenarios by clustering exits.
    A new scenario starts when there is a gap > 10 min between consecutive exits.
    This matches the pattern: burst of entries + quick closes = one dip scenario.

    Returns a DataFrame with one row per scenario, or an empty DataFrame
    if there are no trades on the given date.
    """
    _path = data_file if data_file is not None else DATA_FILE
    df_all = pd.read_csv(_path)
    df_all["time"] = pd.to_datetime(df_all["time"], format="ISO8601", utc=True)
    symbols = load_symbols()

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

    # Prepare price events for exposure calculation
    all_prices = df_all[["time", "symbol_id", "fill_price"]].copy()
    all_prices = all_prices[
        (all_prices["time"] >= sel_dt) & (all_prices["time"] < sel_end)
    ]

    rows = []
    for sc_num, grp in closings.groupby("scenario"):
        grp = grp.sort_values("time")

        pos_ids = grp["position_id"].tolist()
        entries = openings[openings["position_id"].isin(pos_ids)]

        first_entry = entries["time"].min() if not entries.empty else grp["time"].iloc[0]
        first_exit  = grp["time"].min()
        last_exit   = grp["time"].max()
        duration_s  = (last_exit - first_exit).total_seconds()

        if duration_s < 60:
            dur_str = f"{int(duration_s)}s"
        elif duration_s < 3600:
            dur_str = f"{int(duration_s//60)}m {int(duration_s%60)}s"
        else:
            dur_str = f"{int(duration_s//3600)}h {int((duration_s%3600)//60)}m"

        pnl     = grp["pnl"].sum()
        n       = len(grp)
        wins    = len(grp[grp["pnl"] > 0])
        best    = grp["pnl"].max()
        worst   = grp["pnl"].min()
        sym_ids = grp["symbol_id"].unique()
        syms_str = ", ".join([symbols.get(str(s), f"ID:{s}") for s in sym_ids])
        comm    = grp["commission"].sum()

        entry_dirs = entries[entries["position_id"].isin(pos_ids)]["direction"].value_counts()
        buys  = int(entry_dirs.get("BUY",  0))
        sells = int(entry_dirs.get("SELL", 0))

        sc_prices = all_prices[
            (all_prices["time"] >= first_entry) &
            (all_prices["time"] <= last_exit)
        ]
        exposure_dd = calc_scenario_exposure(pos_ids, openings, grp, sc_prices)

        rows.append({
            "Scenario":        int(sc_num),
            "Start":           first_entry.strftime("%H:%M:%S"),
            "First Close":     first_exit.strftime("%H:%M:%S"),
            "Last Close":      last_exit.strftime("%H:%M:%S"),
            "Duration":        dur_str,
            "Trades":          n,
            "Buys":            buys,
            "Sells":           sells,
            "P&L (£)":         round(pnl, 2),
            "Commission (£)":  round(comm, 2),
            "Net (£)":         round(pnl + comm, 2),
            "Win %":           round(wins / n * 100) if n else 0,
            "Best (£)":        round(best, 2),
            "Worst (£)":       round(worst, 2),
            "Exposure DD (£)": exposure_dd,
            "Instruments":     syms_str,
            "_sym_ids":        list(sym_ids),
            "_first_entry":    first_entry,
            "_last_exit":      last_exit,
        })

    return pd.DataFrame(rows)
