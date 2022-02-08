import redis
import json
import time
import random

from ib_insync import *
import asyncio
import multiprocessing

from strategy import OrderPlacer


ib = IB()
ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
op = OrderPlacer(ib=ib)

# connect to redis server and create a new instance of the redis client
redisClient = redis.Redis(host='localhost', port=6379, db=0)
# create a pub/sub client and subscripe to the TV channel
pubSubClient = redisClient.pubsub()
pubSubClient.subscribe('TradingView')


async def check_messages():
    print(f'{time.time()} - Checking for Trading View messages')
    mes = pubSubClient.get_message()
    if mes and mes['type'] == 'message':
        print(mes)
        data = json.loads(mes['data'])
        # place the orders
        # run the place order in a different process


        await op.place_orders(curPrice=float(data['curPrice']), symbol=data['symbol'], right=data['right'])


async def run_periodicallly(interval, func):
    while True:
        await asyncio.gather(asyncio.sleep(delay=interval), func())


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(future=run_periodicallly(interval=1, func=check_messages))

