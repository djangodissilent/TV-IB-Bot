# https://github.com/ppratikcr7/AlgoTradeBot_IB/blob/master/algoTradingBot_IB_3min.py
# https://groups.io/g/insync/message/5632
# https://groups.io/g/twsapi/topic/tws_api_child_order_questions/4045949?p=

from ib_insync import *
import datetime
import random

from decimal import Decimal
import math


def round_nearest(num: float, to: float) -> float:
    """
    Round the nearest number to the nearest multiple of to
    """
    num, to = Decimal(str(num)), Decimal(str(to))
    return float(round(num / to) * to)


def calculate_price(avgFillPrice: float, percentage: int, minTick: float) -> float:
    """
    Calculate the price based on the average fill price and the percentage
    """
    return round_nearest(avgFillPrice + avgFillPrice * (percentage/100), minTick)


def get_contract(curStockPice: float = None):
    """
    Get the closest to the money options contract
    """
    cur_month = datetime.datetime.now().strftime(format='%Y%m')

    contract = Option(symbol='SPY', exchange='SMART', right='C',
                      currency='USD', lastTradeDateOrContractMonth=cur_month)

    contracts = ib.reqContractDetails(contract)

    expiringInFuture = list(filter(lambda con:  ((datetime.datetime.strptime(
        con.realExpirationDate, '%Y%m%d') + datetime.timedelta(0, 86340, 0)) - (datetime.datetime.now())).days >= 0, contracts))
    nextExpiryDate = min(
        expiringInFuture, key=lambda x: x.realExpirationDate).realExpirationDate
    nextExpiryContracts = list(filter(lambda con: con.realExpirationDate ==
                               nextExpiryDate, contracts))

    # getting the stock price will be sent in the req
    curStockPice = 441.78 if curStockPice is None else curStockPice

    closestTotheMoney = sorted(nextExpiryContracts, key=lambda conDet: (
        abs(conDet.contract.strike - curStockPice), conDet.contract.strike))[0]

    return closestTotheMoney


ib = IB()
ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))

contractDet = get_contract()
contract = contractDet.contract
minTick = contractDet.minTick

quant = 1  # how many contracts to buy

# get the current ask for the contract to calculate
# - limit order (ask + 5%)
# - take profit and stopt loss initial levels (inital limit +40% and -60%)

ib.reqMarketDataType(marketDataType=4)
tickers = ib.reqTickers(contract)

lmtPrice = calculate_price(tickers[0].askPrice, 5, minTick)
initialTakeProfit = calculate_price(lmtPrice, 40, minTick)
initialStopLoss = calculate_price(lmtPrice, -60, minTick)

order = LimitOrder('BUY', transmit=False,
                   lmtPrice=lmtPrice, totalQuantity=quant)
parentTrade = ib.placeOrder(contract, order)

profitTaker = LimitOrder(
    'SELL', quant, initialTakeProfit,
    orderId=ib.client.getReqId(),
    transmit=False,
    parentId=parentTrade.order.orderId)

stopLoss = StopOrder(
    'SELL', quant, initialStopLoss,
    orderId=ib.client.getReqId(),
    transmit=True,
    parentId=parentTrade.order.orderId)


childrenTredes = []
for ord in [profitTaker, stopLoss]:
    t = ib.placeOrder(contract, ord)
    childrenTredes.append(t)

# wait for parent to fill then modify the children orders
while not parentTrade.isDone():
    ib.sleep(0.1)

averageFillPrice = parentTrade.orderStatus.avgFillPrice
takeProfitPrice = calculate_price(averageFillPrice, 40, minTick)
stopLossPrice = calculate_price(averageFillPrice, -60, minTick)
profitTaker.lmtPrice = takeProfitPrice
stopLoss.lmtPrice = stopLossPrice
profitTaker.transmit = True
stopLoss.transmit = True

# modify the children orders
for order in [profitTaker, stopLoss]:
    t = ib.placeOrder(contract, order)
    childrenTredes.append(t)

ib.disconnect()
