from flask import Flask, request
import os
import time

app = Flask(__name__)

# 重複防止用の記録
last_signals = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received TEST webhook:", data)

    signal = data.get("signal")
    symbol = data.get("symbol")
    now = time.time()

    key = f"{symbol}_{signal}"
    if key in last_signals and now - last_signals[key] < 60:
        print(f"[SKIP] Duplicate {signal} for {symbol} (within 60s)")
        return "Duplicate ignored", 200

    last_signals[key] = now
    print(f"[TEST] Received signal: {signal} for {symbol}")
    return "Test order received", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)