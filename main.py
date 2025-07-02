
from flask import Flask, request
import oandapyV20
import oandapyV20.endpoints.orders as orders
import json
import os

app = Flask(__name__)

ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("OANDA_ACCESS_TOKEN")

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        alert_name = data.get("alert_name", "").lower()
        print(f"📩 Received alert: {alert_name}")

        client = oandapyV20.API(access_token=ACCESS_TOKEN)

        if "autobuy" in alert_name:
            order_data = {
                "order": {
                    "units": "10000",
                    "instrument": "GBP_JPY",
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                }
            }
            r = orders.OrderCreate(accountID=ACCOUNT_ID, data=order_data)
            client.request(r)
            print("✅ Buy order sent")

        elif "autosell" in alert_name:
            order_data = {
                "order": {
                    "units": "-10000",
                    "instrument": "GBP_JPY",
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                }
            }
            r = orders.OrderCreate(accountID=ACCOUNT_ID, data=order_data)
            client.request(r)
            print("✅ Sell order sent")
        else:
            print("❓ Unknown alert_name format")

        return "", 200
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return "Error", 500
