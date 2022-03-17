import requests
from time import sleep
import config

ret = requests.post(url=f'http://localhost:{config.config["server_port"]}/webhook',json={'stock_price': '451', 'symbol': 'SPY', 'right': 'C'})
print(ret.text)
