import redis
import json
import time
import random

from ib_insync import *
import asyncio

from strategy import OrderPlacer

# connect to redis server and create a new instance of the redis client
redisClient = redis.Redis(host='localhost', port=6379, db=0)
# create a pub/sub client and subscripe to the TV channel
pubSubClient = redisClient.pubsub()
pubSubClient.subscribe('TradingView')

TRIAL_MODE = True


async def check_messages():
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} - Checking for Trading View alerts...')
    mes = pubSubClient.get_message()
    if mes and mes['type'] == 'message':
        print(mes)
        data = json.loads(mes['data'])

        try:
            ib = IB()
            await ib.connectAsync('127.0.0.1', 7497, clientId=random.randint(0, 9999))
            op = OrderPlacer(ib=ib, trial=TRIAL_MODE)
            await op.place_orders(stock_price=float(data['stock_price']), symbol=data['symbol'], right=data['right'])
        except Exception as e:
            print(e)
            print('Error in placing orders')
            ib.disconnect()


async def run_periodicallly(interval, func):
    while True:
        await asyncio.gather(asyncio.sleep(delay=interval), func())


event_loop = asyncio.get_event_loop()
polling_interval = 1
event_loop.run_until_complete(
    future=run_periodicallly(interval=polling_interval, func=check_messages))
