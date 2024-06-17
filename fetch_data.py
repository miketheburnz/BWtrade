import os
import requests
import pandas as pd

ALPHA_VANTAGE_API_KEY = 'ZUMOLG9LWUIQ3C60'
currency_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURNZD', 'GBPAUD', 'GBPCAD', 'GBPNZD', 'AUDCAD', 'AUDCHF', 'AUDNZD', 'CADCHF', 'CADJPY', 'NZDJPY', 'NZDCHF', 'USDRUB', 'USDZAR', 'USDSGD', 'USDHKD', 'USDTRY', 'USDSEK', 'USDDKK', 'USDNOK', 'USDPLN', 'USDMXN', 'USDCNH', 'USDHUF', 'USDTHB', 'USDILS', 'USDCLP', 'USDCOP', 'USDBRL', 'USDKRW', 'USDINR', 'USDIDR', 'USDPHP', 'USDMYR', 'USDVND']

def fetch_data(pair):
    from_symbol, to_symbol = pair[:3], pair[3:]
    url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&apikey={ALPHA_VANTAGE_API_KEY}'

    response = requests.get(url)
    data = response.json()

    if 'Time Series FX (Daily)' not in data:
        print(f"Error fetching data for {pair}: {data}")
        return None

    df = pd.DataFrame.from_dict(data['Time Series FX (Daily)'], orient='index')
    df = df.rename(columns={
        '1. open': 'Open',
        '2. high': 'High',
        '3. low': 'Low',
        '4. close': 'Close'
    })
    df.to_csv(f'data/historical_data_{pair}.csv')
    return df

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

for pair in currency_pairs:
    fetch_data(pair)
