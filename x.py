import datetime
from ib_insync import *
import datetime

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)


cur_month = datetime.datetime.now().strftime(format='%Y%m')

contract = Option(symbol='SPY', exchange='SMART', currency='USD',lastTradeDateOrContractMonth=cur_month)

contracts = ib.reqContractDetails(contract)

with open ('contracts.txt', 'w') as f:
    f.write(str(len(contracts)) + '\n')
    l = []

    for c in contracts:
        l.append(str(c.contract.strike) + '\n' )
    for x in sorted(l):
        f.write(x)

nextExpiryDate = min(contracts, key=lambda x: x.realExpirationDate).realExpirationDate

nextExpiryContracts = list(filter(lambda con: con.realExpirationDate == nextExpiryDate, contracts))

# getting the stock price
curStockPice = 471.0

closestTotheMoney = sorted(nextExpiryContracts, key=lambda conDet: (abs(conDet.contract.strike - curStockPice) ,conDet.contract.strike ))[0]

import pandas as pd
# turn the contract into a dataframe
df = pd.DataFrame(closestTotheMoney.contract.__dict__.items(), columns=['key', 'value'])

# write it to csv
df.to_csv('contract.csv')
print(df)
ib.disconnect()