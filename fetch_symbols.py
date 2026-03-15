# fetch_symbols.py
# Fetches symbol names from cTrader and saves to data/symbols.json
import os, sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
from dotenv import load_dotenv
import json

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
OUTPUT = DATA_DIR / "symbols.json"

def fetch():
    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
            ProtoOAAccountAuthReq,     ProtoOAAccountAuthRes,
            ProtoOASymbolsListReq,     ProtoOASymbolsListRes,
            ProtoOAErrorRes,
        )
        from twisted.internet import reactor
    except ImportError as e:
        print(f"  ✗ {e}"); sys.exit(1)

    state = {"done": False}
    client = Client(HOST, PORT, TcpProtocol)

    def extract(message, cls):
        try:    return Protobuf.extract(message, cls)
        except TypeError:
            obj = cls(); obj.ParseFromString(message.payload); return obj

    def on_connected(c):
        req = ProtoOAApplicationAuthReq()
        req.clientId = CLIENT_ID; req.clientSecret = CLIENT_SECRET
        c.send(req)

    def on_disconnected(c, reason):
        if not state["done"]:
            print(f"  ✗ Disconnected: {reason}")
        try: reactor.stop()
        except: pass

    def on_message(c, message):
        ptype = message.payloadType
        if ptype == ProtoOAApplicationAuthRes().payloadType:
            req = ProtoOAAccountAuthReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.accessToken = ACCESS_TOKEN
            c.send(req)
        elif ptype == ProtoOAAccountAuthRes().payloadType:
            req = ProtoOASymbolsListReq()
            req.ctidTraderAccountId = ACCOUNT_ID
            req.includeArchivedSymbols = False
            c.send(req)
        elif ptype == ProtoOASymbolsListRes().payloadType:
            res = extract(message, ProtoOASymbolsListRes)
            symbols = {str(s.symbolId): s.symbolName for s in res.symbol}
            with open(OUTPUT, "w") as f:
                json.dump(symbols, f)
            print(f"  ✓ Saved {len(symbols)} symbols → {OUTPUT}")
            state["done"] = True
            try: reactor.stop()
            except: pass
        elif ptype == ProtoOAErrorRes().payloadType:
            err = extract(message, ProtoOAErrorRes)
            print(f"  ✗ {err.errorCode}: {err.description}")
            try: reactor.stop()
            except: pass

    client.setConnectedCallback(on_connected)
    client.setDisconnectedCallback(on_disconnected)
    client.setMessageReceivedCallback(on_message)
    client.startService()
    reactor.run()

if __name__ == "__main__":
    fetch()
