import os, requests, datetime, yfinance as yf
import xml.etree.ElementTree as ET
from groq import Groq

# ── Hardcoded keys (change before pushing) ────────────────────────────────────
GROQ_API_KEY   = ""
TWITTER_BEARER = ""

GROQ_CLIENT = Groq(api_key=GROQ_API_KEY)

# ── Common name → ticker map (instant, no LLM needed) ─────────────────────────
KNOWN_TICKERS = {
    "NVIDIA": "NVDA", "APPLE": "AAPL", "MICROSOFT": "MSFT", "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL", "AMAZON": "AMZN", "TESLA": "TSLA", "META": "META",
    "FACEBOOK": "META", "NETFLIX": "NFLX", "BITCOIN": "BTC-USD", "BTC": "BTC-USD",
    "ETHEREUM": "ETH-USD", "ETH": "ETH-USD", "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS", "INFOSYS": "INFY", "NIFTY": "^NSEI", "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN", "GOLD": "GC=F", "SILVER": "SI=F", "CRUDE": "CL=F",
    "OIL": "CL=F", "SAMSUNG": "005930.KS", "SONY": "SONY", "AMD": "AMD",
    "INTEL": "INTC", "QUALCOMM": "QCOM", "PALANTIR": "PLTR", "UBER": "UBER",
    "AIRBNB": "ABNB", "SNOWFLAKE": "SNOW", "COINBASE": "COIN",
}

# ── LLM call ───────────────────────────────────────────────────────────────────
def llm(system: str, user: str) -> str:
    resp = GROQ_CLIENT.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
        temperature=0.3,
        max_tokens=2048,
    )
    return resp.choices[0].message.content.strip()

# ── Extract ticker ─────────────────────────────────────────────────────────────
def extract_ticker(raw_input: str) -> str:
    raw = raw_input.strip().upper()

    # 1. Direct known map
    if raw in KNOWN_TICKERS:
        return KNOWN_TICKERS[raw]

    # 2. Already a valid short ticker (no spaces, ≤10 chars)
    if len(raw.split()) == 1 and len(raw) <= 10:
        return raw

    # 3. Check each word against known map
    for word in raw.split():
        if word in KNOWN_TICKERS:
            return KNOWN_TICKERS[word]

    # 4. LLM fallback — strict prompt
    result = llm(
        system="""You are a stock ticker extractor.
Return ONLY the exact Yahoo Finance ticker symbol — nothing else.
No company names, no explanations, no punctuation, no markdown.
Examples: AAPL, NVDA, TSLA, BTC-USD, RELIANCE.NS, ^NSEI, ETH-USD""",
        user=f"""What is the Yahoo Finance ticker symbol for: "{raw_input}"?
Reply with ONLY the ticker. Single word. No explanation."""
    )
    # Clean LLM output
    ticker = result.strip().upper().split()[0]
    ticker = ticker.replace('"','').replace("'","").replace(".",".",1).strip(".")
    return ticker

# ── Validate ticker actually exists ───────────────────────────────────────────
def validate_ticker(ticker: str) -> str:
    """Try ticker as-is, then check KNOWN_TICKERS, then ask LLM to correct."""
    t = yf.Ticker(ticker)
    info = t.info
    if info and info.get("regularMarketPrice") or info.get("currentPrice"):
        return ticker
    # Try fast lookup
    if ticker in KNOWN_TICKERS:
        return KNOWN_TICKERS[ticker]
    # Ask LLM to correct
    corrected = llm(
        system="You are a Yahoo Finance ticker corrector. Return ONLY the correct ticker symbol.",
        user=f'The ticker "{ticker}" returned no data on Yahoo Finance. What is the correct Yahoo Finance ticker? Reply with only the ticker symbol.'
    )
    return corrected.strip().upper().split()[0]

# ── Stock price + history ──────────────────────────────────────────────────────
def get_price_data(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.info
    hist_5y  = t.history(period="5y",  interval="1mo")
    hist_10y = t.history(period="10y", interval="1mo")
    hist_1y  = t.history(period="1y",  interval="1wk")
    hist_6m  = t.history(period="6mo", interval="1d")

    def series(df):
        return [{"date": str(i.date()), "close": round(float(r["Close"]), 2)}
                for i, r in df.iterrows()]

    return {
        "ticker":     ticker.upper(),
        "name":       info.get("longName", ticker),
        "price":      info.get("currentPrice") or info.get("regularMarketPrice"),
        "prev_close": info.get("previousClose"),
        "open":       info.get("open"),
        "day_high":   info.get("dayHigh"),
        "day_low":    info.get("dayLow"),
        "volume":     info.get("volume"),
        "market_cap": info.get("marketCap"),
        "pe_ratio":   info.get("trailingPE"),
        "eps":        info.get("trailingEps"),
        "52w_high":   info.get("fiftyTwoWeekHigh"),
        "52w_low":    info.get("fiftyTwoWeekLow"),
        "beta":       info.get("beta"),
        "dividend":   info.get("dividendYield"),
        "sector":     info.get("sector", "N/A"),
        "industry":   info.get("industry", "N/A"),
        "hist_6m":    series(hist_6m),
        "hist_1y":    series(hist_1y),
        "hist_5y":    series(hist_5y),
        "hist_10y":   series(hist_10y),
    }

# ── News via Yahoo Finance RSS ─────────────────────────────────────────────────
def get_news(ticker: str, company: str) -> list[dict]:
    rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    articles = []
    try:
        r = requests.get(rss_url, timeout=10)
        root = ET.fromstring(r.text)
        for item in root.findall(".//item")[:15]:
            articles.append({
                "title":       item.findtext("title", ""),
                "description": item.findtext("description", ""),
                "pubDate":     item.findtext("pubDate", ""),
                "link":        item.findtext("link", ""),
            })
    except Exception as e:
        articles = [{"title": f"News fetch error: {e}", "description": "", "pubDate": "", "link": ""}]
    return articles

# ── Twitter / X search ────────────────────────────────────────────────────────
def get_tweets(query: str, max_results: int = 30) -> list[dict]:
    since = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"Authorization": f"Bearer {TWITTER_BEARER}"}
    params = {
        "query":        f"{query} -is:retweet lang:en",
        "max_results":  max_results,
        "start_time":   since,
        "tweet.fields": "created_at,public_metrics,text",
    }
    try:
        r = requests.get("https://api.twitter.com/2/tweets/search/recent",
                         headers=headers, params=params, timeout=15)
        data = r.json()
        if "data" not in data:
            return [{"text": f"Twitter: {data.get('detail', str(data))}", "created_at":"","likes":0,"retweets":0}]
        return [{"text": t["text"],
                 "created_at": t.get("created_at",""),
                 "likes":    t.get("public_metrics",{}).get("like_count",0),
                 "retweets": t.get("public_metrics",{}).get("retweet_count",0)}
                for t in data["data"]]
    except Exception as e:
        return [{"text": f"Twitter error: {e}", "created_at":"","likes":0,"retweets":0}]