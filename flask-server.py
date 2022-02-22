from flask import Flask, Response, request

import random
import redis
import math
import strategy


app = Flask(__name__)
redisClient = redis.Redis(host='localhost', port=6379, db=0)


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method != 'POST':
        return response.json({'error': 'Invalid request method'}, status=400)

    print(request.data)
    data = request.data
    numberOfRecievers = redisClient.publish('TradingView', data)

    return {'status': 'Success'} if numberOfRecievers else {'status': 'Failure'}


@app.get("/")
def hello():
    return '<h6>Bot is online 🟢</h6>'


if __name__ == '__main__':
    serverPort = 5000
    app.run(host='localhost', port=serverPort, debug=True)
