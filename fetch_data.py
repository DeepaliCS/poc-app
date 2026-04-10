# fetch_data.py — incremental fetch with local cache
# 
# Logic:
#   - If trades.csv does not exist → fetch FETCH_DAYS days from scratch
#   - If trades.csv exists        → only fetch from last saved date to today
#   - Merge, deduplicate on deal_id, save
#
# This means running ./run.sh daily only pulls that day's data — fast.

import os, sys, time, warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

CLIENT_ID     = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN  = os.getenv("CTRADER_ACCESS_TOKEN")
ACCOUNT_ID    = int(os.getenv("CTRADER_ACCOUNT_ID", "0"))
HOST          = os.getenv("CTRADER_HOST", "live.ctraderapi.com")
PORT          = int(os.getenv("CTRADER_PORT", "5035"))

FETCH_DAYS = 120   # only used when no cache exists

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT = DATA_DIR / "trades.csv"

def validate_config():
    missing = []
    if not CLIENT_ID or "your_" in CLIENT_ID:         missing.append("CTRADER_CLIENT_ID")
    if not CLIENT_SECRET or "your_" in CLIENT_SECRET: missing.append("CTRADER_CLIENT_SECRET")
    if not ACCESS_TOKEN or "your_" in ACCESS_TOKEN:   missing.append("CTRADER_ACCESS_TOKEN")
    if ACCOUNT_ID == 0:                               missing.append("CTRADER_ACCOUNT_ID")
    if missing:
        print(f"\n  ✗ Missing in .env: {', '.join(missing)}\n")
        sys.exit(1)

def get_fetch_range():
    """
    Decide what time range to fetch.
    Returns (from_ms, to_ms, mode) where mode is 'full' or 'incremental'.
    """
    now_ms = int(time.time() * 1000)

    if not OUTPUT.exists():
        # No cache — fetch full history
        from_ms = now_ms - (FETCH_DAYS * 24 * 60 * 60 * 1000)
        print(f"  → No cache found. Fetching full {FETCH_DAYS} days of history.")
        return from_ms, now_ms, "full"

    # Cache exists — check how stale it is
    try:
        df_existing = pd.read_csv(OUTPUT)
        df_existing["time"] = pd.to_datetime(
            df_existing["time"], format="ISO8601", utc=True
        )
        latest_ts = df_existing["time"].max()
        latest_ms = int(latest_ts.timestamp() * 1000)
        age_hours = (now_ms - latest_ms) / (1000 * 3600)
        age_days  = age_hours / 24

        print(f"  → Cache found: {len(df_existing):,} records, "
              f"latest {latest_ts.strftime('%d %b %Y %H:%M')} UTC "
              f"({age_hours:.1f}h ago)")

        if age_hours < 1:
            print("  → Cache is fresh (< 1 hour old). Skipping fetch.")
            return None, None, "skip"

        # Fetch from latest record minus 1 hour (overlap to catch any late-arriving deals)
        from_ms = latest_ms - (60 * 60 * 1000)
        print(f"  → Incremental fetch: last {age_days:.1f} day(s) of new data.")
        return from_ms, now_ms, "incremental"

    except Exception as e:
        print(f"  ⚠  Could not read cache ({e}). Fetching full history.")
        from_ms = now_ms - (FETCH_DAYS * 24 * 60 * 60 * 1000)
        return from_ms, now_ms, "full"

def fetch():
    validate_config()

    from_ms, to_ms, mode = get_fetch_range()

    if mode == "skip":
        print("  ✓ Using cached data — no fetch needed.\n")
        return

    print("\n  ┌─────────────────────────────────────────┐")
    if mode == "full":
        print(f"  │  Full fetch: {FETCH_DAYS} days from cTrader     │")
    else:
        days = (to_ms - from_ms) / (1000 * 60 * 60 * 24)
        print(f"  │  Incremental fetch: last {days:.1f} day(s)       │")
    print("  └─────────────────────────────────────────┘\n")

    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
            ProtoOAAccountAuthReq,     ProtoOAAccountAuthRes,
            ProtoOADealListReq,        ProtoOADealListRes,
            ProtoOATraderReq,          ProtoOATraderRes,
            ProtoOAErrorRes,
        )
        from twisted.internet import reactor
    except ImportError as e:
        print(f"  ✗ Import error: {e}"); sys.exit(1)

    # Split range into weekly chunks (cTrader max per request)
    chunk_ms = 7 * 24 * 60 * 60 * 1000
    chunks   = []
    cursor   = to_ms
    while cursor > from_ms:
        chunk_start = max(cursor - chunk_ms, from_ms)
        chunks.append((chunk_start, cursor))
        cursor = chunk_start

    print(f"  → Fetching {len(chunks)} chunk(s)…\n")

    all_rows = []
    state    = {"chunk_idx": 0, "done": False, "error": None, "balance": None}
    client   = Client(HOST, PORT, TcpProtocol)

    APP_AUTH_RES     = ProtoOAApplicationAuthRes().payloadType
    ACCOUNT_AUTH_RES = ProtoOAAccountAuthRes().payloadType
    DEAL_LIST_RES    = ProtoOADealListRes().payloadType
    TRADER_RES       = ProtoOATraderRes().payloadType
    ERROR_RES        = ProtoOAErrorRes().payloadType

    def extract(message, cls):
        try:    return Protobuf.extract(message, cls)
        except TypeError:
            obj = cls(); obj.ParseFromString(message.payload); return obj

    def request_next_chunk(c):
        idx = state["chunk_idx"]
        if idx >= len(chunks):
            finish()
            return
        start, end = chunks[idx]
        req = ProtoOADealListReq()
        req.ctidTraderAccountId = ACCOUNT_ID
        req.fromTimestamp       = start
        req.toTimestamp         = end
        c.send(req)

    def finish():
        # ── Save account balance snapshot ─────────────────────
        balance = state.get("balance")
        if balance is not None:
            import json as _json
            account_data = {
                "balance":    balance,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            }
            account_path = DATA_DIR / "account.json"
            with open(account_path, "w") as f:
                _json.dump(account_data, f, indent=2)
            print(f"  ✓ Account balance   : £{balance:,.2f}  → {account_path}")
        else:
            balance = None
            print("  ⚠  No account balance fetched — pnl_pct and volume_pct will be blank.")

        if all_rows:
            df_new = pd.DataFrame(all_rows)
            df_new = df_new.drop_duplicates(subset=["deal_id"])

            # ── Enrich with account balance metrics ───────────
            df_new["balance_at_fetch"] = balance if balance is not None else None
            if balance and balance > 0:
                df_new["pnl_pct"]    = (df_new["pnl"]    / balance * 100).round(4)
                df_new["volume_pct"] = (df_new["volume"]  / balance * 100).round(4)
            else:
                df_new["pnl_pct"]    = None
                df_new["volume_pct"] = None

            # Merge with existing cache if incremental
            if mode == "incremental" and OUTPUT.exists():
                df_old = pd.read_csv(OUTPUT)
                # Backfill balance columns into old rows if they don't exist yet
                for col in ["balance_at_fetch", "pnl_pct", "volume_pct"]:
                    if col not in df_old.columns:
                        if col == "balance_at_fetch":
                            df_old[col] = balance
                        elif balance and balance > 0:
                            if col == "pnl_pct":
                                df_old[col] = (df_old["pnl"] / balance * 100).round(4)
                            elif col == "volume_pct":
                                df_old[col] = (df_old["volume"] / balance * 100).round(4)
                        else:
                            df_old[col] = None
                df_combined = pd.concat([df_old, df_new], ignore_index=True)
                df_combined = df_combined.drop_duplicates(subset=["deal_id"])
                # Convert time column to string consistently before sorting
                # to avoid Timestamp vs str comparison error
                df_combined["time"] = pd.to_datetime(
                    df_combined["time"], format="ISO8601", utc=True
                ).dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
                df_combined = df_combined.sort_values("time").reset_index(drop=True)
                df_combined.to_csv(OUTPUT, index=False)
                new_count = len(df_combined) - len(df_old)
                print(f"\n  ✓ Added {new_count} new records → {len(df_combined):,} total")
            else:
                df_new = df_new.sort_values("time").reset_index(drop=True)
                df_new.to_csv(OUTPUT, index=False)
                closing = df_new[df_new["is_closing"] == True]
                print(f"\n  ✓ Saved {len(df_new):,} deals → {OUTPUT}")
                print(f"  ✓ Closed positions : {len(closing)}")
                if not closing.empty:
                    print(f"  ✓ Total P&L        : £{closing['pnl'].sum():.2f}")

                    # Weekly breakdown
                    print(f"\n  Weekly P&L breakdown:")
                    closing_copy = closing.copy()
                    closing_copy["time"] = pd.to_datetime(
                        closing_copy["time"], format="ISO8601", utc=True
                    )
                    closing_copy["week"] = closing_copy["time"].dt.to_period("W")
                    for week, grp in closing_copy.groupby("week"):
                        wpnl = grp["pnl"].sum()
                        bar  = "█" * min(int(abs(wpnl) / 50), 20)
                        sign = "+" if wpnl >= 0 else ""
                        print(f"    {str(week):<20} {sign}£{wpnl:>8.2f}  {bar}")
        else:
            print("  ⚠  No new deals found.")

        state["done"] = True
        try: reactor.stop()
        except: pass

    def on_connected(c):
        print("  ✓ Connected to cTrader")
        req = ProtoOAApplicationAuthReq()
        req.clientId = CLIENT_ID; req.clientSecret = CLIENT_SECRET
        c.send(req)

    def on_disconnected(c, reason):
        if not state["done"]:
            state["error"] = str(reason)
        try: reactor.stop()
        except: pass

    def on_message(c, message):
        ptype = message.payloadType

        if ptype == APP_AUTH_RES:
            print("  ✓ App authenticated")
            req = ProtoOAAccountAuthReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.accessToken = ACCESS_TOKEN
            c.send(req)

        elif ptype == ACCOUNT_AUTH_RES:
            print("  ✓ Account authenticated\n")
            # Fetch account balance before pulling deals
            req = ProtoOATraderReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            c.send(req)

        elif ptype == TRADER_RES:
            res     = extract(message, ProtoOATraderRes)
            balance = res.trader.balance / 100   # cTrader sends balance in cents
            state["balance"] = balance
            print(f"  ✓ Account balance    : £{balance:,.2f}")
            request_next_chunk(c)

        elif ptype == DEAL_LIST_RES:
            res   = extract(message, ProtoOADealListRes)
            deals = res.deal
            idx   = state["chunk_idx"]
            start, end = chunks[idx]
            start_dt = datetime.fromtimestamp(start/1000, tz=timezone.utc).strftime("%d %b")
            end_dt   = datetime.fromtimestamp(end/1000,   tz=timezone.utc).strftime("%d %b")
            print(f"  ✓ Chunk {idx+1}/{len(chunks)}  "
                  f"({start_dt} → {end_dt})  {len(deals)} deals")

            for d in deals:
                if d.dealStatus != 2:
                    continue
                all_rows.append({
                    "deal_id":     d.dealId,
                    "position_id": d.positionId,
                    "symbol_id":   d.symbolId,
                    "direction":   "BUY" if d.tradeSide == 1 else "SELL",
                    "volume":      d.volume / 100,
                    "fill_price":  d.executionPrice,
                    "close_price": d.closePositionDetail.entryPrice
                                   if d.HasField("closePositionDetail") else 0,
                    "time":        datetime.fromtimestamp(
                                       d.executionTimestamp / 1000,
                                       tz=timezone.utc),
                    "pnl":         d.closePositionDetail.grossProfit / 100
                                   if d.HasField("closePositionDetail") else 0,
                    "commission":  d.commission / 100,
                    "is_closing":  d.HasField("closePositionDetail"),
                })

            state["chunk_idx"] += 1
            from twisted.internet import reactor as r
            r.callLater(0.3, request_next_chunk, c)

        elif ptype == ERROR_RES:
            err = extract(message, ProtoOAErrorRes)
            state["error"] = f"{err.errorCode}: {err.description}"
            try: reactor.stop()
            except: pass

    client.setConnectedCallback(on_connected)
    client.setDisconnectedCallback(on_disconnected)
    client.setMessageReceivedCallback(on_message)
    client.startService()
    reactor.run()

    if state["error"]:
        print(f"\n  ✗ Error: {state['error']}\n")
        sys.exit(1)
    print()

if __name__ == "__main__":
    fetch()
