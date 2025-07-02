import os
import json
from flask import Flask, request
import oandapyV20
import oandapyV20.endpoints.orders as orders

app = Flask(__name__)

ACCOUNT_ID = os.getenv("ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
OANDA_URL = "https://api-fxtrade.oanda.com/v3"

client = oandapyV20.API(access_token=ACCESS_TOKEN)

def execute_order(order_type):
    data = {
        "order": {
            "units": "10000" if order_type == "buy" else "-10000",
            "instrument": "GBP_JPY",
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT"
        }
    }
    r = orders.OrderCreate(accountID=ACCOUNT_ID, data=data)
    try:
        client.request(r)
        print(f"✅ {order_type.upper()} order executed")
    except Exception as e:
        print(f"❌ Error executing {order_type} order:", e)

@app.route("/", methods=["POST"])
def webhook():
    try:
        alert_text = request.get_data(as_text=True).strip()
        print(f"🔔 Alert Text Received (raw): {alert_text}")

        if alert_text == "anybuy":
            print("✅ Buy signal received")
            execute_order("buy")
        elif alert_text == "anysell":
            print("✅ Sell signal received")
            execute_order("sell")
        else:
            print("⚠️ Unknown alert received")
        return "", 200
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)