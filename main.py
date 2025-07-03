from flask import Flask, request, jsonify
import os
import datetime
import requests

app = Flask(__name__)

OANDA_API_URL = "https://api-fxtrade.oanda.com/v3/accounts"
ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.environ.get("OANDA_ACCESS_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

ORDER_UNITS = 40000
STOP_LOSS_PIPS = 0.20
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

recent_alerts = {}

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data"}), 400

    signal = data.get("signal", "").lower()
    ticker = "GBP_JPY"
    price = float(data.get("price", "0"))
    timestamp = data.get("time", datetime.datetime.utcnow().isoformat())

    key = f"{ticker}:{signal}:{round(price, 3)}"
    now = datetime.datetime.utcnow()
    last_seen = recent_alerts.get(key)
    if last_seen and (now - last_seen).total_seconds() < 60:
        print(f"⚠️ Duplicate alert ignored: {key}")
        return jsonify({"status": "duplicate ignored"}), 200
    else:
        recent_alerts[key] = now

    if "buy" in signal or "sell" in signal:
        process_trade(signal, ticker, price, timestamp)

    return jsonify({"status": "processed"}), 200

def process_trade(signal, ticker, price, timestamp):
    opposite = "sell" if "buy" in signal else "buy"
    existing = find_open_position(opposite)

    if existing:
        entry_price = float(existing['properties']['Price']['number'])
        direction = signal.split("+")[0]
        profit = calc_profit(entry_price, price, direction)
        page_id = existing["id"]
        update_notion_closed(page_id, profit)
        print(f"✅ Closed previous position. Profit: {profit}")
    else:
        log_to_notion(signal, ticker, price, timestamp)

    execute_order(signal.split("+")[0], ticker, price)

def calc_profit(entry, exit, side):
    diff = (exit - entry) if side == "buy" else (entry - exit)
    return round(diff * ORDER_UNITS, 1)

def execute_order(side, ticker, price):
    close_opposite_positions(side, ticker)
    place_order(side, ticker, price)

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
    response = requests.post(url, headers=HEADERS, json=order_data)
    print(f"📤 Placed {side.upper()} order: {response.status_code}")

def log_to_notion(signal, ticker, price, timestamp):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Ticker": {"title": [{"text": {"content": ticker}}]},
            "Signal": {"rich_text": [{"text": {"content": signal}}]},
            "Price": {"number": price},
            "Timestamp": {"date": {"start": timestamp}},
            "Status": {"select": {"name": "Open"}},
            "Profit (JPY)": {"number": 0},
            "Stop Loss Triggered": {"checkbox": False}
        }
    }
    requests.post(url, headers=headers, json=payload)

def find_open_position(direction):
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    query = {
        "filter": {
            "and": [
                {"property": "Status", "select": {"equals": "Open"}},
                {"property": "Signal", "rich_text": {"contains": direction}}
            ]
        },
        "page_size": 1,
        "sorts": [{"timestamp": "created_time", "direction": "descending"}]
    }
    response = requests.post(url, headers=headers, json=query)
    results = response.json().get("results", [])
    return results[0] if results else None

def update_notion_closed(page_id, profit):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "properties": {
            "Status": {"select": {"name": "Closed"}},
            "Profit (JPY)": {"number": profit},
            "Stop Loss Triggered": {"checkbox": False}
        }
    }
    requests.patch(url, headers=headers, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
