# https://github.com/ppratikcr7/AlgoTradeBot_IB/blob/master/algoTradingBot_IB_3min.py
# https://groups.io/g/insync/message/5632
# https://groups.io/g/twsapi/topic/tws_api_child_order_questions/4045949?p=

from ib_insync import *
import datetime
import random
from decimal import Decimal
import math
from pytz import timezone

class ExecutionStatus:
    """
    Execution status of the order
    """
    PendingSubmit = 'PendingSubmit'
    PendingCancel = 'PendingCancel'
    PreSubmitted = 'PreSubmitted'
    Submitted = 'Submitted'
    Cancelled = 'Cancelled'
    Filled = 'Filled'
    Inactive = 'Inactive'
    Expired = 'Expired'
    Rejected = 'Rejected'
    Suspended = 'Suspended'
    PendingReplace = 'PendingReplace'


def round_nearest(num: float, to: float) -> float:
    """
    Round the nearest number to the nearest multiple of to

    Args:
        num (float): Number to be rounded
        to (float): Number to be rounded to

    Returns:
        float: Rounded number

    """
    num, to = Decimal(str(num)), Decimal(str(to))
    return float(round(num / to) * to)


def calculate_price(avgFillPrice: float, percentage: int, minTick: float) -> float:
    """
    Calculate the price based on the average fill price and the percentage

    Args:
        avgFillPrice (float): Average fill price for the trade
        percentage (int): Percentage to be added (plus or minus) to the price
        minTick (float): Minimum tick size for the underlying contract

    Returns:
        float: modified price based on the percentage
    """
    return round_nearest(avgFillPrice + avgFillPrice * (percentage/100), minTick)


def get_contract_details(curPrice: float = None, symbol: str = 'SPY', right: str = 'C') -> ContractDetails:
    """
    Get the closest to the money options contract

    Args:
        curPrice (float): Current stock price
        right (str): Direction of the contract

    Returns:
        Contract: ContractDetails
    """
    curPrice = 441.78 if curPrice is None else curPrice
    cur_month = datetime.datetime.now(
        tz=timezone('US/Eastern')).strftime(format='%Y%m')
    contract = Option(symbol=symbol, exchange='SMART', right=right,
                      currency='USD', lastTradeDateOrContractMonth=cur_month)
    contracts = ib.reqContractDetails(contract)

    aSecondBeforeMidnight = 86340
    expiringInFuture = list(filter(lambda con:  ((datetime.datetime.strptime(
        con.realExpirationDate, '%Y%m%d') + datetime.timedelta(0, aSecondBeforeMidnight, 0)) - (datetime.datetime.now())).days >= 0, contracts))
    nextExpiryDate = min(
        expiringInFuture, key=lambda x: x.realExpirationDate).realExpirationDate
    nextExpiryContracts = list(filter(lambda con: con.realExpirationDate ==
                               nextExpiryDate, contracts))

    # get the closest contract to the money
    # - If tie and right is call, get the one with the lower strike price
    # - If tie and right is put, get the one with the higher strike price
    closestTotheMoney = sorted(nextExpiryContracts, key=lambda conDet: (
        abs(conDet.contract.strike - curPrice), conDet.contract.strike if right == 'C' else -conDet.contract.strike))[0]

    return closestTotheMoney



def place_orders(curPrice: float, symbol='SPY', right: str = 'C', quantity: int = 1, parentLimitPercent: int = 5, stopLossPercent: int = 60, takeProfitPercent: int = 40) -> ExecutionStatus:
    """
    - Make a brackt order with (defualt +5%) parent limit order
    - Modify children on fill based on avg fill of parent and (default +40%) take profit and (default -60%) stop loss percentages

    Args:
        curPrice (float): Current stock price
        symbol (str): Stock symbol
        right (str): Direction of the contract (CALL, PUT)
        quantity (int): Quantity to be bought
        stopLossPercent (int): Stop loss percentage
        takeProfitPercent (int): Take profit percentage
    Returns:
        status: ExecutionStatus
    """

    contractDetail = get_contract_details(
        curPrice=curPrice, symbol=symbol, right=right)
    contract = contractDetail.contract
    minTick = contractDetail.minTick
    quant = quantity

    # get the current ask for the contract to calculate
    # - limit order (ask + (ask)* parentLimitPercent%)
    limitPercent = parentLimitPercent
    ib.reqMarketDataType(marketDataType=4)  # chage to 1 at production
    tickers = ib.reqTickers(contract)
    lmtPrice = calculate_price(tickers[0].ask, limitPercent, minTick)
    initialTakeProfit = calculate_price(lmtPrice, takeProfitPercent, minTick)
    initialStopLoss = calculate_price(lmtPrice, -stopLossPercent, minTick)

    parentOrder = LimitOrder('BUY', transmit=False,
                             lmtPrice=lmtPrice, totalQuantity=quant)
    parentTrade = ib.placeOrder(contract, parentOrder)

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

    for ord in [profitTaker, stopLoss]:
        ib.placeOrder(contract, ord)

    while not parentTrade.isDone():
        ib.sleep(0.01)

    # modify the children orders based on avg fill price
    averageFillPrice = parentTrade.orderStatus.avgFillPrice
    takeProfitPrice = calculate_price(
        averageFillPrice, takeProfitPercent, minTick)
    stopLossPrice = calculate_price(
        averageFillPrice, -stopLossPercent, minTick)
    profitTaker.lmtPrice = takeProfitPrice
    stopLoss.lmtPrice = stopLossPrice
    profitTaker.transmit = True
    stopLoss.transmit = True

    childrenTrades = []
    for order in [profitTaker, stopLoss]:
        childrenTrades.append(ib.placeOrder(contract, order))

    return childrenTrades


ib = IB()
ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
place_orders(curPrice=441.78, symbol='SPY', right='C', quantity=1, parentLimitPercent=5, stopLossPercent=60, takeProfitPercent=40)

ib.disconnect()
