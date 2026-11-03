"""Serves the planner and keeps market data fresh in the background."""
import os, threading, time
from flask import Flask, jsonify, send_from_directory
import market_data_updater as mu

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "market_data.json")
INTERVAL = float(os.environ.get("REFRESH_HOURS", "6")) * 3600
app = Flask(__name__)


def loop():
    while True:
        try:
            mu.main(DATA)
            print("market data refreshed")
        except Exception as e:
            print("refresh failed:", e)
        time.sleep(INTERVAL)


@app.route("/")
def home():
    return send_from_directory(HERE, "index.html")


@app.route("/api/market")
def market():
    if not os.path.exists(DATA):
        return jsonify({"error": "Market data is still loading. Try again in a minute."}), 503
    resp = send_from_directory(HERE, "market_data.json")
    resp.headers["Cache-Control"] = "no-store"
    return resp


threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
