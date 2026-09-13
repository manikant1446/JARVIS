"""
actions/information.py — Live financial data, currency exchange, sports scores, and Wikipedia ported from Layra.
Supports: real-time stock prices (Yahoo Finance), currency conversion, INR rates, cricket scores, and Wikipedia summaries.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request


def get_stock_price(parameters: dict = None, **kwargs) -> str:
    """Get real-time stock price and daily change using Yahoo Finance."""
    symbol = (parameters or {}).get("symbol", "").upper().strip()
    if not symbol:
        return "Please specify a stock ticker symbol (e.g. AAPL, TSLA, MSFT, RELIANCE.NS, TCS.NS)."

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", price)
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        currency = meta.get("currency", "USD")
        name = meta.get("longName") or meta.get("shortName") or symbol

        direction = "📈" if change >= 0 else "📉"
        sign = "+" if change >= 0 else ""
        return (
            f"{direction} {name} ({symbol})\n"
            f"Current Price: {currency} {price:.2f}\n"
            f"Daily Change: {sign}{change:.2f} ({sign}{change_pct:.2f}%)"
        )
    except Exception as e:
        return f"Could not fetch stock data for '{symbol}': {e}. Please ensure it is a valid ticker symbol."


def convert_currency(parameters: dict = None, **kwargs) -> str:
    """Converts amount from one currency to another using exchange rates."""
    params = parameters or {}
    amount = params.get("amount", 1.0)
    from_curr = params.get("from_currency", "USD").upper().strip()
    to_curr = params.get("to_currency", "INR").upper().strip()

    try:
        amount = float(amount)
    except Exception:
        amount = 1.0

    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        rates = data.get("rates", {})
        if to_curr not in rates:
            return f"Currency code '{to_curr}' was not found in exchange rates."

        rate = rates[to_curr]
        converted = amount * rate
        return (
            f"💱 Currency Conversion:\n"
            f"{amount:,.2f} {from_curr} = {converted:,.2f} {to_curr}\n"
            f"Rate: 1 {from_curr} = {rate:.4f} {to_curr}"
        )
    except Exception as e:
        return f"Currency conversion failed: {e}"


def get_inr_rates(parameters: dict = None, **kwargs) -> str:
    """Gets current exchange rates for major currencies against Indian Rupee (INR)."""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/INR"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rates = data.get("rates", {})

        currencies = ["USD", "EUR", "GBP", "AED", "SGD", "CAD", "AUD", "JPY"]
        lines = ["💹 Current INR Exchange Rates:"]
        for c in currencies:
            if c in rates and rates[c] > 0:
                inr_value = 1.0 / rates[c]
                lines.append(f"  • 1 {c} = ₹{inr_value:.2f}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not retrieve INR rates: {e}"


def get_cricket_score(parameters: dict = None, **kwargs) -> str:
    """Fetches live or recent cricket match scores."""
    try:
        url = "https://api.cricapi.com/v1/currentMatches?apikey=free&offset=0"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        matches = data.get("data", [])[:3]
        if not matches:
            return "No live cricket matches currently found."

        results = ["🏏 Live Cricket Matches:"]
        for m in matches:
            name = m.get("name", "Match")
            status = m.get("status", "")
            score = m.get("score", [])
            score_str = " | ".join(
                f"{s.get('inning','')}: {s.get('r','0')}/{s.get('w','0')} ({s.get('o','0')} ov)"
                for s in score[:2]
            ) if score else "Score pending"
            results.append(f"\n{name}\n{score_str}\n{status}")
        return "\n".join(results)
    except Exception:
        return "Live cricket scores currently unavailable from API."


def get_wikipedia_summary(parameters: dict = None, **kwargs) -> str:
    """Gets a concise 2-3 sentence Wikipedia summary for any topic or question."""
    topic = (parameters or {}).get("topic", "").strip()
    if not topic:
        return "Please specify a topic to search on Wikipedia."

    try:
        search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
        req = urllib.request.Request(search_url, headers={"User-Agent": "JarvisAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        title = data.get("title", topic)
        extract = data.get("extract", "No summary found.")
        sentences = extract.split(". ")
        summary = ". ".join(sentences[:3]) + ("." if len(sentences) > 3 else "")
        return f"📚 Wikipedia — {title}:\n{summary}"
    except Exception as e:
        return f"Wikipedia lookup failed for '{topic}': {e}"


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "get_stock_price",
        "description": "Fetches real-time stock price and percentage change for any stock ticker symbol (e.g., AAPL, TSLA, GOOGL, RELIANCE.NS).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbol": {
                    "type": "STRING",
                    "description": "Stock ticker symbol (e.g. AAPL, NVDA, TSLA, RELIANCE.NS)."
                }
            },
            "required": ["symbol"]
        },
        "handler": get_stock_price,
    },
    {
        "name": "convert_currency",
        "description": "Converts an amount from one fiat currency to another using live exchange rates.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "amount": {
                    "type": "NUMBER",
                    "description": "Amount to convert (e.g. 100)."
                },
                "from_currency": {
                    "type": "STRING",
                    "description": "Source 3-letter currency code (e.g. USD, EUR, GBP)."
                },
                "to_currency": {
                    "type": "STRING",
                    "description": "Target 3-letter currency code (e.g. INR, USD, EUR)."
                }
            },
            "required": ["amount", "from_currency", "to_currency"]
        },
        "handler": convert_currency,
    },
    {
        "name": "get_inr_rates",
        "description": "Returns current exchange rates for major currencies (USD, EUR, GBP, AED, CAD, AUD) converted to Indian Rupees (INR).",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_inr_rates,
    },
    {
        "name": "get_cricket_score",
        "description": "Gets live scores and match status for ongoing cricket matches.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_cricket_score,
    },
    {
        "name": "get_wikipedia_summary",
        "description": "Fetches a quick summary from Wikipedia for any person, place, concept, or event.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {
                    "type": "STRING",
                    "description": "Topic, person, or term to look up."
                }
            },
            "required": ["topic"]
        },
        "handler": get_wikipedia_summary,
    }
]
