from flask import Flask, request, jsonify, render_template
import schedule
import time
from threading import Thread
from utils.logger import setup_logging
from utils.data_fetcher import fetch_market_data, fetch_sentiment_analysis
from utils.model_trainer import load_models, prepare_prediction_data, predict, train_xgboost_model
from utils.trading import initialize_mt5, get_account_state, get_open_trades, place_order, close_order, execute_trades, close_open_trades
from config import load_config, save_config

app = Flask(__name__)

# Configure logging
logger = setup_logging('trading_app.log')

# Load configuration
config = load_config()

# Initialize MetaTrader 5
if not initialize_mt5():
    quit()

# List of currency pairs
currency_pairs = config['currency_pairs']

models = load_models(currency_pairs)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/configure', methods=['GET', 'POST'])
def configure():
    if request.method == 'POST':
        config['currency_pairs'] = request.form['currencyPairs'].split(',')
        config['trade_volume'] = float(request.form['tradeVolume'])
        config['stop_loss'] = float(request.form['stopLoss'])
        config['take_profit'] = float(request.form['takeProfit'])
        save_config(config)
        return jsonify({"status": "Configuration updated successfully"}), 200
    return render_template('config.html', config=config)

@app.route('/predict', methods=['POST'])
def predict_route():
    try:
        data = request.get_json(force=True)
        logger.info(f"Received data: {data}")

        if 'data' not in data or 'pair' not in data:
            return jsonify({"error": "Invalid input format"}), 400

        input_data = prepare_prediction_data(data['data'])
        prediction = predict(models, data['pair'], input_data)

        if prediction is None:
            return jsonify({"error": f"No model found for {data['pair']}"}), 400

        logger.info(f"Prediction for {data['pair']}: {prediction}")
        return jsonify({'prediction': float(prediction[0][0])}), 200
    except Exception as e:
        logger.error(f"Error in prediction: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/logs')
def logs():
    with open('logs/trading_app.log', 'r') as f:
        logs = f.readlines()
    return render_template('logs.html', logs=logs)

def main_trading_logic():
    account_state = get_account_state()
    if account_state is None:
        logger.error("Failed to retrieve account state.")
        return

    execute_trades(models, currency_pairs, account_state)

def close_trades_logic():
    close_open_trades()

def main():
    schedule.every(60).seconds.do(main_trading_logic)
    schedule.every(60).seconds.do(close_trades_logic)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    flask_thread = Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': 5000})
    flask_thread.start()
    main()
