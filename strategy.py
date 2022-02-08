# https://github.com/ppratikcr7/AlgoTradeBot_IB/blob/master/algoTradingBot_IB_3min.py
# https://groups.io/g/insync/message/5632
# https://groups.io/g/twsapi/topic/tws_api_child_order_questions/4045949?p=

from ib_insync import *
import datetime
import random
from decimal import Decimal
import math
from pytz import timezone
import asyncio


class OrderPlacer:
    def __init__(self, ib) -> None:
        self.ib = ib

    def round_nearest(self, num: float, to: float) -> float:
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

    def calculate_price(self, avgFillPrice: float, percentage: int, minTick: float) -> float:
        """
        Calculate the price based on the average fill price and the percentage

        Args:
            avgFillPrice (float): Average fill price for the trade
            percentage (int): Percentage to be added (plus or minus) to the price
            minTick (float): Minimum tick size for the underlying contract

        Returns:
            float: modified price based on the percentage
        """
        return self.round_nearest(avgFillPrice + avgFillPrice * (percentage/100), minTick)

    async def get_contract_details(self, curPrice: float = None, symbol: str = 'SPY', right: str = 'C') -> ContractDetails:
        """
        Get the closest to the money options contract

        Args:
            curPrice (float): Current stock price
            right (str): Direction of the contract

        Returns:
            Contract: ContractDetails
        """
        curPrice = 448.7 if curPrice is None else curPrice
        cur_month = datetime.datetime.now(
            tz=timezone('US/Eastern')).strftime(format='%Y%m')
        contract = Option(symbol=symbol, exchange='SMART', right=right,
                          currency='USD', lastTradeDateOrContractMonth=cur_month, includeExpired=False)
        contracts = await self.ib.reqContractDetailsAsync(contract)

        aSecondBeforeMidnight = 86340  # 23:59:40
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

    async def get_tickers(self, contract: Contract) -> Ticker:
        """
        Get the ticker for the contract
        keep asking for the ticker until it is available, not nan

        Args:
            contract (Contract): Contract to get the ticker for

        Returns:
            Ticker: Ticker for the contract
        """
        tickers = await self.ib.reqTickersAsync(contract)
        while math.isnan(tickers[0].ask):
            await asyncio.sleep(0.01)
            tickers = await self.ib.reqTickersAsync(contract)
        return tickers

    async def place_orders(self, curPrice: float, symbol='SPY', right: str = 'C', quantity: int = 1, parentLimitPercent: int = 5, stopLossPercent: int = 60, takeProfitPercent: int = 40) -> list[Order]:
        """
        - Make a bracket order with (defualt +5%) parent limit order
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

        contractDetail = await self.get_contract_details(
            curPrice=curPrice, symbol=symbol, right=right)
        contract = contractDetail.contract
        minTick = contractDetail.minTick
        quant = quantity

        # get the current ask for the contract to calculate
        # - limit order (ask + (ask)* parentLimitPercent%)
        limitPercent = parentLimitPercent
        self.ib.reqMarketDataType(marketDataType=4)  # chage to 1 at production

        tickers = await self.get_tickers(contract)
        lmtPrice = self.calculate_price(tickers[0].ask, limitPercent, minTick)
        initialTakeProfit = self.calculate_price(
            lmtPrice, takeProfitPercent, minTick)
        initialStopLoss = self.calculate_price(
            lmtPrice, -stopLossPercent, minTick)

        parentOrder = LimitOrder('BUY', transmit=False,
                                 lmtPrice=lmtPrice, totalQuantity=quant)
        parentTrade = self.ib.placeOrder(contract, parentOrder)

        profitTaker = LimitOrder(
            'SELL', quant, initialTakeProfit,
            orderId=self.ib.client.getReqId(),
            transmit=False,
            parentId=parentTrade.order.orderId)
        stopLoss = StopOrder(
            'SELL', quant, initialStopLoss,
            orderId=self.ib.client.getReqId(),
            transmit=True,
            parentId=parentTrade.order.orderId)

        for ord in [profitTaker, stopLoss]:
            self.ib.placeOrder(contract, ord)

        while not parentTrade.isDone():
            await asyncio.sleep(0.01)

        # modify the children orders based on avg fill price
        averageFillPrice = parentTrade.orderStatus.avgFillPrice
        takeProfitPrice = self.calculate_price(
            averageFillPrice, takeProfitPercent, minTick)
        stopLossPrice = self.calculate_price(
            averageFillPrice, -stopLossPercent, minTick)
        profitTaker.lmtPrice = takeProfitPrice
        stopLoss.lmtPrice = stopLossPrice
        profitTaker.transmit = True
        stopLoss.transmit = True

        childrenTrades = []
        for order in [profitTaker, stopLoss]:
            childrenTrades.append(self.ib.placeOrder(contract, order))

        return childrenTrades


def main(data):
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
    op = OrderPlacer(ib=ib)
    print(data)

    DEFUALT_PRICE = None
    DEFUALT_SYMBOL = 'SPY'
    DEFUALT_RIGHT = 'C'
    DEFUALT_QUANTITY = 1
    DEFUALT_PARENT_LIMIT_PERCENT = 5
    DEFUALT_STOP_LOSS_PERCENT = 60
    DEFUALT_TAKE_PROFIT_PERCENT = 40

    curPrice = DEFUALT_PRICE if 'curPrice' not in data else data['curPrice']
    symbol = DEFUALT_SYMBOL if 'symbol' not in data else data['symbol']
    right = DEFUALT_RIGHT if 'right' not in data else data['right']
    quantity = DEFUALT_QUANTITY if 'quantity' not in data else data['quantity']
    parentLimitPercent = DEFUALT_PARENT_LIMIT_PERCENT if 'parentLimitPercent' not in data else data[
        'parentLimitPercent']
    stopLossPercent = DEFUALT_STOP_LOSS_PERCENT if 'stopLossPercent' not in data else data[
        'stopLossPercent']
    takeProfitPercent = DEFUALT_TAKE_PROFIT_PERCENT if 'takeProfitPercent' not in data else data[
        'takeProfitPercent']

    trades = op.place_orders(curPrice, symbol, right, quantity,
                             parentLimitPercent, stopLossPercent, takeProfitPercent)

    ib.disconnect()


# ib = IB()
# ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
# op = OrderPlacer(ib=ib)
# op.place_orders(curPrice=441.78, symbol='SPY', right='C', quantity=1,
#                 parentLimitPercent=5, stopLossPercent=60, takeProfitPercent=40)

# ib.disconnect()
