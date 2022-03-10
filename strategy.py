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
    def __init__(self, ib: IB, trial: bool) -> None:
        self.ib = ib
        self.trial = trial

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

    async def get_contract_details(self, stock_price: float = None, symbol: str = 'SPY', right: str = 'C') -> ContractDetails:
        """
        Get the closest to the money options contract

        Args:
            stock_price (float): Current stock price
            right (str): Direction of the contract

        Returns:
            Contract: ContractDetails
        """
        stock_price = stock_price
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

        if not nextExpiryContracts:
            raise Exception('No contract found')
        # get the closest contract to the money
        # - If tie and right is call, get the one with the lower strike price
        # - If tie and right is put, get the one with the higher strike price
        closestTotheMoney = sorted(nextExpiryContracts, key=lambda conDet: (
            abs(conDet.contract.strike - stock_price), conDet.contract.strike if right == 'C' else -conDet.contract.strike))[0]

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
        self.ib.reqMarketDataType(marketDataType=1 if not self.trial else 4)
        # data = self.ib.reqMktData(contract, '', True, False)
        tickers = await self.ib.reqTickersAsync(contract)
        if math.isnan(tickers[0].ask):
            raise Exception('Ticker is nan')
        return tickers

    async def place_orders(self, stock_price: float, symbol='SPY', right: str = 'C', quantity: int = 1, parentLimitPercent: int = 5, stopLossPercent: int = 60, takeProfitPercent: int = 40) -> None:
        """
        - Make a bracket order with (defualt +5%) parent limit order
        - Modify children on fill based on avg fill of parent and (default +40%) take profit and (default -60%) stop loss percentages

        Args:
            stock_price (float): Current stock price
            symbol (str): Stock symbol
            right (str): Direction of the contract (CALL, PUT)
            quantity (int): Quantity to be bought
            stopLossPercent (int): Stop loss percentage
            takeProfitPercent (int): Take profit percentage
        Returns:
            status: ExecutionStatus
        """

        contractDetail = await self.get_contract_details(
            stock_price=stock_price, symbol=symbol, right=right)
        contract = contractDetail.contract
        minTick = contractDetail.minTick
        quant = quantity

        # get the current ask for the contract to calculate
        # - limit order (ask + (ask)* parentLimitPercent%)
        limitPercent = parentLimitPercent
        # chage to 1 at production
        self.ib.reqMarketDataType(marketDataType=1 if not self.trial else 4)
        tickers = await self.get_tickers(contract)
        lmtPrice = self.calculate_price(tickers[0].ask, limitPercent, minTick)
        initialTakeProfit = self.calculate_price(
            lmtPrice, takeProfitPercent, minTick)
        initialStopLoss = self.calculate_price(
            lmtPrice, -stopLossPercent, minTick)

        initialStopLoss = max(initialStopLoss, minTick)

        print("Ask for the contract: ", tickers[0].ask)
        print("Initial LmtPrice +5%: ", lmtPrice)
        print("Initial Take Profit 40%: ", initialTakeProfit)
        print("Initial Stop Loss 60%: ", initialStopLoss)
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

        maxRetries = 500
        while not parentTrade.isDone() and maxRetries > 0:
            await asyncio.sleep(0.01)
            maxRetries -= 1

        if maxRetries == 0:
            raise Exception('Parent order timed out')

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

        print("Avg Fill Price: ", averageFillPrice)
        print("Take Profit Price: ", takeProfitPrice)
        print("Stop Loss Price: ", stopLossPrice)
        for order in [profitTaker, stopLoss]:
            self.ib.placeOrder(contract, order)

        return None
