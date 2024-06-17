import MetaTrader5 as mt5
import os
import logging
import time
import yfinance as yf
from keras.models import load_model
import numpy as np
from textblob import TextBlob
import requests

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
    "USDHUF", "USDTHB", "USDILS", "USDCLP", "USDCOP", "USDBRL", "USDKRW", "USDINR", "USDIDR",
    "USDPHP", "USDMYR", "USDVND"
]

models = {}
percentage_of_equity_to_trade = 0.01  # 1% of equity

# Load models
for pair in currency_pairs:
    model_path = f'C:/Users/Owner/Desktop/BWtrade/models/model_{pair}.keras'
    if os.path.exists(model_path):
        models[pair] = load_model(model_path)
        logging.info(f"Loaded model for {pair}")
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
    data['SMA'] = data['Close'].rolling(window=14).mean()
    data['EMA'] = data['Close'].ewm(span=14, adjust=False).mean()
    data['MACD'] = data['Close'].ewm(span=12, adjust=False).mean() - data['Close'].ewm(span=26, adjust=False).mean()
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
    data['RSI'] = 100 - (100 / (1 + (data['Close'].diff(1).dropna().gt(0).sum() / data['Close'].diff(1).dropna().lt(0).sum())))
    data['BB_upper'] = data['SMA'] + 2 * data['Close'].rolling(window=14).std()
    data['BB_lower'] = data['SMA'] - 2 * data['Close'].rolling(window=14).std()
    return data

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
        # Example of fetching sentiment data
        url = f'https://newsapi.org/v2/everything?q={pair}&apiKey=617ca539a455482c9a08f204f7af4d47'
        response = requests.get(url)
        articles = response.json().get('articles', [])
        sentiment_scores = [TextBlob(article['title']).sentiment.polarity for article in articles]
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
        return avg_sentiment
    except Exception as e:
        logging.error(f"Error fetching sentiment data for {pair}: {e}")
        return 0

def main_trading_logic():
    account_state = get_account_state()
    if account_state is None:
        logging.error("Failed to retrieve account state.")
        return

    equity = account_state['equity']

    for pair in currency_pairs:
        try:
            model = models.get(pair)
            if model:
                data = fetch_market_data(pair)
                if data is None:
                    continue

                sentiment_score = fetch_sentiment_analysis(pair)
                prediction_input = data[['SMA', 'EMA', 'MACD', 'Signal', 'RSI', 'BB_upper', 'BB_lower']].tail(10).values.reshape(1, 10, 7)
                prediction = model.predict(prediction_input)
                
                # Adjust trade direction based on sentiment analysis
                if sentiment_score > 0:
                    trade_direction = 'buy' if prediction > 0.5 else 'sell'
                else:
                    trade_direction = 'sell' if prediction > 0.5 else 'buy'

                lot_size = (percentage_of_equity_to_trade * equity) / 100000
                lot_size = max(min(lot_size, 100), 0.01)

                if account_state['free_margin'] > lot_size * 100000 / 50:
                    open_trades = get_open_trades()
                    if len(open_trades) < 5:
                        order_result = place_order(pair, trade_direction, lot_size)
                        if order_result:
                            logging.info(f"Placed {trade_direction} order for {pair} with lot size {lot_size}: {order_result}")
                        else:
                            logging.error(f"Failed to place {trade_direction} order for {pair} with lot size {lot_size}")
                    else:
                        logging.warning(f"Maximum open trades reached for {pair}")
                else:
                    logging.warning(f"Insufficient free margin to place new trade for {pair}")

        except Exception as e:
            logging.error(f"Error trading {pair}: {e}")

def close_trades_logic():
    open_trades = get_open_trades()
    for trade in open_trades:
        try:
            profit_threshold = 100  # Adjust as needed
            loss_threshold = -50  # Adjust as needed
            maximum_holding_time = 3600  # 1 hour in seconds, adjust as needed

            if trade['profit'] >= profit_threshold or trade['loss'] <= loss_threshold:
                close_result = close_order(trade['order_id'])
                if close_result:
                    logging.info(f"Closed trade {trade['order_id']} due to profit/loss condition: {close_result}")
                else:
                    logging.error(f"Failed to close trade {trade['order_id']} due to profit/loss condition")

            current_time = time.time()
            holding_time = current_time - trade['open_time']
            if holding_time >= maximum_holding_time:
                close_result = close_order(trade['order_id'])
                if close_result:
                    logging.info(f"Closed trade {trade['order_id']} due to holding time condition: {close_result}")
                else:
                    logging.error(f"Failed to close trade {trade['order_id']} due to holding time condition")

        except Exception as e:
            logging.error(f"Error closing trade {trade['order_id']}: {e}")

def main():
    while True:
        try:
            logging.info("Starting main trading cycle.")
            main_trading_logic()
            logging.info("Main trading cycle completed. Starting trade closing logic.")
            close_trades_logic()
            logging.info("Trade closing logic completed. Sleeping for 60 seconds.")
            time.sleep(60)  # Sleep for 60 seconds before next cycle
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(60)  # Sleep for 60 seconds before retrying

if __name__ == "__main__":
    main()
