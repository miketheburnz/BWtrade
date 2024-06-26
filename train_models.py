import os
import numpy as np
import pandas as pd
from keras.models import Sequential
from keras.layers import Input, LSTM, Dense
from utils.logger import setup_logging

currency_pairs = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY",
    "GBPJPY", "AUDJPY", "CHFJPY", "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPCAD", "GBPNZD",
    "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY", "NZDJPY", "NZDCHF", "USDRUB", "USDZAR",
    "USDSGD", "USDHKD", "USDTRY", "USDSEK", "USDDKK", "USDNOK", "USDPLN", "USDMXN", "USDCNH",
    "USDHUF", "USDTHB", "USDILS", "USDCOP", "USDBRL", "USDKRW", "USDINR", "USDIDR",
    "USDPHP", "USDMYR", "USDVND"
]

logger = setup_logging('train_models.log')

def create_dataset(data, look_back=1):
    X, Y = [], []
    for i in range(len(data) - look_back):
        a = data[i:(i + look_back), 0]
        X.append(a)
        Y.append(data[i + look_back, 0])
    return np.array(X), np.array(Y)

for pair in currency_pairs:
    try:
        df = pd.read_csv(f'data/historical_data/{pair}.csv')
        df['Close'] = df['Close'].astype(float)

        dataset = df['Close'].values
        dataset = dataset.reshape(-1, 1)
        look_back = 10
        X, Y = create_dataset(dataset, look_back)

        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        Y_train, Y_test = Y[:train_size], Y[train_size:]

        X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

        model = Sequential()
        model.add(Input(shape=(look_back, 1)))
        model.add(LSTM(50, return_sequences=True))
        model.add(LSTM(50))
        model.add(Dense(1))
        model.compile(loss='mean_squared_error', optimizer='adam')

        model.fit(X_train, Y_train, epochs=20, batch_size=1, verbose=2)

        model_path = f'models/lstm_model_{pair}.keras'
        model.save(model_path)
        logger.info(f"Model for {pair} saved at {model_path}")

    except Exception as e:
        logger.error(f"Error processing {pair}: {e}")
