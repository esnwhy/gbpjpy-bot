from flask import Flask, request
import oandapyV20
import oandapyV20.endpoints.orders as orders
import json
import os

app = Flask(__name__)

account_id = os.environ.get("OANDA_ACCOUNT_ID")
access_token = os.environ.get("OANDA_ACCESS_TOKEN")
api = oandapyV20.API(access_token=access_token)

@app.route("/", methods=["POST"])
def webhook():
    try:
        message = request.data.decode("utf-8").strip().lower()

        print(f"Received raw message: {message}")

        if "anybuy" in message:
            order_type = "buy"
        elif "anysell" in message:
            order_type = "sell"
        else:
            return "Invalid signal", 400

        units = 10000 if order_type == "buy" else -10000

        order_data = {
            "order": {
                "instrument": "GBP_JPY",
                "units": str(units),
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }

        r = orders.OrderCreate(account_id, data=order_data)
        api.request(r)

        print(f"{order_type.upper()} order placed")
        return f"{order_type.upper()} order placed", 200

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return f"Error: {e}", 500
