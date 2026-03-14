# fetch_data.py
# ── Fetches deals (closed trades) from cTrader for past 7 days ─
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
        print(f"\n  ✗ Missing in .env: {', '.join(missing)}")
        print(f"    Fill in your .env file and try again.\n")
        sys.exit(1)

def fetch():
    validate_config()

    print("\n  ┌─────────────────────────────────────────┐")
    print("  │  Fetching deals from cTrader …           │")
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
        print(f"  ✗ Import error: {e}")
        sys.exit(1)

    now_ms  = int(time.time() * 1000)
    week_ms = now_ms - (7 * 24 * 60 * 60 * 1000)

    state = {"done": False, "error": None}
    client = Client(HOST, PORT, TcpProtocol)

    APP_AUTH_RES     = ProtoOAApplicationAuthRes().payloadType
    ACCOUNT_AUTH_RES = ProtoOAAccountAuthRes().payloadType
    DEAL_LIST_RES    = ProtoOADealListRes().payloadType
    ERROR_RES        = ProtoOAErrorRes().payloadType

    def extract(message, cls):
        try:    return Protobuf.extract(message, cls)
        except TypeError:
            obj = cls(); obj.ParseFromString(message.payload); return obj

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
            print("  ✓ Account authenticated")
            print(f"  → Requesting deals for past 7 days…")
            req = ProtoOADealListReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.fromTimestamp       = week_ms
            req.toTimestamp         = now_ms
            c.send(req)

        elif ptype == DEAL_LIST_RES:
            res   = extract(message, ProtoOADealListRes)
            deals = res.deal
            print(f"  ✓ Received {len(deals)} deals")

            rows = []
            for d in deals:
                # Only include filled/closed deals (dealStatus 2 = FILLED)
                if d.dealStatus != 2:
                    continue
                rows.append({
                    "deal_id":      d.dealId,
                    "position_id":  d.positionId,
                    "symbol_id":    d.symbolId,
                    "direction":    "BUY" if d.tradeSide == 1 else "SELL",
                    "volume":       d.volume / 100,
                    "fill_price":   d.executionPrice,
                    "close_price":  d.closePositionDetail.entryPrice if d.HasField("closePositionDetail") else 0,
                    "time":         datetime.fromtimestamp(d.executionTimestamp / 1000, tz=timezone.utc),
                    "pnl":          d.closePositionDetail.grossProfit / 100 if d.HasField("closePositionDetail") else 0,
                    "commission":   d.commission / 100,
                    "is_closing":   d.HasField("closePositionDetail"),
                })

            df = pd.DataFrame(rows)

            if df.empty:
                print("  ⚠  No filled deals found in the past 7 days.")
                print("     This could mean:")
                print("     - No trades were made this week")
                print("     - Try extending the date range in fetch_data.py")
            else:
                df.to_csv(OUTPUT, index=False)
                print(f"  ✓ Saved {len(df)} deals → {OUTPUT}")
                # Print a quick summary
                closing = df[df["is_closing"]]
                if not closing.empty:
                    total_pnl = closing["pnl"].sum()
                    print(f"  ✓ Closed positions: {len(closing)}")
                    print(f"  ✓ Total P&L: £{total_pnl:.2f}")

            state["done"] = True
            try: reactor.stop()
            except: pass

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
