from flask import Flask, request, jsonify
from oanda_trade import place_order
import time
import logging
import os

app = Flask(__name__)
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s %(message)s')

last_order_time = 0
last_order_signal = None
cooldown_seconds = 60

@app.route('/', methods=['POST'])
def webhook():
    global last_order_time, last_order_signal

    try:
        data = request.get_json(force=True, silent=True)
        logging.info(f"Raw received data: {data}")
        if not data:
            return jsonify({'error': 'No JSON received'}), 400
    except Exception as e:
        logging.error(f"JSON decode failed: {str(e)}")
        return jsonify({'error': 'Invalid JSON'}), 400

    signal = None
    if isinstance(data, str):
        signal = data.lower()
    elif isinstance(data, dict) and 'signal' in data:
        signal = data['signal'].lower()

    # anybuy/anysell のマッピング
    if signal == 'anybuy':
        signal = 'buy'
    elif signal == 'anysell':
        signal = 'sell'

    if signal not in ['buy', 'sell']:
        logging.info("Invalid or missing signal.")
        return jsonify({'error': 'Invalid signal'}), 400

    current_time = time.time()
    if signal == last_order_signal and (current_time - last_order_time) < cooldown_seconds:
        logging.info("Duplicate signal ignored due to cooldown.")
        return jsonify({'status': 'duplicate signal ignored'}), 200

    response = place_order(signal)
    last_order_time = current_time
    last_order_signal = signal
    logging.info(f"Order placed: {signal}, Response: {response}")
    return jsonify({'status': 'order sent', 'response': response}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
