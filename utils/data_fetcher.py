import yfinance as yf
import pandas as pd
import talib
from textblob import TextBlob
import requests
import numpy as np
from utils.logger import setup_logging

logger = setup_logging('data_fetcher.log')

def fetch_market_data(pair):
    try:
        data = yf.download(pair + "=X", period="1mo", interval="1h")
        if data.empty:
            logger.error(f"Error fetching market data for {pair}")
            return None
        return get_technical_indicators(data)
    except Exception as e:
        logger.error(f"Error fetching market data for {pair}: {e}")
        return None

def get_technical_indicators(data):
    data['SMA'] = talib.SMA(data['Close'], timeperiod=14)
    data['EMA'] = talib.EMA(data['Close'], timeperiod=14)
    data['MACD'], data['MACD_signal'], data['MACD_hist'] = talib.MACD(data['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    data['RSI'] = talib.RSI(data['Close'], timeperiod=14)
    data['BB_upper'], data['BB_middle'], data['BB_lower'] = talib.BBANDS(data['Close'], timeperiod=14, nbdevup=2, nbdevdn=2, matype=0)
    data['ATR'] = talib.ATR(data['High'], data['Low'], data['Close'], timeperiod=14)
    return data

def fetch_sentiment_analysis(pair):
    try:
        url = f'https://newsapi.org/v2/everything?q={pair}&apiKey=YOUR_NEWSAPI_KEY'
        response = requests.get(url)
        articles = response.json().get('articles', [])
        sentiment_scores = [TextBlob(article['title']).sentiment.polarity for article in articles]
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
        return avg_sentiment
    except Exception as e:
        logger.error(f"Error fetching sentiment data for {pair}: {e}")
        return 0
