import requests
import json
import os
import csv
from datetime import datetime
import time
from notion_logger import log_order_to_notion

ACCOUNT_ID = os.getenv('ACCOUNT_ID')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
OANDA_URL = 'https://api-fxtrade.oanda.com/v3/accounts'
HEADERS = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}

CSV_FILE = 'order_history.csv'

def log_order_to_csv(signal, result, success, unrealized_pl=None):
    fieldnames = ['timestamp', 'signal', 'success', 'order_id', 'status', 'error', 'unrealized_pl']
    timestamp = datetime.utcnow().isoformat()
    order_id = result.get('orderFillTransaction', {}).get('id') if success else ''
    status = result.get('orderFillTransaction', {}).get('reason') if success else ''
    error = result.get('errorMessage') if not success else ''
    row = {
        'timestamp': timestamp,
        'signal': signal,
        'success': success,
        'order_id': order_id,
        'status': status,
        'error': error,
        'unrealized_pl': unrealized_pl
    }
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def get_unrealized_pl():
    url = f"{OANDA_URL}/{ACCOUNT_ID}/openPositions"
    try:
        response = requests.get(url, headers=HEADERS)
        positions = response.json().get('positions', [])
        for pos in positions:
            if pos['instrument'] == 'GBP_JPY':
                return pos['unrealizedPL']
    except Exception as e:
        return f"Error: {e}"
    return "0"

def place_order(signal, retries=3):
    side = 'BUY' if signal == 'buy' else 'SELL'
    units = "1000" if side == 'BUY' else "-1000"
    order = {
        "order": {
            "units": units,
            "instrument": "GBP_JPY",
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "distance": "0.20"
            }
        }
    }
    url = f"{OANDA_URL}/{ACCOUNT_ID}/orders"
    for attempt in range(retries):
        try:
            response = requests.post(url, headers=HEADERS, data=json.dumps(order))
            result = response.json()
            success = 'orderFillTransaction' in result
            unrealized_pl = get_unrealized_pl()
            log_order_to_csv(signal, result, success, unrealized_pl)

            if success:
                log_order_to_notion(
                    order_type=side,
                    amount=abs(int(units)),
                    price=float(result['orderFillTransaction']['price']),
                    order_id=result['orderFillTransaction']['id'],
                    stop_loss=20,
                    pnl=float(result['orderFillTransaction'].get('pl', 0))
                )

            return result
        except Exception as e:
            time.sleep(2)
            if attempt == retries - 1:
                result = {'errorMessage': str(e)}
                log_order_to_csv(signal, result, success=False)
                return result
