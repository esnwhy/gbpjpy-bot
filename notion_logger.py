import requests
import datetime
import os

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def log_order_to_notion(order_type, amount, price, order_id, stop_loss, pnl):
    if not NOTION_API_KEY or not DATABASE_ID:
        print("Missing Notion API credentials.")
        return

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    now = datetime.datetime.utcnow().isoformat()
    payload = {
        "parent": { "database_id": DATABASE_ID },
        "properties": {
            "DateTime": {
                "date": { "start": now }
            },
            "Type": {
                "select": { "name": order_type }
            },
            "Amount": {
                "number": amount
            },
            "Price": {
                "number": price
            },
            "Order ID": {
                "rich_text": [{ "text": { "content": order_id } }]
            },
            "Stop Loss": {
                "number": stop_loss
            },
            "Unrealized PnL": {
                "number": pnl
            }
        }
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
    if response.status_code != 200:
        print("Failed to log to Notion:", response.status_code, response.text)
    else:
        print("✅ Order successfully logged to Notion.")
