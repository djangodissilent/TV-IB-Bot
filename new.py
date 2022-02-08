import pandas as pd
from ib_insync import IB, Forex, Contract, Index, util
from ib_insync.ibcontroller import IBC, Watchdog
import os.path
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

util.patchAsyncio()
util.logToFile("df.log")


async def tick_10(c):
    print('Tick! The time for the 10 second job is: {}'.format(datetime.datetime.now()))
    if not app.ib.isConnected():
        pass
    else:
        bars = app.ib.reqHistoricalData(c,
                                endDateTime=pd.to_datetime("2018-04-01"),
                                durationStr='1 D',
                                barSizeSetting='1 min',
                                whatToShow='MIDPOINT',
                                formatDate=2,
                                useRTH=True)
        df = util.df(bars)
        if not df is None:
            print(df.tail().loc[:,["date","close"]])


scheduler = AsyncIOScheduler()

ibc = IBC(970, gateway=True, tradingMode='paper',ibcIni='/home/bn/ibc/configPaper.ini')
# start and run gateway
app = Watchdog(ibc, appStartupTime=15,host='127.0.0.1',port=4002,clientId=11)
app.start()

# define a contract
c = app.ib.qualifyContracts(Forex('EURUSD'))[0]

# define a scheduled task
scheduler.add_job(tick_10, args=[c],trigger='cron', minute='*',second='*/10')
scheduler.start()
print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
# Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
try:
    asyncio.get_event_loop().run_forever()
except (KeyboardInterrupt, SystemExit):
    pass
