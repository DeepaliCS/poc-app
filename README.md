# 📊 Trading Journal

A personal trading analytics dashboard built for **cTrader** accounts. Connects directly to the cTrader API to pull your live trade history and visualise it across four analytical views — overview, daily review, journal, and scenario analysis.

Built with Python, Plotly Dash, and the cTrader Open API.

---

## What It Does

| Page | Description |
|------|-------------|
| **📊 Overview** | Cumulative P&L curve, timeframe selector (1W → All), stats cards, trade bar chart, buy/sell split, recent trade log |
| **📅 Daily View** | Pick any date — one candlestick chart per symbol traded, with entry and exit markers overlaid on the candles and session boxes (Tokyo, London, New York, Sydney) |
| **📋 Journal** | Daily P&L table with sessions traded, instruments, max drawdown, exposure drawdown, win rate, commission. Downloadable as CSV |
| **🔍 Scenarios** | Pattern-based trade clustering — automatically groups bursts of entries and exits into trading scenarios (e.g. a dip-buying sequence). Market chart overlay with scenario colour bands. Downloadable as CSV |

---

## Requirements

- **Python 3.11** via [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- **cTrader account** with API access (client ID, secret, access token)
- **Linux / macOS** (tested on Ubuntu 24)

---

## Setup

### 1. Clone the repo

```bash
git clone git@github.com:DeepaliCS/poc-app.git
cd poc-app
```

### 2. Create the conda environment

```bash
conda create -n poc_app python=3.11 -y
conda activate poc_app
pip install -r requirements.txt
```

### 3. Configure your credentials

Copy the example env file and fill in your cTrader details:

```bash
cp .env.example .env
```

Edit `.env`:

```env
CTRADER_CLIENT_ID=your_client_id
CTRADER_CLIENT_SECRET=your_client_secret
CTRADER_ACCESS_TOKEN=your_access_token
CTRADER_ACCOUNT_ID=your_account_id
CTRADER_HOST=live.ctraderapi.com
CTRADER_PORT=5035
CTRADER_SYMBOL=XAUUSD
```

> **Where to find these:**  
> Log into [cTrader Open API](https://openapi.ctrader.com/) → create an app → copy client ID and secret.  
> Get your access token from the OAuth flow or your broker's API portal.  
> Your account ID is the number shown in cTrader under your account name.

---

## Running the App

```bash
cd poc-app
./run.sh
```

This will:
1. Activate the `poc_app` conda environment
2. Fetch your latest trade data from cTrader (incremental — only fetches new data if cache exists)
3. Fetch symbol names
4. Launch the dashboard at **http://127.0.0.1:8050**

Open your browser and go to `http://127.0.0.1:8050`.

---

## Data Fetching — How It Works

The app uses **incremental fetching with local caching** so it only downloads what it needs:

| Situation | What happens |
|-----------|-------------|
| First run (no cache) | Fetches full 120 days of history (~18 API chunks) |
| Cache < 1 hour old | Skips fetch entirely — uses disk cache |
| Cache > 1 hour old | Fetches only from last saved timestamp to now (1–2 chunks) |

Trade data is saved to `data/trades.csv`. This file is gitignored — it never gets committed.

---

## File Structure

```
poc-app/
├── app.py               ← Main Dash app (all pages in one file)
├── fetch_data.py        ← Incremental trade data fetcher
├── fetch_symbols.py     ← Fetches symbol ID → name map
├── run.sh               ← One-click launcher
├── save.sh              ← Git commit + push to GitHub
├── undo.sh              ← Revert to last saved version
├── history.sh           ← Show version history
├── requirements.txt     ← Python dependencies
├── .env.example         ← Credential template (safe to commit)
├── .env                 ← YOUR credentials (gitignored — never commit)
└── data/
    ├── trades.csv       ← Auto-generated trade cache (gitignored)
    └── symbols.json     ← Auto-generated symbol map (gitignored)
```

---

## Helper Scripts

```bash
# Save changes to GitHub
./save.sh "describe what you changed"

# Undo all uncommitted changes (revert to last save)
./undo.sh

# View version history
./history.sh
```

---

## Updating the App

When a new `app.py` is provided:

```bash
cp ~/Downloads/app.py ~/Downloads/poc-app/app.py
rm ~/Downloads/app.py
cd ~/Downloads/poc-app
./run.sh
```

---

## Dependencies

```
dash>=2.16.0
plotly>=5.20.0
pandas>=2.0.0
python-dotenv>=1.0.0
ctrader-open-api>=0.9.0
twisted>=24.3.0
service-identity>=21.1.0
```

---

## Technical Notes

- **cTrader API:** Uses `ctrader-open-api` with Twisted. The Twisted reactor runs in a persistent background thread — it starts once and stays alive for the app's lifetime. All API calls use `reactor.callFromThread()` + `threading.Event` for thread-safe communication from Dash callbacks.
- **Price normalisation:** cTrader returns raw integer prices. The app auto-detects the correct decimal divisor per symbol by comparing raw bar values to known fill prices from the trade history.
- **Scenario detection:** Trades are grouped into scenarios by clustering exit times — a gap of more than 10 minutes between consecutive exits signals the start of a new scenario.
- **Session boxes:** Tokyo (00:00–09:00 UTC), London (08:00–17:00 UTC), New York (13:00–22:00 UTC), Sydney (21:00–06:00 UTC).

---

## Security

- **Never commit `.env`** — it contains your live trading account credentials.
- The `.gitignore` blocks `.env` and all files in `data/`.
- `ACCESS_TOKEN` has read-only scope — it cannot place or modify trades.

---

## Licence

Private — not for redistribution.

---

*Built by Deepali · March 2026*
