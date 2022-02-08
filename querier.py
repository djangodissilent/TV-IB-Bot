import requests
from time import sleep

while True:
    sleep(1)
    try:
        ret = requests.post(url='http://localhost:5000/webhook', json={'curPrice': '12', 'symbol': 'SPY', 'right': 'C'})
        print(ret.text)
    except: pass


# I'm also thinking of adding the functionality to create a seperate processs using Redis to handle the orders placements aside from the main server process, this will be necessary to free the server to only handle the webhook requests.

# I think that we would need to add a seperate worker to handle the order placements and free the server to handle the incoming webhook request from TV.