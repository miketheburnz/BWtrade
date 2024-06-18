from flask import Flask, request, jsonify
import psycopg2
import json

app = Flask(__name__)

# PostgreSQL connection details
DB_CONFIG = {
    "dbname": "your_dbname",
    "user": "your_username",
    "password": "your_password",
    "host": "localhost",
    "port": 5432
}

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/get_config', methods=['GET'])
def get_config():
    key = request.args.get('key')
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = %s", (key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return jsonify({"value": result[0]})
    else:
        return jsonify({"error": "Key not found"}), 404

@app.route('/set_config', methods=['POST'])
def set_config():
    data = request.json
    key = data['key']
    value = data['value']
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, value))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/log_trade', methods=['POST'])
def log_trade():
    data = request.json
    pair = data['pair']
    volume = data['volume']
    price = data['price']
    action = data['action']
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO trades (pair, volume, price, action, timestamp) VALUES (%s, %s, %s, %s, NOW())", (pair, volume, price, action))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/fetch_trades', methods=['GET'])
def fetch_trades():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades")
    result = cursor.fetchall()
    conn.close()
    trades = []
    for row in result:
        trades.append({
            "pair": row[0],
            "volume": row[1],
            "price": row[2],
            "action": row[3],
            "timestamp": row[4]
        })
    return jsonify({"trades": trades})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
