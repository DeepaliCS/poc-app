# tests/test_api_connection.py
# Tests that we can connect and authenticate with the cTrader API
#
# Run: pytest tests/test_api_connection.py -v

import os
import sys
import threading
import pytest
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent

pytestmark = pytest.mark.core
load_dotenv(BASE_DIR / ".env")


@pytest.mark.smoke
def test_env_variables_exist():
    """All required credentials must be present in .env"""
    assert os.getenv("CTRADER_CLIENT_ID"),     "CTRADER_CLIENT_ID missing from .env"
    assert os.getenv("CTRADER_CLIENT_SECRET"), "CTRADER_CLIENT_SECRET missing from .env"
    assert os.getenv("CTRADER_ACCESS_TOKEN"),  "CTRADER_ACCESS_TOKEN missing from .env"
    assert os.getenv("CTRADER_ACCOUNT_ID"),    "CTRADER_ACCOUNT_ID missing from .env"
    assert os.getenv("CTRADER_HOST"),          "CTRADER_HOST missing from .env"
    assert os.getenv("CTRADER_PORT"),          "CTRADER_PORT missing from .env"


@pytest.mark.smoke
def test_env_values_not_placeholder():
    """Credentials must not still be the placeholder template values"""
    client_id = os.getenv("CTRADER_CLIENT_ID", "")
    secret    = os.getenv("CTRADER_CLIENT_SECRET", "")
    token     = os.getenv("CTRADER_ACCESS_TOKEN", "")
    account   = os.getenv("CTRADER_ACCOUNT_ID", "0")

    assert "your_" not in client_id.lower(), "CTRADER_CLIENT_ID is still a placeholder"
    assert "your_" not in secret.lower(),    "CTRADER_CLIENT_SECRET is still a placeholder"
    assert "your_" not in token.lower(),     "CTRADER_ACCESS_TOKEN is still a placeholder"
    assert int(account) != 0,               "CTRADER_ACCOUNT_ID is still 0"


@pytest.mark.smoke
def test_ctrader_api_importable():
    """The ctrader-open-api package must be installed"""
    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
    except ImportError:
        pytest.fail("ctrader-open-api not installed. Run: pip install ctrader-open-api")


@pytest.mark.smoke
def test_twisted_importable():
    """Twisted must be installed"""
    try:
        from twisted.internet import reactor
    except ImportError:
        pytest.fail("twisted not installed. Run: pip install twisted")


@pytest.mark.live
@pytest.mark.slow
def test_api_app_authentication():
    """
    Actually connects to cTrader and authenticates the app.
    This is a live network test — requires internet and valid credentials.
    Times out after 15 seconds if no response.
    """
    try:
        from ctrader_open_api import Client, Protobuf, TcpProtocol
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq,
            ProtoOAApplicationAuthRes,
            ProtoOAErrorRes,
        )
        from twisted.internet import reactor
    except ImportError as e:
        pytest.skip(f"Dependencies not available: {e}")

    CLIENT_ID     = os.getenv("CTRADER_CLIENT_ID")
    CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")
    HOST          = os.getenv("CTRADER_HOST", "live.ctraderapi.com")
    PORT          = int(os.getenv("CTRADER_PORT", "5035"))

    result     = {"authenticated": False, "error": None}
    done_event = threading.Event()
    client     = Client(HOST, PORT, TcpProtocol)

    def extract(message, cls):
        try:    return Protobuf.extract(message, cls)
        except TypeError:
            obj = cls(); obj.ParseFromString(message.payload); return obj

    def on_connected(c):
        req = ProtoOAApplicationAuthReq()
        req.clientId     = CLIENT_ID
        req.clientSecret = CLIENT_SECRET
        c.send(req)

    def on_disconnected(c, reason):
        done_event.set()

    def on_message(c, message):
        ptype = message.payloadType
        if ptype == ProtoOAApplicationAuthRes().payloadType:
            result["authenticated"] = True
            done_event.set()
            try: client.stopService()
            except: pass
        elif ptype == ProtoOAErrorRes().payloadType:
            err = extract(message, ProtoOAErrorRes)
            result["error"] = f"{err.errorCode}: {err.description}"
            done_event.set()
            try: client.stopService()
            except: pass

    client.setConnectedCallback(on_connected)
    client.setDisconnectedCallback(on_disconnected)
    client.setMessageReceivedCallback(on_message)

    if not reactor.running:
        def run():
            reactor.run(installSignalHandlers=False)
        t = threading.Thread(target=run, daemon=True)
        t.start()

    reactor.callFromThread(client.startService)
    done_event.wait(timeout=15)

    if result["error"]:
        pytest.fail(f"cTrader API error: {result['error']}")

    assert result["authenticated"], "App authentication did not complete within 15 seconds"
