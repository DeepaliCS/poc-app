# fetch_data.py
# ── Fetches closed trades from cTrader for the past 7 days ────
# Saves to data/trades.csv — read by app.py
# Run this before launching the dashboard, or it runs automatically
# via run.sh

import os, sys, time, warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Load .env from project root
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

CLIENT_ID     = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
ACCESS_TOKEN  = os.getenv("CTRADER_ACCESS_TOKEN")
ACCOUNT_ID    = int(os.getenv("CTRADER_ACCOUNT_ID", "0"))
HOST          = os.getenv("CTRADER_HOST", "live.ctraderapi.com")
PORT          = int(os.getenv("CTRADER_PORT", "5035"))
SYMBOL        = os.getenv("CTRADER_SYMBOL", "XAUUSD")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT = DATA_DIR / "trades.csv"

def validate_config():
    missing = []
    if not CLIENT_ID or CLIENT_ID == "your_client_id_here":     missing.append("CTRADER_CLIENT_ID")
    if not CLIENT_SECRET or CLIENT_SECRET == "your_client_secret_here": missing.append("CTRADER_CLIENT_SECRET")
    if not ACCESS_TOKEN or ACCESS_TOKEN == "your_access_token_here":  missing.append("CTRADER_ACCESS_TOKEN")
    if ACCOUNT_ID == 0:                                          missing.append("CTRADER_ACCOUNT_ID")
    if missing:
        print(f"\n  ✗ Missing in .env: {', '.join(missing)}")
        print(f"    Copy .env.example → .env and fill in your values\n")
        sys.exit(1)

def fetch():
    validate_config()

    print("\n  ┌─────────────────────────────────────────┐")
    print("  │  Fetching trades from cTrader …          │")
    print("  └─────────────────────────────────────────┘\n")

    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
            ProtoOAAccountAuthReq,     ProtoOAAccountAuthRes,
            ProtoOAGetClosedTradesReq, ProtoOAGetClosedTradesRes,
            ProtoOAErrorRes,
        )
        from twisted.internet import reactor
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        sys.exit(1)

    now_ms   = int(time.time() * 1000)
    week_ms  = now_ms - (7 * 24 * 60 * 60 * 1000)

    state = {"done": False, "error": None}

    client = Client(HOST, PORT, TcpProtocol)

    APP_AUTH_RES     = ProtoOAApplicationAuthRes().payloadType
    ACCOUNT_AUTH_RES = ProtoOAAccountAuthRes().payloadType
    TRADES_RES       = ProtoOAGetClosedTradesRes().payloadType
    ERROR_RES        = ProtoOAErrorRes().payloadType

    def extract(message, cls):
        try:
            return Protobuf.extract(message, cls)
        except TypeError:
            obj = cls(); obj.ParseFromString(message.payload); return obj

    def on_connected(c):
        print("  ✓ Connected")
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
            print(f"  → Fetching closed trades for past 7 days …")
            req = ProtoOAGetClosedTradesReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.fromTimestamp = week_ms
            req.toTimestamp   = now_ms
            c.send(req)

        elif ptype == TRADES_RES:
            res    = extract(message, ProtoOAGetClosedTradesRes)
            trades = res.closedTrade
            print(f"  ✓ Received {len(trades)} closed trades")
            rows = []
            for tr in trades:
                pos = tr.position
                rows.append({
                    "trade_id":    tr.closingDealId,
                    "symbol_id":   pos.tradeData.symbolId,
                    "direction":   "BUY" if pos.tradeData.tradeSide == 1 else "SELL",
                    "volume":      pos.tradeData.volume / 100,
                    "open_price":  pos.price,
                    "close_price": tr.closePrice,
                    "open_time":   datetime.fromtimestamp(
                                       pos.tradeData.openTimestamp / 1000,
                                       tz=timezone.utc),
                    "close_time":  datetime.fromtimestamp(
                                       tr.closeTimestamp / 1000,
                                       tz=timezone.utc),
                    "pnl":         tr.closedBalance / 100,
                    "commission":  tr.commission / 100 if hasattr(tr, "commission") else 0,
                })
            df = pd.DataFrame(rows)
            df.to_csv(OUTPUT, index=False)
            print(f"  ✓ Saved → {OUTPUT}")
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

if __name__ == "__main__":
    fetch()
