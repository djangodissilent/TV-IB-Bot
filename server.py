from flask import Flask, Response, request

import random
import redis
import math
import strategy

import config

app = Flask(__name__)
redisClient = redis.Redis(host='localhost', port=6379, db=0)


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method != 'POST':
        return response.json({'error': 'Invalid request method'}, status=400)

    print(request.data)
    data = request.data
    numberOfRecievers = redisClient.publish('TradingView', data)

    return {'status': 'Success'} if numberOfRecievers != 0 else {'status': 'Failure'}


@app.get("/")
def hello():
    return '<h4>Bot is online 🟢</h4>'


if __name__ == '__main__':
    serverPort = config.config['server_port']
    app.run(port=serverPort, debug=True)
