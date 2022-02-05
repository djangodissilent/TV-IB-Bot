from datetime import datetime
from sanic import Sanic
from sanic import response
import asyncio
import ast
import datetime
from ib_insync import *
import random

app = Sanic(__name__)
ib = IB()


@app.route('/')
async def root(request):
    return response.text('Bot is online ... 🤖')


async def create_braket_order(contract, amount, limit, takeprofit, stoploss):
    bracket = ib.bracketOrder('BUY', amount, limit,
                              takeprofit, stoploss, outsideRth=True)

    gtddelta = (datetime.now() + timedelta(seconds=45)
                ).strftime("%Y%m%d %H:%M:%S")
    bracket.parent.tif = 'GTD'
    bracket.parent.goodTillDate = gtddelta

    for order in bracket:
        ib.placeOrder(contract, order)


async def get_contracts():
    cur_month = datetime.datetime.now().strftime(format='%Y%m')

    contract = Option(symbol='SPY', exchange='SMART',
                      currency='USD', lastTradeDateOrContractMonth=cur_month)

    contracts = ib.reqContractDetails(contract)
    nextExpiryDate = min(
        contracts, key=lambda x: x.realExpirationDate).realExpirationDate

    nextExpiryContracts = list(filter(lambda con: con.realExpirationDate ==
                               nextExpiryDate and con.contract.right == 'C', contracts))

    # getting the stock price will be sent in the req
    curStockPice = 457.78

    closestTotheMoney = sorted(nextExpiryContracts, key=lambda conDet: (
        abs(conDet.contract.strike - curStockPice), conDet.contract.strike))[0]

    return closestTotheMoney


async def checkIfReconnect(ib):
    print((datetime.datetime.now().strftime("%b %d %H:%M:%S")) +
          " Checking if we need to reconnect")
    # Reconnect if needed
    if not ib.isConnected() or not ib.client.isConnected():
        try:
            print((datetime.datetime.now().strftime(
                "%b %d %H:%M:%S")) + " Reconnecting")
            ib.disconnect()
            ib = IB()
            ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
            ib.errorEvent += onError
            print((datetime.datetime.now().strftime(
                "%b %d %H:%M:%S")) + " Reconnect Success")
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print("Make sure TWS or Gateway is open with the correct port")
            print((datetime.datetime.now().strftime(
                "%b %d %H:%M:%S")) + " : " + str(e))
    return ''


@app.route('/webhook', methods=['POST'])
async def webhook(request):
    print(request)
    if request.method == 'POST':
        # Check if we need to reconnect with IB
        await checkIfReconnect(ib)
        # Parse the string data from tradingview into a python dict
        data = request.json
        print(data)
        # Get the contract details
        contract = await get_contracts()

        # order = MarketOrder("BUY", 1, account=ib.wrapper.accounts[0])
        # print(data['symbol'])
        # print(data['symbol'][0:3])
        # print(data['symbol'][3:6])
        # # contract = Crypto(data['symbol'][0:3],'PAXOS',data['symbol'][3:6]) #Get first 3 chars BTC then last 3 for currency USD
        # # or stock for example
        # contract = Stock('SPY', 'SMART', 'USD')
        # print((datetime.datetime.now().strftime("%b %d %H:%M:%S")) +
        #       " Buying: " + str(data['symbol']))
        # ib.placeOrder(contract, order)
    return response.json({})
# On IB Error


def onError(self, reqId, errorCode, errorString, contract):
    print((datetime.datetime.now().strftime(
        "%b %d %H:%M:%S")) + " : " + str(errorCode))
    print((datetime.datetime.now().strftime(
        "%b %d %H:%M:%S")) + " : " + str(errorString))


if __name__ == '__main__':
    # IB Connection
    print((datetime.datetime.now().strftime(
        "%b %d %H:%M:%S")) + " Connecting to IB")
    ib.connect('127.0.0.1', 7497, clientId=random.randint(0, 9999))
    print((datetime.datetime.now().strftime("%b %d %H:%M:%S")) +
          " Successfully Connected to IB")
    ib.errorEvent += onError
    serverPort = 5000

    app.run(port=serverPort, debug=True)
