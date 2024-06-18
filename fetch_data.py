import os
import yfinance as yf
import pandas as pd

currency_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURNZD', 'GBPAUD', 'GBPCAD', 'GBPNZD', 'AUDCAD', 'AUDCHF', 'AUDNZD', 'CADCHF', 'CADJPY', 'NZDJPY', 'NZDCHF', 'USDRUB', 'USDZAR', 'USDSGD', 'USDHKD', 'USDTRY', 'USDSEK', 'USDDKK', 'USDNOK', 'USDPLN', 'USDMXN', 'USDCNH', 'USDHUF', 'USDTHB', 'USDILS', 'USDCLP', 'USDCOP', 'USDBRL', 'USDKRW', 'USDINR', 'USDIDR', 'USDPHP', 'USDMYR', 'USDVND']

def fetch_data(pair):
    pair_yahoo = pair + "=X"
    data = yf.download(pair_yahoo, period="1mo", interval="1h")
    if data.empty:
        print(f"Error fetching data for {pair}")
        return None
    data = data.rename(columns={
        'Open': 'Open',
        'High': 'High',
        'Low': 'Low',
        'Close': 'Close'
    })
    data.to_csv(f'data/historical_data_{pair}.csv')
    return data

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

for pair in currency_pairs:
    fetch_data(pair)
