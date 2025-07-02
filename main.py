
from flask import Flask, request
import oanda_trade
import notion_logger

app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)  # Content-Type 無視してJSONとして読み取る
        print(f"✅ Raw received data: {data}")
        signal = data.get("signal", "").lower()
        if signal in ["buy", "buy+", "anybuy"]:
            oanda_trade.execute_trade("buy", units=10000)
        elif signal in ["sell", "sell+", "anysell"]:
            oanda_trade.execute_trade("sell", units=10000)
        else:
            print("⚠️ No valid signal found in payload.")
        notion_logger.log_to_notion(data)
        return "✅ Webhook received", 200
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return "❌ Error", 400
