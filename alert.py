import requests
from time import sleep


ret = requests.post(url='http://localhost:5000/webhook',json={'stock_price': '451', 'symbol': 'SPY', 'right': 'C'})
print(ret.text)
