# fetch_data.py — fetches 90 days of deals from cTrader
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

# ── How far back to fetch ─────────────────────────────────────
FETCH_DAYS = 120

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

def fetch():
    validate_config()

    print("\n  ┌─────────────────────────────────────────┐")
    print(f"  │  Fetching {FETCH_DAYS} days of deals from cTrader  │")
    print("  └─────────────────────────────────────────┘\n")

    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
            ProtoOAAccountAuthReq,     ProtoOAAccountAuthRes,
            ProtoOADealListReq,        ProtoOADealListRes,
            ProtoOAErrorRes,
        )
        from twisted.internet import reactor
    except ImportError as e:
        print(f"  ✗ Import error: {e}"); sys.exit(1)

    now_ms   = int(time.time() * 1000)
    # cTrader API max window per request is 1 week — we loop in weekly chunks
    all_rows = []
    chunk_ms = 7 * 24 * 60 * 60 * 1000   # 1 week in ms
    chunks   = []
    cursor   = now_ms
    for _ in range((FETCH_DAYS // 7) + 1):
        chunk_end   = cursor
        chunk_start = cursor - chunk_ms
        chunks.append((chunk_start, chunk_end))
        cursor = chunk_start
        if (now_ms - chunk_start) >= FETCH_DAYS * 24 * 60 * 60 * 1000:
            break

    print(f"  → Fetching {len(chunks)} weekly chunks ({FETCH_DAYS} days total)…\n")

    state = {"chunk_idx": 0, "done": False, "error": None}

    client = Client(HOST, PORT, TcpProtocol)

    APP_AUTH_RES     = ProtoOAApplicationAuthRes().payloadType
    ACCOUNT_AUTH_RES = ProtoOAAccountAuthRes().payloadType
    DEAL_LIST_RES    = ProtoOADealListRes().payloadType
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
        if all_rows:
            df = pd.DataFrame(all_rows)
            df = df.drop_duplicates(subset=["deal_id"])
            df = df.sort_values("time").reset_index(drop=True)
            df.to_csv(OUTPUT, index=False)
            closing = df[df["is_closing"] == True]
            print(f"\n  ✓ Total deals saved : {len(df)}")
            print(f"  ✓ Closed positions  : {len(closing)}")
            if not closing.empty:
                pnl = closing["pnl"].sum()
                print(f"  ✓ Total P&L         : £{pnl:.2f}")
                # Breakdown by week
                print(f"\n  Weekly P&L breakdown:")
                closing["week"] = pd.to_datetime(closing["time"]).dt.to_period("W")
                for week, grp in closing.groupby("week"):
                    wpnl = grp["pnl"].sum()
                    bar  = "█" * min(int(abs(wpnl) / 50), 20)
                    sign = "+" if wpnl >= 0 else ""
                    print(f"    {str(week):<20} {sign}£{wpnl:>8.2f}  {bar}")
        else:
            print("  ⚠  No deals found.")
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
            request_next_chunk(c)

        elif ptype == DEAL_LIST_RES:
            res   = extract(message, ProtoOADealListRes)
            deals = res.deal
            idx   = state["chunk_idx"]
            start, end = chunks[idx]
            start_dt = datetime.fromtimestamp(start/1000, tz=timezone.utc).strftime("%d %b")
            end_dt   = datetime.fromtimestamp(end/1000,   tz=timezone.utc).strftime("%d %b")
            print(f"  ✓ Chunk {idx+1}/{len(chunks)}  ({start_dt} → {end_dt})  {len(deals)} deals")

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
                                       d.executionTimestamp / 1000, tz=timezone.utc),
                    "pnl":         d.closePositionDetail.grossProfit / 100
                                   if d.HasField("closePositionDetail") else 0,
                    "commission":  d.commission / 100,
                    "is_closing":  d.HasField("closePositionDetail"),
                })

            state["chunk_idx"] += 1
            # Small delay between requests to avoid rate limiting
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
