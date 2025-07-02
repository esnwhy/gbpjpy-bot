from flask import Flask, request, jsonify
import os
import oandapyV20
import oandapyV20.endpoints.orders as orders

app = Flask(__name__)

ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("OANDA_ACCESS_TOKEN")
UNITS = int(os.getenv("TRADE_UNITS", 10000))  # default 10,000 units

client = oandapyV20.API(access_token=ACCESS_TOKEN)

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        message = data.get("message", "").lower()

        if "buy" in message:
            order_data = {
                "order": {
                    "instrument": "GBP_JPY",
                    "units": str(UNITS),
                    "type": "market",
                    "positionFill": "DEFAULT"
                }
            }
            r = orders.OrderCreate(ACCOUNT_ID, data=order_data)
            client.request(r)
            return jsonify({"status": "buy order sent"}), 200

        elif "sell" in message:
            order_data = {
                "order": {
                    "instrument": "GBP_JPY",
                    "units": str(-UNITS),
                    "type": "market",
                    "positionFill": "DEFAULT"
                }
            }
            r = orders.OrderCreate(ACCOUNT_ID, data=order_data)
            client.request(r)
            return jsonify({"status": "sell order sent"}), 200

        else:
            return jsonify({"error": "No valid signal found"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)