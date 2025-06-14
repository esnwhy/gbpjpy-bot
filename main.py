from flask import Flask, request
import os
import time

app = Flask(__name__)

last_signals = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received TEST webhook:", data, flush=True)

    signal = data.get("signal")
    symbol = data.get("symbol")
    now = time.time()

    key = f"{symbol}_{signal}"
    print(f"Current last_signals: {last_signals}", flush=True)

    if key in last_signals and now - last_signals[key] < 60:
        print(f"[SKIP] Duplicate {signal} for {symbol} (within 60s)", flush=True)
        return "Duplicate ignored", 200

    last_signals[key] = now
    print(f"[TEST] Accepted signal: {signal} for {symbol} at {now}", flush=True)
    return "Test order received", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)