from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received TEST webhook:", data)

    signal = data.get("signal")
    symbol = data.get("symbol")

    if signal in ["buy", "sell"]:
        print(f"[TEST] Received signal: {signal} for {symbol}")
        return "Test order received", 200

    return "Invalid signal", 400
