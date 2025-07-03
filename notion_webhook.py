from flask import Flask, request, jsonify
import os
import requests
import datetime

app = Flask(__name__)

NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    ticker = data.get("ticker", "")
    price = float(data.get("price", 0))
    signal = data.get("signal", "").capitalize()
    timestamp = data.get("timestamp", datetime.datetime.utcnow().isoformat())

    notion_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Signal": {"rich_text": [{"text": {"content": signal}}]},
            "Ticker": {"title": [{"text": {"content": ticker}}]},
            "Price": {"number": price},
            "Timestamp": {"date": {"start": timestamp}},
            "Status": {"select": {"name": "Open"}},
            "Profit (JPY)": {"number": 0}
        }
    }

    response = requests.post(notion_url, headers=headers, json=payload)
    return jsonify({"notion_response": response.status_code}), response.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
