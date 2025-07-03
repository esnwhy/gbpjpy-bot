from flask import Flask, request, jsonify
import os
import datetime
import requests

app = Flask(__name__)

# 環境変数設定
OANDA_API_URL = "https://api-fxtrade.oanda.com/v3/accounts"
ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.environ.get("OANDA_ACCESS_TOKEN")
NOTION_URL = os.environ.get("NOTION_WEBHOOK_URL")
ORDER_UNITS = 10000
STOP_LOSS_PIPS = 0.30  # 30 pips
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    signal = data.get("signal", "").lower()
    ticker = "GBP_JPY"
    price = float(data.get("price", "0"))
    timestamp = data.get("time", datetime.datetime.utcnow().isoformat())

    log_to_notion(signal, ticker, price, timestamp)

    if "buy" in signal:
        execute_order("buy", ticker, price)
    elif "sell" in signal:
        execute_order("sell", ticker, price)

    return jsonify({"status": "order processed"}), 200

def execute_order(signal_side, ticker, price):
    close_opposite_positions(signal_side, ticker)
    place_order(signal_side, ticker, price)

def close_opposite_positions(signal_side, ticker):
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/openPositions"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print("Failed to get positions.")
        return

    positions = response.json().get("positions", [])
    for pos in positions:
        if pos["instrument"] != ticker:
            continue
        long_units = int(float(pos["long"]["units"]))
        short_units = int(float(pos["short"]["units"]))

        if signal_side == "buy" and short_units < 0:
            print("🔁 Closing SHORT position before BUY")
            close_position(ticker, "short", abs(short_units))
        elif signal_side == "sell" and long_units > 0:
            print("🔁 Closing LONG position before SELL")
            close_position(ticker, "long", abs(long_units))

def close_position(ticker, side, units):
    close_data = {
        f"{side}Units": "ALL"
    }
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/positions/{ticker}/close"
    response = requests.put(url, headers=HEADERS, json=close_data)
    print(f"❌ Closed {side.upper()} position: {response.status_code} - {response.text}")

def place_order(side, ticker, price):
    units = ORDER_UNITS if side == "buy" else -ORDER_UNITS
    stop_loss_price = round(price - STOP_LOSS_PIPS, 3) if side == "buy" else round(price + STOP_LOSS_PIPS, 3)
    order_data = {
        "order": {
            "instrument": ticker,
            "units": str(units),
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "price": str(stop_loss_price)
            }
        }
    }
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/orders"
    response = requests.post(url, headers=HEADERS, json=order_data)
    print(f"📤 Placed {side.upper()} order: {response.status_code} - {response.text}")

def log_to_notion(signal, ticker, price, timestamp):
    if NOTION_URL:
        payload = {
            "ticker": ticker,
            "price": price,
            "signal": signal,
            "timestamp": timestamp
        }
        try:
            response = requests.post(NOTION_URL, json=payload)
            print(f"📝 Notion log: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Notion logging failed: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
