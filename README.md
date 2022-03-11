#  IBKR Options Bot
<p float="left">
  <img src="./static/IBKR.png"/>
  <img src="./static/Trading View.png"  height="180"/>
</p>


 Automated tradeing bot using the [Interactive Brokers platform](https://www.interactivebrokers.com/en/home.php) to trade options on different assets using EMA and VWAP indicators from Trading View.


[![Build Status](https://img.shields.io/travis/com/jacebrowning/template-python.svg)](https://travis-ci.com/jacebrowning/template-python)

## Usage


```
- Change TWS API configurations
```
![api_conf](./static/api_conf.png?raw=true)

```
$ cd <github_repo>
$ docekr run -d -p 6379:6379 redis
$ python3 venv bot
$ source bot/bin/activate
$ pip3 install -r requirements.txt
$ python3 broker.py
$ python3 server.py [gunicorn server:app --workers 4 --bind localhost:5000 --access-logfile access_log.txt --error-logfile error_log.txt]

$ngrok http 5000

```

## Setup the webhook adress in Trading View 
```
<ngrok_URL>/webhook
```
