
from flask import Flask, request
import oanda_trade
import notion_logger
import json

app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("✅ Webhook received!")
        print("🔹 Raw data:", data)

        if not data or "signal" not in data:
            return "❌ Missing 'signal' field in JSON", 400

        signal = data["signal"].lower()
        print(f"🔍 Signal received: {signal}")

        if signal == "anybuy":
            result = oanda_trade.execute_trade("buy", 10000)
            notion_logger.log_to_notion("BUY", result)
            return "✅ Executed BUY", 200

        elif signal == "anysell":
            result = oanda_trade.execute_trade("sell", 10000)
            notion_logger.log_to_notion("SELL", result)
            return "✅ Executed SELL", 200

        else:
            return f"❌ Unknown signal: {signal}", 400

    except Exception as e:
        print("❌ Error processing webhook:", str(e))
        return f"❌ Internal error: {str(e)}", 500

@app.route("/", methods=["GET"])
def index():
    return "⚡ GBPJPY Bot is running.", 200
