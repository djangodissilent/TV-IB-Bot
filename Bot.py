from datetime import datetime
from sanic import Sanic
from sanic import response
import asyncio
import ast
import datetime
from ib_insync import *
import random
from decimal import Decimal
import math
from pytz import timezone

from strategy import *

app = Sanic(__name__)
ib = IB()
orderPlacer = OrderPlacer(ib)


@app.route('/webhook', methods=['POST'])
async def webhook(request):
    print(request)
    if request.method != 'POST':
        return response.json({'error': 'Invalid request method'}, status=400)

    await checkIfReconnect(ib)
    data = request.json
    print(data)
    childrenTrades = orderPlacer.place_orders(
        stock_price=data['stock_price'], symbol=data['symbol'], right=data['right'],)
    return response.json({'status': 'success', 'childrenTrades': childrenTrades}, status=200)


@app.route('/')
async def root(request):
    return response.html(body='<h1>Bot is online ... 🤖</h1>')


async def checkIfReconnect(ib):
    """
    Check if the connection is still alive

    Args:
        ib (IB): ib object
    """
    print((datetime.datetime.now().strftime("%b %d %H:%M:%S")) +
          " Checking if we need to reconnect")
    if not ib.isConnected() or not ib.client.isConnected():
        try:
            print((datetime.datetime.now().strftime(
                "%b %d %H:%M:%S")) + " Reconnecting")
            ib.disconnect()
            ib = IB()
            ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
            orderPlacer.ib = ib
            print((datetime.datetime.now().strftime(
                "%b %d %H:%M:%S")) + " Reconnect Success")
        except Exception as e:
            print((datetime.datetime.now().strftime(
                "%b %d %H:%M:%S")) + " : " + str(e))


if __name__ == '__main__':
    print((datetime.datetime.now().strftime(
        "%b %d %H:%M:%S")) + " Connecting to IB")
    ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
    print((datetime.datetime.now().strftime("%b %d %H:%M:%S")) +
          " Successfully Connected to IB")

    serverPort = 5000
    app.run(port=serverPort, debug=True)
