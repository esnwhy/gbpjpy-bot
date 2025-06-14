from flask import Flask, request
import oandapyV20
import oandapyV20.endpoints.orders as orders
import os

app = Flask(__name__)

# OANDA API環境変数
ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("OANDA_API_TOKEN")
client = oandapyV20.API(access_token=ACCESS_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received:", data)

    signal = data.get("signal")
    symbol = data.get("symbol")
    units = "100" if signal == "buy" else "-100"

    if signal in ["buy", "sell"]:
        order_data = {
            "order": {
                "instrument": symbol,
                "units": units,
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        r = orders.OrderCreate(accountID=ACCOUNT_ID, data=order_data)
        client.request(r)
        return "Order executed", 200

    return "Invalid signal", 400