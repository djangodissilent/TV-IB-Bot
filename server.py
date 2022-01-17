import requests

req = requests.post('https://0960-41-232-63-210.ngrok.io/webhook', json={'symbol': 'BTCUSD'})
print(req.text)

{"message":"Test message", "ticker":"{{ticker}}"}