"""
market_data_updater.py
Fetches index data for the world's largest exchanges plus inflation by country,
then writes market_data.json for the Investment Planner page.

Setup:   pip install yfinance pandas requests
Run:     python market_data_updater.py
Daily:   cron  ->  0 */6 * * *  python /path/market_data_updater.py
Then open the planner and upload market_data.json in the "Market data" card.
Note: index levels are price returns (dividends excluded), so they understate total return.
"""
import json, math, sys, datetime as dt
import pandas as pd, requests, yfinance as yf

# symbol, display name, exchange, planner country (None = shown only)
INDICES = [
    ("^GSPC", "S&P 500", "NYSE / US", "United States"),
    ("^IXIC", "NASDAQ Composite", "NASDAQ", None),
    ("^DJI", "Dow Jones", "NYSE", None),
    ("^NSEI", "NIFTY 50", "NSE India", "India"),
    ("^BSESN", "SENSEX", "BSE India", None),
    ("^FTSE", "FTSE 100", "London", "United Kingdom"),
    ("^N225", "Nikkei 225", "Tokyo", "Japan"),
    ("^GDAXI", "DAX", "Frankfurt", "Germany"),
    ("^STI", "Straits Times", "Singapore", "Singapore"),
    ("^AXJO", "ASX 200", "Australia", "Australia"),
    ("^GSPTSE", "S&P/TSX", "Toronto", "Canada"),
    ("^BVSP", "Ibovespa", "B3 Brazil", "Brazil"),
    ("^HSI", "Hang Seng", "Hong Kong", None),
    ("000001.SS", "SSE Composite", "Shanghai", None),
]
ISO = {"India": "IN", "United States": "US", "United Kingdom": "GB", "Japan": "JP", "Germany": "DE",
       "Singapore": "SG", "UAE": "AE", "Australia": "AU", "Canada": "CA", "Brazil": "BR"}


def analyse(sym, name, exch, country):
    s = yf.Ticker(sym).history(period="11y", auto_adjust=True)["Close"].dropna()
    if len(s) < 260:
        raise ValueError("not enough history")
    last, end = float(s.iloc[-1]), s.index[-1]

    def back(days):
        return float(s.asof(end - pd.Timedelta(days=days)))

    def cagr(years):
        if (end - s.index[0]).days / 365.25 < years - 0.6:
            return None
        return (last / back(int(years * 365.25))) ** (1 / years) - 1

    ma200 = float(s.tail(200).mean())
    ret6m = last / back(182) - 1
    vol = float(s.pct_change().tail(252).std() * math.sqrt(252))
    if last > ma200 and ret6m > 0 and vol < 0.25:
        style = "Bull"
    elif last < ma200 and ret6m < 0:
        style = "Bear"
    elif vol >= 0.25:
        style = "Volatile"
    else:
        style = "Sideways"
    return {"name": name, "exchange": exch, "symbol": sym, "country": country, "last": round(last, 2),
            "ret1y": last / back(365) - 1, "ret3y": cagr(3), "cagr5": cagr(5), "cagr10": cagr(10),
            "vol": vol, "drawdown": last / float(s.max()) - 1,
            "trend": "Above 200-day avg" if last > ma200 else "Below 200-day avg", "style": style}


def inflation(iso):
    url = f"https://api.worldbank.org/v2/country/{iso}/indicator/FP.CPI.TOTL.ZG?format=json&mrnev=1"
    v = requests.get(url, timeout=20).json()[1][0]["value"]
    return None if v is None else min(0.15, max(0.0, v / 100))


def main(path="market_data.json"):
    out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(), "indices": [], "byCountry": {}, "inflation": {}}
    for sym, name, exch, country in INDICES:
        try:
            row = analyse(sym, name, exch, country)
            out["indices"].append(row)
            if country:
                out["byCountry"][country] = {"cagr10": row["cagr10"], "vol": row["vol"], "style": row["style"]}
        except Exception as e:
            print(f"skip {sym}: {e}", file=sys.stderr)
    for country, iso in ISO.items():
        try:
            v = inflation(iso)
            if v is not None:
                out["inflation"][country] = v
        except Exception as e:
            print(f"skip inflation {country}: {e}", file=sys.stderr)
    if not out["indices"]:
        raise RuntimeError("No market data fetched; keeping the previous file")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"Wrote market_data.json: {len(out['indices'])} indices, {len(out['inflation'])} inflation figures")


if __name__ == "__main__":
    main()
