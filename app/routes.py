from flask import render_template, request, redirect
from app import app
import sqlite3

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/configure', methods=['POST'])
def configure():
    api_key = request.form['apiKey']
    currency_pairs = request.form['currencyPairs']
    trade_volume = request.form['tradeVolume']
    stop_loss = request.form['stopLoss']
    take_profit = request.form['takeProfit']

    conn = sqlite3.connect('logs/config.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Config (
            apiKey TEXT,
            currencyPairs TEXT,
            tradeVolume REAL,
            stopLoss REAL,
            takeProfit REAL
        )
    ''')
    cursor.execute('DELETE FROM Config')
    cursor.execute('''
        INSERT INTO Config (apiKey, currencyPairs, tradeVolume, stopLoss, takeProfit)
        VALUES (?, ?, ?, ?, ?)
    ''', (api_key, currency_pairs, trade_volume, stop_loss, take_profit))
    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/logs')
def logs():
    conn = sqlite3.connect('logs/trades.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TradeLogs")
    logs = cursor.fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)
