from flask import Flask, request
import os
import oandapyV20
import oandapyV20.endpoints.orders as orders

app = Flask(__name__)

ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("OANDA_ACCESS_TOKEN")
client = oandapyV20.API(access_token=ACCESS_TOKEN)

@app.route("/", methods=["POST"])
def webhook():
    try:
        alert_text = request.get_data(as_text=True).strip()
        print("🔔 Alert Text Received:", alert_text)

        if "AutoBuy-GbpJpy" in alert_text:
            return place_order("BUY")
        elif "AutoSell-GbpJpy" in alert_text:
            return place_order("SELL")
        else:
            print("⚠️ Unknown alert received")
            return "Ignored", 200

    except Exception as e:
        print("❌ Error processing webhook:", e)
        return "Error", 500

def place_order(side):
    order_data = {
        "order": {
            "instrument": "GBP_JPY",
            "units": "10000" if side == "BUY" else "-10000",
            "type": "MARKET",
            "positionFill": "DEFAULT"
        }
    }

    r = orders.OrderCreate(accountID=ACCOUNT_ID, data=order_data)
    client.request(r)
    print(f"✅ {side} order executed")
    return f"{side} order executed", 200

if __name__ == "__main__":
    app.run(port=10000)
