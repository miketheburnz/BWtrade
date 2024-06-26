import MetaTrader5 as mt5
import logging
import os
import pandas as pd
from yfinance import download
from utils.logger import setup_logging

logger = setup_logging('data_fetcher.log')

def initialize_mt5():
    if not mt5.initialize():
        logger.error("initialize() failed, error code = %s", mt5.last_error())
        return False
    return True

def get_account_state():
    account_info = mt5.account_info()
    if account_info is None:
        logger.error("Failed to get account info, error code = %s", mt5.last_error())
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
        logger.error("Failed to get open positions, error code = %s", mt5.last_error())
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
        logger.error(f"Failed to get symbol info for {pair}, error code = %s", mt5.last_error())
        return None
    if not symbol_info.visible:
        if not mt5.symbol_select(pair, True):
            logger.error(f"Failed to select symbol {pair}, error code = %s", mt5.last_error())
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
        logger.error(f"Failed to place order, error code = %s", mt5.last_error())
        return None
    return result

def close_order(order_id):
    position = mt5.positions_get(ticket=order_id)
    if position is None or len(position) == 0:
        logger.error(f"Failed to find position with ticket {order_id}, error code = %s", mt5.last_error())
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
        logger.error(f"Failed to close order, error code = %s", mt5.last_error())
        return None
    return result

def execute_trades(models, currency_pairs, account_state):
    equity = account_state['equity']
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
                trend = data['SMA'].iloc[-1] > data['EMA'].iloc[-1]
                volatile = data['ATR'].iloc[-1] > data['ATR'].mean() * 1.5
                if sentiment_score > 0 and trend and not volatile:
                    trade_direction = 'buy' if prediction > 0.5 and xgb_prediction > 0.5 else 'sell'
                else:
                    trade_direction = 'sell' if prediction > 0.5 and xgb_prediction > 0.5 else 'buy'
                lot_size = (equity * 0.01) / 100000
                lot_size = max(min(lot_size, 100), 0.01)
                if account_state['free_margin'] > lot_size * 100000 / 50:
                    open_trades = get_open_trades()
                    if len(open_trades) < 5:
                        order_result = place_order(pair, trade_direction, lot_size)
                        if order_result:
                            logger.info(f"Placed {trade_direction} order for {pair} with lot size {lot_size}: {order_result}")
                        else:
                            logger.error(f"Failed to place {trade_direction} order for {pair} with lot size {lot_size}")
                    else:
                        logger.warning(f"Maximum open trades reached for {pair}")
                else:
                    logger.warning(f"Insufficient free margin to place new trade for {pair}")
        except Exception as e:
            logger.error(f"Error trading {pair}: {e}")
        time.sleep(5)

def close_open_trades():
    open_trades = get_open_trades()
    for trade in open_trades:
        try:
            if trade['profit'] >= 100 or trade['loss'] <= -50:
                close_order(trade['order_id'])
                logger.info(f"Closed trade {trade['order_id']} due to profit/loss condition")
            current_time = time.time()
            holding_time = current_time - trade['open_time']
            if holding_time >= 3600:
                close_order(trade['order_id'])
                logger.info(f"Closed trade {trade['order_id']} due to holding time condition")
        except Exception as e:
            logger.error(f"Error closing trade {trade['order_id']}: {e}")
