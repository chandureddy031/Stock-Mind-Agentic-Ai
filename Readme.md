# 🧠 StockMind — Agentic Stock Intelligence System

> **5 AI agents. One question. Complete analysis.**  
> From live price data to a full trading strategy — intraday to 10-year investor outlook.

---

## 📋 Table of Contents

- [What is StockMind?](#what-is-stockmind)
- [Project Structure](#project-structure)
- [How Each File Works](#how-each-file-works)
- [The 5 Agents — Explained](#the-5-agents--explained)
- [Agent Graph Flow](#agent-graph-flow)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [How to Use It](#how-to-use-it)
- [API Keys Used](#api-keys-used)
- [Troubleshooting](#troubleshooting)

---

## What is StockMind?

StockMind is a **multi-agent AI system** built with Python + FastAPI that analyzes any stock or cryptocurrency on demand. You type a question like *"what about NVIDIA"* or even *"tell me about bitcoin"* — and 5 specialized AI agents run in sequence to give you:

- Live price snapshot with metrics
- Today's and yesterday's news with sentiment
- Twitter/X social sentiment from the last 24 hours
- Full fundamental analysis (past 10 years, past 5 years, next 5 year outlook)
- A complete trading strategy for every trader type — intraday, swing, short-term, long-term, and investor

The system is built as an **agentic graph** — each agent passes its output to the next, building richer context at every step. The final agent sees everything all previous agents found and synthesizes a verdict.

---

## Project Structure

```
stock-agent/
│
├── .env                   ← API keys (never commit this)
├── tools.py               ← All external API calls (Groq, yfinance, Yahoo RSS, Twitter)
├── agents.py              ← All 5 agents + the graph orchestrator
├── main.py                ← FastAPI server + routing
│
└── templates/
    └── index.html         ← Full UI (HTML + CSS + Chart.js, no JS framework)
```

**That's it. 4 Python files + 1 HTML template. No JavaScript framework. No database. No complex config.**

---

## How Each File Works

### `.env` — Configuration

Stores all your secret API keys. Loaded at startup. Never commit this file to Git.

```env
GROQ_API_KEY=your_groq_key_here
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
```

---

### `tools.py` — The Toolbox

This is the **foundation layer**. All 5 agents call functions from this file. It handles every external API call and keeps agents clean and simple.

| Function | What it does |
|---|---|
| `llm(system, user)` | Sends a prompt to Groq's LLaMA 3.3 70B model and returns the response |
| `extract_ticker(raw_input)` | Converts natural language ("tell me about Apple") → ticker symbol ("AAPL") |
| `validate_ticker(ticker)` | Confirms the ticker actually exists on Yahoo Finance; auto-corrects if not |
| `get_price_data(ticker)` | Pulls live price, OHLCV, fundamentals, and 6mo/1y/5y/10y history via yfinance |
| `get_news(ticker, company)` | Fetches latest news via Yahoo Finance RSS feed (free, no key needed) |
| `get_tweets(query)` | Searches Twitter/X for the last 24 hours of tweets about the stock |

**Key design decision:** `tools.py` also contains a `KNOWN_TICKERS` dictionary that maps common names to correct Yahoo Finance symbols without needing an LLM call:

```
"NVIDIA"  → "NVDA"
"BITCOIN" → "BTC-USD"
"NIFTY"   → "^NSEI"
"GOLD"    → "GC=F"
```

This makes lookups instant for common stocks and avoids wasting LLM tokens on simple name resolution.

---

### `agents.py` — The 5 Agents + Graph

This is the **brain** of the system. Each function is one agent. The `run_graph()` function at the bottom is the orchestrator that calls them in order.

Agents are designed to be:
- **Single-responsibility** — each agent does exactly one thing
- **Context-building** — each agent's output feeds into the next
- **Reusable** — you can call any agent individually if you want

---

### `main.py` — The Web Server

FastAPI application with two routes:

| Route | Method | What happens |
|---|---|---|
| `/` | `GET` | Renders the homepage with an empty search form |
| `/analyze` | `POST` | Receives the ticker input, runs `run_graph()`, renders results |

Uses **Jinja2 templating** to pass the Python result dictionary directly into the HTML template. No JSON API, no JavaScript fetch — the server renders the full page with results embedded.

---

### `templates/index.html` — The UI

A single-file HTML + CSS + minimal JS interface. No React, no Vue, no Tailwind CDN.

Features:
- **Dark terminal aesthetic** with grid background texture
- **Agent pipeline visualization** — icons light up green after analysis completes
- **Chart.js charts** — 6-month and 5-year price charts rendered from yfinance data
- **Metrics strip** — 12 key financial metrics in a compact grid
- **Responsive** — works on mobile
- **Example chips** — click NVDA, TSLA, BTC-USD, etc. to auto-fill the input

The template receives a `result` dictionary from FastAPI and renders everything with Jinja2 template syntax (`{{ result.price.price }}`, `{% for a in result.news.articles %}`).

---

## The 5 Agents — Explained

### Agent 1 — Price Agent 📈

**What it does:**  
Fetches comprehensive price data from Yahoo Finance and writes a human-readable snapshot summary.

**Data it collects:**
- Current price, previous close, open, day high/low
- Volume, market cap, P/E ratio, EPS
- 52-week high and low, beta, dividend yield
- Sector and industry classification
- Historical price series: 6 months (daily), 1 year (weekly), 5 years (monthly), 10 years (monthly)

**LLM task:**  
Write a concise 3–4 line trader-dashboard summary of the price situation.

**Output passed forward:** Everything above, plus the text summary. The historical data is used by Agent 4 for the 10-year analysis. The price and fundamentals are used by Agent 5 for strategy levels.

---

### Agent 2 — News Agent 📰

**What it does:**  
Fetches the latest headlines from Yahoo Finance's RSS feed (completely free, no API key required) and performs a detailed news sentiment analysis.

**Data it collects:**  
Up to 15 recent articles including title, description, publication date, and link. Filters to the most relevant 12 for analysis.

**LLM task:**  
Analyze the news and return:
1. Overall sentiment score from -10 (very bearish) to +10 (very bullish)
2. Key themes appearing across multiple articles
3. Any macro or geopolitical risks mentioned — wars, sanctions, supply chain disruptions, rate decisions
4. How this news is likely to affect the stock in the next 1–5 trading days

**Why this matters:**  
News drives short-term price movement. A stock with strong fundamentals can still drop 15% on a bad earnings headline. Agent 2 captures this.

**Output passed forward:** The full sentiment analysis text is passed to Agent 5 as context for the trading strategy.

---

### Agent 3 — Twitter / X Sentiment Agent 🐦

**What it does:**  
Searches Twitter/X for the past 24 hours of tweets about the stock using the Twitter v2 API, then analyzes the crowd sentiment.

**Data it collects:**  
Up to 30 recent tweets (excluding retweets, English only) with like count, retweet count, and timestamp. Sends the top 20 by engagement to the LLM.

**LLM task:**  
Analyze the Twitter sentiment and return:
1. Social sentiment score from -10 to +10
2. What the dominant retail trader opinion is right now
3. Any viral narratives or FUD (Fear, Uncertainty, Doubt) spreading
4. Any signals from influential accounts
5. One-line conclusion of what the crowd thinks

**Why this matters:**  
Retail sentiment on social media is a leading indicator — especially for high-beta and meme-adjacent stocks. It captures what institutional data misses: the crowd's emotional state right now.

**Output passed forward:** The full Twitter analysis text is passed to Agent 5.

---

### Agent 4 — Fundamental Analysis Agent 📊

**What it does:**  
Performs a comprehensive fundamental and historical analysis covering the past 10 years, past 5 years, and a forward 5-year outlook — taking the current global macro environment into account.

**Data it uses:**  
- All fundamental metrics from Agent 1 (P/E, EPS, Market Cap, Beta, Dividend)
- Last 12 data points from the 5-year monthly history
- Last 12 data points from the 10-year monthly history
- Hardcoded global context: ongoing wars (Russia-Ukraine, Middle East), elevated interest rates, inflation, supply chain stress

**LLM task:**  
Produce a complete analysis with 5 sections:
1. **Past 10 years** — long-term trend, key turning points, estimated CAGR
2. **Past 5 years** — recent growth pattern, COVID-19 impact, recovery shape
3. **Valuation** — is the stock overvalued, undervalued, or fairly valued right now?
4. **Risks** — fundamental risks, macro risks, geopolitical risks, sector-specific risks
5. **Next 5-year outlook** — projected trajectory factoring in current war and macro environment

**Why this matters:**  
This is the analysis even professional traders rarely do fully. Most traders look at 1-year charts. Agent 4 forces a 10-year lens and makes the LLM reason about decade-long patterns.

**Output passed forward:** The full analysis text is passed to Agent 5.

---

### Agent 5 — Strategy & Verdict Agent 🎯

**What it does:**  
This is the synthesis agent. It receives outputs from all 4 previous agents and produces a complete, actionable trading strategy for every type of trader — plus a final buy/hold/wait verdict.

**Data it uses:**  
- Current price, 52-week range, Beta, P/E from Agent 1
- News sentiment analysis from Agent 2
- Twitter sentiment analysis from Agent 3
- Full fundamental analysis from Agent 4
- Hardcoded global macro context

**LLM task:**  
Produce trading strategies for 5 trader types:

| Trader Type | Timeframe | What it includes |
|---|---|---|
| 🏃 Intraday | Same day | Entry zone, exit target, stop loss, risk level |
| 🌊 Swing | 1–4 weeks | Setup type, entry, price targets, invalidation level |
| 📅 Short Term | 1–3 months | Key catalyst to watch, price targets |
| 📈 Long Term | 1–5 years | Accumulation strategy, DCA entry levels |
| 🏦 Investor | 5–10 years | Is this a compounder? Buy or avoid? |

Then produce a **Final Verdict**:
- Overall score out of 10
- Is it worth buying now? (Yes / No / Wait) with a clear reason
- Best entry price if buying
- The single biggest risk that could destroy this trade

**Why this matters:**  
Most analysis tools give you data. Agent 5 tells you what to *do* with it.

---

## Agent Graph Flow

```
User Input ("what about NVIDIA")
        │
        ▼
  extract_ticker()  ──→  "NVDA"
  validate_ticker() ──→  confirmed
        │
        ▼
  ┌─────────────┐
  │   AGENT 1   │  ──→  price_data (price, metrics, history)
  │  Price Data │
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │   AGENT 2   │  ──→  news_result (articles + sentiment analysis)
  │    News     │
  └─────────────┘
        │
        ▼
  ┌─────────────┐
  │   AGENT 3   │  ──→  twitter_result (tweets + sentiment analysis)
  │   Twitter   │
  └─────────────┘
        │
        ▼
  ┌─────────────────────┐
  │      AGENT 4        │  uses: price_data
  │  Fundamentals +     │  ──→  fund_result (10Y/5Y/future analysis)
  │  Historical         │
  └─────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────┐
  │                    AGENT 5                      │
  │  Strategy + Verdict                             │
  │  uses: price_data + news + twitter + fundamentals│
  │  ──→  strategy_result (all trader types + verdict)│
  └─────────────────────────────────────────────────┘
        │
        ▼
  FastAPI renders index.html with all results
  User sees full dashboard
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip
- Internet connection (for live data)

### Step 1 — Clone or create the project folder

```bash
mkdir stock-agent
cd stock-agent
```

### Step 2 — Create the files

Create these files in the folder:
```
.env
tools.py
agents.py
main.py
templates/
    index.html
```

### Step 3 — Install dependencies

```bash
pip install fastapi uvicorn groq yfinance requests python-dotenv jinja2 python-multipart httpx==0.27.2
```

If you get a `proxies` TypeError with httpx, run:
```bash
pip install httpx==0.27.2 groq --force-reinstall
```

---

## Configuration

Open `.env` and set your keys:

```env
GROQ_API_KEY=gsk_your_key_here
TWITTER_BEARER_TOKEN=your_bearer_token_here
```

### Getting a Groq API Key (Free)

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up for free
3. Go to API Keys → Create API Key
4. Copy and paste into `.env`

Groq is completely free with generous rate limits. It runs LLaMA 3.3 70B at very high speed.

### Getting a Twitter Bearer Token

1. Go to [https://developer.twitter.com](https://developer.twitter.com)
2. Create a project and app
3. Go to Keys and Tokens → Bearer Token
4. Copy and paste into `.env`

The Bearer Token is the only one needed for read-only tweet search. The consumer key, consumer secret, access token, and access secret are only needed for posting tweets — not required here.

---

## Running the App

```bash
uvicorn main:app --reload --port 8000
```

Then open your browser:

```
http://localhost:8000
```

**Flags explained:**
- `--reload` — auto-restarts when you edit any Python file (remove this in production)
- `--port 8000` — runs on port 8000 (change if port is busy)

---

## How to Use It

1. Open `http://localhost:8000`
2. Type a stock ticker or company name in the search box:
   - `AAPL` — Apple
   - `NVDA` — NVIDIA
   - `BTC-USD` — Bitcoin
   - `RELIANCE.NS` — Reliance Industries (NSE)
   - `^NSEI` — Nifty 50 Index
   - Or just type: `"tell me about Tesla"` — the system resolves it automatically
3. Click **Analyze**
4. Wait 30–60 seconds while all 5 agents run
5. Scroll through the full analysis dashboard

### Supported Input Formats

| You type | System resolves to |
|---|---|
| `NVDA` | `NVDA` (direct) |
| `NVIDIA` | `NVDA` (known tickers map) |
| `bitcoin` | `BTC-USD` (known tickers map) |
| `"what about reliance"` | `RELIANCE.NS` (LLM extraction) |
| `Tesla stock analysis` | `TSLA` (LLM extraction) |
| `Nifty 50` | `^NSEI` (known tickers map) |

---

## API Keys Used

| Service | Used for | Cost | Required |
|---|---|---|---|
| **Groq** | LLaMA 3.3 70B LLM — all 5 agents | Free | ✅ Yes |
| **yfinance** | Live price data + historical data | Free | ✅ Built-in |
| **Yahoo Finance RSS** | News headlines | Free | ✅ Built-in |
| **Twitter v2 API** | Tweet search last 24hr | Free tier | ⚠️ Optional |

Twitter is optional — if the Bearer Token is invalid or rate-limited, Agent 3 still runs and reports the error gracefully. Agents 1, 2, 4, and 5 are completely unaffected.

---

## Troubleshooting

### `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`
```bash
pip install httpx==0.27.2 groq --force-reinstall
```

### `404 Not Found` for a stock ticker
The ticker symbol is wrong. Use Yahoo Finance format:
- Indian stocks: `RELIANCE.NS`, `TCS.NS`, `INFY.NS`
- Crypto: `BTC-USD`, `ETH-USD`
- Indices: `^NSEI`, `^BSESN`, `^GSPC`
- US stocks: `AAPL`, `MSFT`, `TSLA`

### `429 Rate Limit` from Groq
You've hit the free tier limit for the minute. Wait 60 seconds and try again. Groq resets limits per minute.

### `401 Unauthorized` from Twitter
Your Bearer Token is incorrect or expired. Generate a new one from [developer.twitter.com](https://developer.twitter.com). The app will still work — Twitter agent will show an error message but the other 4 agents complete normally.

### `.env` not loading
Make sure `.env` is in the **same folder** as `main.py`. Check for hidden spaces or quotes around values:
```env
# CORRECT
GROQ_API_KEY=gsk_abc123

# WRONG — do not add quotes
GROQ_API_KEY="gsk_abc123"
```

Test your env loading:
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GROQ_API_KEY'))"
```

### Analysis takes too long
Each LLM call takes 3–8 seconds. With 5 agents making 6 total LLM calls, expect 30–60 seconds total. This is normal.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| Templating | Jinja2 |
| LLM | Groq — LLaMA 3.3 70B Versatile |
| Stock data | yfinance |
| News | Yahoo Finance RSS |
| Social data | Twitter v2 API |
| Charts | Chart.js (CDN) |
| Fonts | Instrument Serif, DM Mono, Manrope |
| Styling | Vanilla CSS |

---

## Important Disclaimer

> **This tool is for educational and research purposes only.**  
> Nothing produced by StockMind constitutes financial advice.  
> Do not make investment decisions based solely on AI-generated analysis.  
> Always do your own research and consult a qualified financial advisor.

---

*Built with FastAPI · Groq · yfinance · Twitter API*