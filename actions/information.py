"""
actions/information.py — Live financial data, weather, world clock, news, currency exchange, sports scores, and Wikipedia.
Supports: real-time stock prices (Yahoo Finance), live weather (wttr.in), world clock and timezone conversion,
latest news, currency conversion, INR rates, cricket scores, and Wikipedia summaries.
Enforces: Never fabricate live data. If live API is unavailable, clearly report that.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo


def get_stock_price(parameters: dict = None, **kwargs) -> str:
    """Get real-time stock price and daily change using Yahoo Finance."""
    symbol = (parameters or {}).get("symbol", "").upper().strip()
    if not symbol:
        return "Please specify a stock ticker symbol (e.g. AAPL, TSLA, MSFT, RELIANCE.NS, TATAMOTORS.NS)."

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
        return f"Could not fetch live stock data for '{symbol}' ({e}). Live API unavailable."


def get_live_weather(parameters: dict = None, **kwargs) -> str:
    """Gets real-time weather information for a specified city or location."""
    city = (parameters or {}).get("city", "Delhi").strip()
    if not city:
        city = "Delhi"

    try:
        safe_city = urllib.parse.quote(city)
        url = f"https://wttr.in/{safe_city}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "MARK-LIII/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        curr = data["current_condition"][0]
        temp_c = curr.get("temp_C")
        desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
        humidity = curr.get("humidity")
        wind_km = curr.get("windspeedKmph")
        feels_c = curr.get("FeelsLikeC")

        return (
            f"🌤️ Live Weather in {city.title()}:\n"
            f"• Condition: {desc}\n"
            f"• Temperature: {temp_c}°C (Feels like {feels_c}°C)\n"
            f"• Humidity: {humidity}%\n"
            f"• Wind Speed: {wind_km} km/h"
        )
    except Exception as e:
        return f"Live weather data is currently unavailable for '{city}': {e}."


def convert_currency(parameters: dict = None, **kwargs) -> str:
    """Converts amount from one currency to another using live exchange rates."""
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
        return f"Currency conversion failed: live exchange rates unavailable ({e})."


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
            return "No live cricket matches currently scheduled or active."

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
        return "Live cricket score API is currently unreachable. Score unavailable."


def get_latest_news(parameters: dict = None, **kwargs) -> str:
    """Fetches latest real-time news headlines or topic-specific news."""
    topic = (parameters or {}).get("topic", "").strip()
    try:
        if topic:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&hl=en-IN&gl=IN&ceid=IN:en"
        else:
            url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            root = ET.fromstring(resp.read())

        items = root.findall("./channel/item")[:5]
        if not items:
            return f"No recent news found for '{topic}'." if topic else "No recent news found."

        header = f"📰 Latest News on '{topic}':" if topic else "📰 Top News Headlines:"
        out = [header]
        for idx, item in enumerate(items, 1):
            title = item.find("title").text if item.find("title") is not None else "News item"
            out.append(f"{idx}. {title}")
        return "\n".join(out)
    except Exception as e:
        return f"Could not retrieve latest news: {e}."


def get_world_clock(parameters: dict = None, **kwargs) -> str:
    """Provides current local times across major international time zones and cities."""
    city = (parameters or {}).get("city", "").strip().lower()

    timezones = {
        "new york": "America/New_York",
        "london": "Europe/London",
        "dubai": "Asia/Dubai",
        "mumbai": "Asia/Kolkata",
        "delhi": "Asia/Kolkata",
        "tokyo": "Asia/Tokyo",
        "singapore": "Asia/Singapore",
        "sydney": "Australia/Sydney",
        "san francisco": "America/Los_Angeles",
        "paris": "Europe/Paris",
        "berlin": "Europe/Berlin",
    }

    now_utc = datetime.now(ZoneInfo("UTC"))

    if city and city in timezones:
        tz_name = timezones[city]
        t = now_utc.astimezone(ZoneInfo(tz_name))
        return f"🕒 Time in {city.title()} ({tz_name}): {t.strftime('%A, %I:%M %p (%Z)')}"

    out = ["🌍 World Clock:"]
    for c_name, tz_name in [("Mumbai (IST)", "Asia/Kolkata"),
                            ("London (GMT/BST)", "Europe/London"),
                            ("New York (EST/EDT)", "America/New_York"),
                            ("San Francisco (PST/PDT)", "America/Los_Angeles"),
                            ("Dubai (GST)", "Asia/Dubai"),
                            ("Tokyo (JST)", "Asia/Tokyo")]:
        t = now_utc.astimezone(ZoneInfo(tz_name))
        out.append(f"• {c_name}: {t.strftime('%I:%M %p (%a)')}")
    return "\n".join(out)


def convert_timezone(parameters: dict = None, **kwargs) -> str:
    """Converts a given time between two time zones."""
    params = parameters or {}
    time_str = params.get("time", "").strip()  # e.g., "15:00" or "3:00 PM"
    from_tz = params.get("from_tz", "Asia/Kolkata").strip()
    to_tz = params.get("to_tz", "America/New_York").strip()

    try:
        # Standardize common names
        aliases = {"ist": "Asia/Kolkata", "est": "America/New_York", "pst": "America/Los_Angeles", "gmt": "UTC", "utc": "UTC"}
        f_tz = aliases.get(from_tz.lower(), from_tz)
        t_tz = aliases.get(to_tz.lower(), to_tz)

        today = datetime.now().date()
        parsed = None
        for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p"):
            try:
                parsed = datetime.strptime(time_str, fmt).time()
                break
            except ValueError:
                pass

        if not parsed:
            return f"Could not parse time '{time_str}'. Please use HH:MM format like '15:00' or '3:00 PM'."

        dt_from = datetime.combine(today, parsed, tzinfo=ZoneInfo(f_tz))
        dt_to = dt_from.astimezone(ZoneInfo(t_tz))

        return (
            f"🌐 Timezone Conversion:\n"
            f"• {time_str} in {f_tz} = {dt_to.strftime('%I:%M %p (%Z)')} in {t_tz}"
        )
    except Exception as e:
        return f"Timezone conversion failed: {e}."


def get_wikipedia_summary(parameters: dict = None, **kwargs) -> str:
    """Gets a concise 2-3 sentence Wikipedia summary for any topic or question."""
    topic = (parameters or {}).get("topic", "").strip()
    if not topic:
        return "Please specify a topic to search on Wikipedia."

    try:
        search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
        req = urllib.request.Request(search_url, headers={"User-Agent": "MARK-LIII/1.0"})
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
        "description": "Fetches real-time stock price and percentage change for any stock ticker symbol (e.g., AAPL, TSLA, GOOGL, RELIANCE.NS, TATAMOTORS.NS).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbol": {
                    "type": "STRING",
                    "description": "Stock ticker symbol (e.g. AAPL, NVDA, TSLA, RELIANCE.NS, TATAMOTORS.NS)."
                }
            },
            "required": ["symbol"]
        },
        "handler": get_stock_price,
    },
    {
        "name": "get_live_weather",
        "description": "Fetches real-time temperature, condition, humidity, and wind speed for any city.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {
                    "type": "STRING",
                    "description": "City name (e.g. Delhi, Mumbai, London, New York)."
                }
            },
            "required": []
        },
        "handler": get_live_weather,
    },
    {
        "name": "convert_currency",
        "description": "Converts an amount from one fiat currency to another using live exchange rates.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "amount": {
                    "type": "NUMBER",
                    "description": "Amount to convert (e.g. 100, 500)."
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
        "name": "get_latest_news",
        "description": "Fetches current real-time news headlines or topic-specific news.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {
                    "type": "STRING",
                    "description": "Optional keyword or topic to search news for."
                }
            },
            "required": []
        },
        "handler": get_latest_news,
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
        "name": "get_world_clock",
        "description": "Returns current local times across major international time zones and cities.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {
                    "type": "STRING",
                    "description": "Optional city name to get specific time for (e.g. London, Tokyo, New York)."
                }
            },
            "required": []
        },
        "handler": get_world_clock,
    },
    {
        "name": "convert_timezone",
        "description": "Converts a specific time between two timezones.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "time": {
                    "type": "STRING",
                    "description": "Time string (e.g. '15:00' or '3:00 PM')."
                },
                "from_tz": {
                    "type": "STRING",
                    "description": "Source timezone (e.g. 'Asia/Kolkata', 'IST', 'UTC')."
                },
                "to_tz": {
                    "type": "STRING",
                    "description": "Target timezone (e.g. 'America/New_York', 'EST', 'Europe/London')."
                }
            },
            "required": ["time", "from_tz", "to_tz"]
        },
        "handler": convert_timezone,
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
