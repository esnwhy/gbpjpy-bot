from flask import Flask, request, jsonify
import os
import datetime
import requests
import time
import json

app = Flask(__name__)

# === OANDA基本設定 ===
OANDA_API_URL = "https://api-fxtrade.oanda.com/v3/accounts"
ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("OANDA_ACCESS_TOKEN")

ORDER_UNITS = int(os.environ.get("ORDER_UNITS", "1000"))

# 推奨トレーリング幅（pips）。Webhookから "trail_pips" で上書き可
DEFAULT_TRAIL_PIPS = float(os.environ.get("DEFAULT_TRAIL_PIPS", "20"))

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

LOG_FILE = "log.txt"

# 通貨ペアごとの1pip値（価格の桁ベース）
# 例：GBP_JPYは 1 pip = 0.01, EUR_USDは 0.0001
PIP_VALUE_MAP = {
    "GBP_JPY": 0.01,
    "USD_JPY": 0.01,
    "EUR_JPY": 0.01,
    "EUR_USD": 0.0001,
    "GBP_USD": 0.0001,
    # 必要に応じて追加
}

def now_utc_iso():
    return datetime.datetime.utcnow().isoformat()

def log_line(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "no data"}), 400

        signal_raw = (data.get("signal") or "").lower()
        # 例: "buy+confirmed" → "buy"
        side = signal_raw.split("+")[0].strip()

        ticker = (data.get("ticker") or "GBP_JPY").upper()
        price = float(data.get("price") or 0)
        timestamp = data.get("time") or now_utc_iso()

        # トレーリング幅(pips)をpayloadから上書き可能
        trail_pips = float(data.get("trail_pips") or DEFAULT_TRAIL_PIPS)

        result = process_trade(side, ticker, price, timestamp, trail_pips)

        log_event(data, side, result)
        return jsonify({"status": "processed"}), 200

    except Exception as e:
        log_line(f"[{now_utc_iso()}] ERROR in webhook: {repr(e)}")
        return jsonify({"error": str(e)}), 500

def log_event(request_json, side, resp_obj):
    log_line(f"---")
    log_line(f"{now_utc_iso()}")
    log_line(f"Request: {json.dumps(request_json, ensure_ascii=False)}")
    log_line(f"Side: {side}")
    if resp_obj is None:
        log_line("OANDA Response: None")
    else:
        try:
            log_line(f"OANDA Response: {resp_obj.status_code} - {resp_obj.text}")
        except Exception:
            log_line("OANDA Response: <unreadable>")

def process_trade(side, ticker, price, timestamp, trail_pips):
    if side not in ("buy", "sell"):
        # 想定外シグナルは何もしない
        log_line(f"[{now_utc_iso()}] Skip unknown side: {side}")
        return None

    # まず逆方向ポジションをクローズ
    close_opposite_positions(side, ticker)

    # すぐに新規発注（トレーリングを同梱）
    return place_order(side, ticker, trail_pips)

def get_trailing_distance(ticker, trail_pips):
    pip_value = PIP_VALUE_MAP.get(ticker)
    if not pip_value:
        # 未登録ペアはデフォルト0.0001で計算（USD系想定）
        pip_value = 0.0001
    # OANDAのdistanceは“価格差”。pips -> price distance へ変換
    return trail_pips * pip_value

def close_opposite_positions(side, ticker):
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/openPositions"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        log_line(f"[{now_utc_iso()}] Failed to fetch positions: {response.status_code} {response.text}")
        return

    positions = response.json().get("positions", [])
    for pos in positions:
        if pos.get("instrument") != ticker:
            continue

        long_units = int(float(pos.get("long", {}).get("units", 0)))
        short_units = int(float(pos.get("short", {}).get("units", 0)))

        # 逆方向の建玉があれば全決済
        if side == "buy" and short_units < 0:
            close_position(ticker, "short")
        elif side == "sell" and long_units > 0:
            close_position(ticker, "long")

    # APIの整合が取れるまで短い待ちを入れる（約定直後の連続エラー回避）
    time.sleep(0.3)

def close_position(ticker, side):
    # side: "long" or "short"
    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/positions/{ticker}/close"
    payload = {f"{side}Units": "ALL"}
    response = requests.put(url, headers=HEADERS, json=payload, timeout=10)
    log_line(f"[{now_utc_iso()}] ❌ Closed {side.upper()} position {ticker}: {response.status_code} {response.text}")

def place_order(side, ticker, trail_pips):
    if not ACCOUNT_ID or not ACCESS_TOKEN:
        raise RuntimeError("Missing ACCOUNT_ID or ACCESS_TOKEN environment variables.")

    units = ORDER_UNITS if side == "buy" else -ORDER_UNITS

    trailing_distance = get_trailing_distance(ticker, trail_pips)
    # OANDAは文字列を推奨
    trailing_spec = {
        "timeInForce": "GTC",
        "distance": f"{trailing_distance:.5f}"
    }

    order_data = {
        "order": {
            "instrument": ticker,
            "units": str(units),
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "trailingStopLossOnFill": trailing_spec
        }
    }

    url = f"{OANDA_API_URL}/{ACCOUNT_ID}/orders"

    attempt = 0
    response = None
    while attempt < 3:
        response = requests.post(url, headers=HEADERS, json=order_data, timeout=10)
        if 200 <= response.status_code < 300:
            break
        attempt += 1
        log_line(f"[{now_utc_iso()}] ⚠️ Retry placing order (attempt {attempt})... {response.status_code} {response.text}")
        time.sleep(1.0)

    log_line(f"[{now_utc_iso()}] 📤 Placed {side.upper()} {ticker} (units {units}) with trailing {trail_pips} pips "
             f"(distance {trailing_distance:.5f}). Resp: {response.status_code if response else 'None'}")
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
