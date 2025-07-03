from flask import Flask, request, jsonify
import os
import datetime
import requests
import time

app = Flask(__name__)

OANDA_API_URL = "https://api-fxtrade.oanda.com/v3/accounts"
ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.environ.get("OANDA_ACCESS_TOKEN")

ORDER_UNITS = 40000
STOP_LOSS_PIPS = 0.20
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

LOG_FILE = "log.txt"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    signal = data.get("signal", "").lower()
    ticker = "GBP_JPY"
    price = float(data.get("price", "0"))
    timestamp = data.get("time", datetime.datetime.utcnow().isoformat())

    result = process_trade(signal, ticker, price, timestamp)
    log_event(data, signal, result)
    return jsonify({"status": "processed"}), 200

def log_event(data, signal, oanda_response):
    with open(LOG_FILE, "a") as f:
        f.write(f"---\n{datetime.datetime.utcnow().isoformat()}\n")
        f.write(f"Request: {data}\n")
        f.write(f"Signal: {signal}\n")
        f.write(f"OANDA Response: {oanda_response.status_code} - {oanda_response.text}\n")

def process_trade(signal, ticker, price, timestamp):
    return execute_order(signal.split("+")[0], ticker, price)

def execute_order(side, ticker, price):
    close_opposite_positions(side, ticker)
    return place_order(side, ticker, price)

def close_opposite_positions(side, ticker):
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/openPositions"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return

    positions = response.json().get("positions", [])
    for pos in positions:
        if pos["instrument"] != ticker:
            continue
        long_units = int(float(pos["long"]["units"]))
        short_units = int(float(pos["short"]["units"]))
        if side == "buy" and short_units < 0:
            close_position(ticker, "short")
        elif side == "sell" and long_units > 0:
            close_position(ticker, "long")

def close_position(ticker, side):
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/positions/{ticker}/close"
    response = requests.put(url, headers=HEADERS, json={f"{side}Units": "ALL"})
    print(f"❌ Closed {side.upper()} position: {response.status_code}")

def place_order(side, ticker, price):
    units = ORDER_UNITS if side == "buy" else -ORDER_UNITS
    sl_price = round(price - STOP_LOSS_PIPS, 3) if side == "buy" else round(price + STOP_LOSS_PIPS, 3)
    order_data = {
        "order": {
            "instrument": ticker,
            "units": str(units),
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {"price": str(sl_price)}
        }
    }
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/orders"
    attempt = 0
    while attempt < 3:
        response = requests.post(url, headers=HEADERS, json=order_data)
        if response.status_code >= 200 and response.status_code < 300:
            break
        else:
            print(f"⚠️ Retry placing order (attempt {attempt+1})...")
            attempt += 1
            time.sleep(1)
    print(f"📤 Placed {side.upper()} order: {response.status_code}")
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
