from tools import llm, extract_ticker, get_price_data, get_news, get_tweets
import json

# ── Agent 1: Price ─────────────────────────────────────────────────────────────
def agent_price(ticker: str) -> dict:
    data = get_price_data(ticker)
    summary = llm(
        system="You are a precise stock market data reporter. Summarize the price snapshot clearly for a trader dashboard.",
        user=f"""
Ticker: {data['ticker']} | Name: {data['name']}
Current Price: {data['price']} | Prev Close: {data['prev_close']} | Open: {data['open']}
Day High: {data['day_high']} | Day Low: {data['day_low']} | Volume: {data['volume']}
Market Cap: {data['market_cap']} | P/E: {data['pe_ratio']} | EPS: {data['eps']}
52W High: {data['52w_high']} | 52W Low: {data['52w_low']} | Beta: {data['beta']}
Sector: {data['sector']} | Industry: {data['industry']}
Write a concise 3-4 line snapshot summary.
"""
    )
    data["summary"] = summary
    return data

# ── Agent 2: News ──────────────────────────────────────────────────────────────
def agent_news(ticker: str, company: str) -> dict:
    articles = get_news(ticker, company)
    combined = "\n".join([f"- [{a['pubDate']}] {a['title']}: {a['description']}" for a in articles[:12]])
    analysis = llm(
        system="You are a financial news analyst. Analyze news sentiment. Be specific, mention war/macro risks if present.",
        user=f"""
Stock: {ticker} ({company})
Recent News:
{combined}

Provide:
1. Overall news sentiment (Bullish / Bearish / Neutral) with score -10 to +10
2. Key themes from news (bullet points)
3. Any macro/geopolitical risks (wars, sanctions, supply chain)
4. How this news might affect the stock in next 1-5 days
"""
    )
    return {"articles": articles[:8], "analysis": analysis}

# ── Agent 3: Twitter ───────────────────────────────────────────────────────────
def agent_twitter(ticker: str, company: str) -> dict:
    tweets = get_tweets(f"${ticker} OR {company} stock")
    tweet_text = "\n".join([f"[👍{t['likes']} 🔁{t['retweets']}] {t['text']}" for t in tweets[:20]])
    analysis = llm(
        system="You are a social media sentiment analyst for financial markets.",
        user=f"""
Stock: {ticker} ({company})
Last 24hr Tweets:
{tweet_text}

Provide:
1. Social sentiment score -10 to +10
2. Dominant retail trader opinion
3. Any viral narratives or FUD spreading
4. Influencer-level signals if any
5. One-line conclusion: what the crowd thinks
"""
    )
    return {"tweets": tweets[:10], "analysis": analysis}

# ── Agent 4: Fundamentals ──────────────────────────────────────────────────────
def agent_fundamental(price_data: dict) -> dict:
    hist_5y_str  = json.dumps(price_data["hist_5y"][-12:])
    hist_10y_str = json.dumps(price_data["hist_10y"][-12:])
    analysis = llm(
        system="You are a veteran fundamental analyst with 20+ years experience including macro, wars, and interest rates.",
        user=f"""
Stock: {price_data['ticker']} | {price_data['name']}
Sector: {price_data['sector']} | Industry: {price_data['industry']}
Price: {price_data['price']} | P/E: {price_data['pe_ratio']} | EPS: {price_data['eps']}
Market Cap: {price_data['market_cap']} | Beta: {price_data['beta']} | Dividend: {price_data['dividend']}
52W High: {price_data['52w_high']} | 52W Low: {price_data['52w_low']}
5Y History (last 12 pts): {hist_5y_str}
10Y History (last 12 pts): {hist_10y_str}
Global Context: Ongoing wars (Russia-Ukraine, Middle East), elevated rates, inflation, supply chain stress.

Perform COMPLETE analysis:
1. PAST 10 YEAR analysis — trend, turning points, CAGR estimate
2. PAST 5 YEAR analysis — growth pattern, COVID impact, recovery
3. VALUATION — overvalued / undervalued / fairly valued?
4. RISKS — fundamental, macro, geopolitical, sector-specific
5. NEXT 5 YEAR OUTLOOK — projected trajectory with war/macro considerations
"""
    )
    return {"analysis": analysis}

# ── Agent 5: Strategy & Verdict ────────────────────────────────────────────────
def agent_strategy(ticker: str, price_data: dict, news_analysis: str,
                   twitter_analysis: str, fundamental_analysis: str) -> dict:
    verdict = llm(
        system="You are a master trading strategist. Be bold, specific, honest. Consider current war/macro environment heavily.",
        user=f"""
Stock: {ticker} | Price: {price_data['price']}
52W High: {price_data['52w_high']} | 52W Low: {price_data['52w_low']}
Beta: {price_data['beta']} | P/E: {price_data['pe_ratio']}

NEWS SENTIMENT: {news_analysis}
TWITTER SENTIMENT: {twitter_analysis}
FUNDAMENTAL ANALYSIS: {fundamental_analysis}

Global: Active wars, elevated rates, dollar strength, supply chain stress.

Give COMPLETE strategy for ALL trader types:
1. 🏃 INTRADAY — Entry zone, exit target, stop loss, risk level
2. 🌊 SWING (1-4 weeks) — Setup, entry, targets, invalidation level
3. 📅 SHORT TERM (1-3 months) — Key catalyst, price targets
4. 📈 LONG TERM (1-5 years) — Accumulation strategy, DCA levels
5. 🏦 INVESTOR (5-10 years) — Is this a compounder? Buy/avoid?

FINAL VERDICT:
- Overall Score: X/10
- WORTH BUYING NOW? Yes / No / Wait — with clear reason
- Best entry price if yes
- The ONE risk that could kill this trade
"""
    )
    return {"verdict": verdict}

# ── Graph Orchestrator ─────────────────────────────────────────────────────────
# In run_graph() — replace the ticker extraction block with:
def run_graph(raw_input: str) -> dict:
    from tools import validate_ticker
    logs = []

    logs.append(f"🔎 Extracting ticker from: '{raw_input}'...")
    ticker = extract_ticker(raw_input)
    logs.append(f"🔍 Resolved: {ticker} — validating with Yahoo Finance...")
    ticker = validate_ticker(ticker)
    logs.append(f"✅ Confirmed ticker: {ticker}")

    logs.append("📈 Agent 1: Fetching live price data...")
    price_data = agent_price(ticker)
    company = price_data.get("name", ticker)

    logs.append("📰 Agent 2: Analyzing today's & yesterday's news...")
    news_result = agent_news(ticker, company)

    logs.append("🐦 Agent 3: Scanning Twitter/X last 24hrs...")
    twitter_result = agent_twitter(ticker, company)

    logs.append("📊 Agent 4: Running fundamental + 10Y/5Y historical analysis...")
    fund_result = agent_fundamental(price_data)

    logs.append("🎯 Agent 5: Building trading strategy & final verdict...")
    strategy_result = agent_strategy(
        ticker, price_data,
        news_result["analysis"],
        twitter_result["analysis"],
        fund_result["analysis"]
    )

    logs.append("✅ All 5 agents complete.")
    return {
        "ticker":      ticker,
        "company":     company,
        "logs":        logs,
        "price":       price_data,
        "news":        news_result,
        "twitter":     twitter_result,
        "fundamental": fund_result,
        "strategy":    strategy_result,
    }