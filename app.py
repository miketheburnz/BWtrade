from flask import Flask, request, jsonify
import MetaTrader5 as mt5
import os
import logging
import time
import yfinance as yf
from keras.models import load_model
import numpy as np
import pandas as pd
from textblob import TextBlob
import requests
import talib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import json
import schedule

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='trading_app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize MetaTrader 5
if not mt5.initialize():
    logging.error("initialize() failed, error code = %s", mt5.last_error())
    quit()

# List of currency pairs
currency_pairs = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY",
    "GBPJPY", "AUDJPY", "CHFJPY", "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPCAD", "GBPNZD",
    "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY", "NZDJPY", "NZDCHF", "USDRUB", "USDZAR",
    "USDSGD", "USDHKD", "USDTRY", "USDSEK", "USDDKK", "USDNOK", "USDPLN", "USDMXN", "USDCNH",
    "USDHUF", "USDTHB", "USDILS", "USDCOP", "USDBRL", "USDKRW", "USDINR", "USDIDR",
    "USDPHP", "USDMYR", "USDVND"
]

models = {}
percentage_of_equity_to_trade = 0.01  # 1% of equity

# Load models
for pair in currency_pairs:
    model_path = f'C:/Users/Owner/Desktop/BWtrade/models/lstm_model_{pair}.keras'
    if os.path.exists(model_path):
        try:
            models[pair] = load_model(model_path)
            logging.info(f"Loaded model for {pair}")
        except Exception as e:
            logging.error(f"Error loading model for {pair}: {e}")
    else:
        logging.warning(f"Model file for {pair} does not exist at {model_path}")

def get_account_state():
    account_info = mt5.account_info()
    if account_info is None:
        logging.error("Failed to get account info, error code = %s", mt5.last_error())
        return None

    return {
        'balance': account_info.balance,
        'equity': account_info.equity,
        'margin': account_info.margin,
        'free_margin': account_info.margin_free
    }

def get_open_trades():
    open_positions = mt5.positions_get()
    if open_positions is None:
        logging.error("Failed to get open positions, error code = %s", mt5.last_error())
        return []
    
    open_trades = []
    for position in open_positions:
        open_trades.append({
            'order_id': position.ticket,
            'pair': position.symbol,
            'direction': 'buy' if position.type == mt5.ORDER_TYPE_BUY else 'sell',
            'lots': position.volume,
            'open_price': position.price_open,
            'profit': position.profit,
            'loss': position.price_open - position.price_current if position.type == mt5.ORDER_TYPE_BUY else position.price_current - position.price_open,
            'open_time': position.time
        })
    
    return open_trades

def place_order(pair, direction, lot_size):
    symbol_info = mt5.symbol_info(pair)
    if symbol_info is None:
        logging.error(f"Failed to get symbol info for {pair}, error code = %s", mt5.last_error())
        return None

    if not symbol_info.visible:
        if not mt5.symbol_select(pair, True):
            logging.error(f"Failed to select symbol {pair}, error code = %s", mt5.last_error())
            return None

    point = symbol_info.point
    price = mt5.symbol_info_tick(pair).ask if direction == 'buy' else mt5.symbol_info_tick(pair).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pair,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if direction == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": price - 100 * point if direction == 'buy' else price + 100 * point,
        "tp": price + 100 * point if direction == 'buy' else price - 100 * point,
        "deviation": 10,
        "magic": 234000,
        "comment": "Python script order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Failed to place order, error code = %s", mt5.last_error())
        return None

    return result

def close_order(order_id):
    position = mt5.positions_get(ticket=order_id)
    if position is None or len(position) == 0:
        logging.error(f"Failed to find position with ticket {order_id}, error code = %s", mt5.last_error())
        return None

    position = position[0]
    price = mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": position.ticket,
        "price": price,
        "deviation": 10,
        "magic": 234000,
        "comment": "Python script order close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Failed to close order, error code = %s", mt5.last_error())
        return None

    return result

def get_technical_indicators(data):
    data['SMA'] = talib.SMA(data['Close'], timeperiod=14)
    data['EMA'] = talib.EMA(data['Close'], timeperiod=14)
    data['MACD'], data['MACD_signal'], data['MACD_hist'] = talib.MACD(data['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    data['RSI'] = talib.RSI(data['Close'], timeperiod=14)
    data['BB_upper'], data['BB_middle'], data['BB_lower'] = talib.BBANDS(data['Close'], timeperiod=14, nbdevup=2, nbdevdn=2, matype=0)
    data['ATR'] = talib.ATR(data['High'], data['Low'], data['Close'], timeperiod=14)
    return data

def is_trending(data):
    recent_sma = data['SMA'].iloc[-1]
    recent_ema = data['EMA'].iloc[-1]
    return recent_sma > recent_ema  # Simple trend confirmation

def is_volatile(data):
    recent_atr = data['ATR'].iloc[-1]
    return recent_atr > data['ATR'].mean() * 1.5  # Volatility condition

def train_xgboost_model(data):
    features = ['SMA', 'EMA', 'MACD', 'MACD_signal', 'RSI', 'BB_upper', 'BB_lower', 'ATR']
    X = data[features].shift().dropna()
    y = (data['Close'].shift(-1) > data['Close']).astype(int).iloc[:-1]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = xgb.XGBClassifier()
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"XGBoost model accuracy: {accuracy}")

    return model

def fetch_market_data(pair):
    try:
        data = yf.download(pair + "=X", period="1mo", interval="1h")
        data = get_technical_indicators(data)
        return data
    except Exception as e:
        logging.error(f"Error fetching market data for {pair}: {e}")
        return None

def fetch_sentiment_analysis(pair):
    try:
        url = f'https://newsapi.org/v2/everything?q={pair}&apiKey=617ca539a455482c9a08f204f7af4d47'
        response = requests.get(url)
        articles = response.json().get('articles', [])
        sentiment_scores = [TextBlob(article['title']).sentiment.polarity for article in articles]
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
        return avg_sentiment
    except Exception as e:
        logging.error(f"Error fetching sentiment data for {pair}: {e}")
        return 0

def read_optimization_data():
    try:
        with open('optimization_data.json', 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        logging.error(f"Error reading optimization data: {e}")
        return {}

def update_trade_log(pair, trade_result):
    try:
        with open('trade_log.json', 'a') as file:
            json.dump({pair: trade_result}, file)
            file.write("\n")
    except Exception as e:
        logging.error(f"Error updating trade log: {e}")

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json(force=True)
        app.logger.info(f"Received data: {data}")
        
        if 'data' not in data or 'pair' not in data:
            return jsonify({"error": "Invalid input format"}), 400
        
        # Prepare data for prediction
        input_data = np.array(data['data']).reshape(1, -1)
        
        # Make prediction using the loaded model
        model = models.get(data['pair'])
        if model is None:
            app.logger.error(f"No model found for {data['pair']}")
            return jsonify({"error": f"No model found for {data['pair']}"}), 400
        
        # Ensure the input data shape is compatible with the model
        input_data = input_data.reshape((input_data.shape[0], input_data.shape[1], 1))
        prediction = model.predict(input_data)
        prediction_value = float(prediction[0][0])
        
        app.logger.info(f"Prediction for {data['pair']}: {prediction_value}")
        return jsonify({'prediction': prediction_value}), 200
    
    except Exception as e:
        app.logger.error(f"Error in prediction: {e}")
        return jsonify({"error": "Internal server error"}), 500

def main_trading_logic():
    account_state = get_account_state()
    if account_state is None:
        logging.error("Failed to retrieve account state.")
        return

    equity = account_state['equity']

    optimization_data = read_optimization_data()

    for pair in currency_pairs:
        try:
            model = models.get(pair)
            if model:
                data = fetch_market_data(pair)
                if data is None:
                    continue

                sentiment_score = fetch_sentiment_analysis(pair)
                prediction_input = data[['SMA', 'EMA', 'MACD', 'MACD_signal', 'RSI', 'BB_upper', 'BB_lower']].tail(10).values.reshape(1, 10, 7)
                prediction = model.predict(prediction_input)
                
                xgb_model = train_xgboost_model(data)
                xgb_prediction = xgb_model.predict(prediction_input)
                
                trend = is_trending(data)
                volatile = is_volatile(data)

                if sentiment_score > 0 and trend and not volatile:
                    trade_direction = 'buy' if prediction > 0.5 and xgb_prediction > 0.5 else 'sell'
                else:
                    trade_direction = 'sell' if prediction > 0.5 and xgb_prediction > 0.5 else 'buy'

                # Adjust lot size based on optimization data
                lot_size = (optimization_data.get(pair, {}).get('Risk', 0.01) * equity) / 100000
                lot_size = max(min(lot_size, 100), 0.01)

                if account_state['free_margin'] > lot_size * 100000 / 50:
                    open_trades = get_open_trades()
                    if len(open_trades) < 5:
                        order_result = place_order(pair, trade_direction, lot_size)
                        if order_result:
                            logging.info(f"Placed {trade_direction} order for {pair} with lot size {lot_size}: {order_result}")
                            # Update trade log with result
                            update_trade_log(pair, {
                                "trade_direction": trade_direction,
                                "lot_size": lot_size,
                                "result": order_result._asdict()
                            })
                        else:
                            logging.error(f"Failed to place {trade_direction} order for {pair} with lot size {lot_size}")
                    else:
                        logging.warning(f"Maximum open trades reached for {pair}")
                else:
                    logging.warning(f"Insufficient free margin to place new trade for {pair}")

        except Exception as e:
            logging.error(f"Error trading {pair}: {e}")
        # Add a delay between processing each pair to avoid rapid trading
        time.sleep(5)

def close_trades_logic():
    open_trades = get_open_trades()
    for trade in open_trades:
        try:
            profit_threshold = 100
            loss_threshold = -50
            maximum_holding_time = 3600

            if trade['profit'] >= profit_threshold or trade['loss'] <= loss_threshold:
                close_result = close_order(trade['order_id'])
                if close_result:
                    logging.info(f"Closed trade {trade['order_id']} due to profit/loss condition: {close_result}")
                    # Update trade log with closing result
                    update_trade_log(trade['pair'], {
                        "action": "close",
                        "order_id": trade['order_id'],
                        "result": close_result._asdict()
                    })
                else:
                    logging.error(f"Failed to close trade {trade['order_id']} due to profit/loss condition")

            current_time = time.time()
            holding_time = current_time - trade['open_time']
            if holding_time >= maximum_holding_time:
                close_result = close_order(trade['order_id'])
                if close_result:
                    logging.info(f"Closed trade {trade['order_id']} due to holding time condition: {close_result}")
                    # Update trade log with closing result
                    update_trade_log(trade['pair'], {
                        "action": "close",
                        "order_id": trade['order_id'],
                        "result": close_result._asdict()
                    })
                else:
                    logging.error(f"Failed to close trade {trade['order_id']} due to holding time condition")

        except Exception as e:
            logging.error(f"Error closing trade {trade['order_id']}: {e}")

def main():
    schedule.every(60).seconds.do(main_trading_logic)
    schedule.every(60).seconds.do(close_trades_logic)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    from threading import Thread
    flask_thread = Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': 5000})
    flask_thread.start()
    main()
