from ib_insync import *
import datetime

ib = IB()
ib.connect('localhost', 7497, clientId=1)

stock = Stock('SPY', 'SMART', 'USD')
contract = Option(symbol='SPY', exchange='SMART', right='C',
                  currency='USD', lastTradeDateOrContractMonth='202202', includeExpired=False)
ret = ib.reqSecDefOptParams(
    stock.symbol, '', stock.secType, stock.conId)
ret = ib.reqContractDetails(contract)

print(ret)
