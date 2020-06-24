import pandas as pd
# from plotly.graph_objs import Scatter, Layout, Figure
# import plotly
from okexAPI import *
# from datetime import datetime
# import numpy as np
# from scipy.stats import norm
# import time
# from deribit import *
# import urllib.request


#
# START = 7000
# END = 13000
# INTERVAL = 10
# RANGE = range(START, END, INTERVAL)
# SPOT_PRICE_RANGE = pd.Series(RANGE)
# FEE = 0.0008 #buffered. Actual (taker) fee: 0.0005
#

# init Okex API

apiKey = open('api.key', 'r').read()
otherKey = open('other.key', 'r').read()
ppKey = open('pp.key', 'r').read()

OK =  Okex(apiKey, otherKey, ppKey, '')


def getOptionStrikes_okex(date):

    yr = str(date.year)[-2:]
    mth = str(date.month)
    if len(mth) == 1:
        mth = '0' + mth
    day = str(date.day)
    if len(day) == 1:
        day = '0' + day

    date = yr+mth+day

    r = OK.optionStrikes(date)

    strikes = []

    for each in r:
        id = each['instrument_id']
        # print(id)
        st = id[15:-2]
        st = int(st)
        if st not in strikes:
            strikes.append(st)
    strikes.sort()

    return strikes

def getOptionData(date, strike, callPut):

    yr = str(date.year)[-2:]
    mth = str(date.month)
    if len(mth) == 1:
        mth = '0' + mth
    day = str(date.day)
    if len(day) == 1:
        day = '0' + day

    date = yr+mth+day
    strike = str(int(strike))


    r = OK.options(date, strike, callPut)

    ask = 0
    bid = 0
    delta = 0

    if r['best_ask'] !='':
        ask = float(r['best_ask'])
    if r['best_bid'] != '':
        bid  = float(r['best_bid'])
    if r['delta'] != '':
        delta = float(r['delta'])



    return ask, bid, delta


def getCandles(instrument, granularity = TimeFrame.H1,
               start=None, end = None):

    res = OK.get_candles(instrument, granularity, start_time=start, end_time=end)

    candles = pd.DataFrame(res, columns = ['time', 'open','high','low','close','vol'])

    candles['time'] = pd.to_datetime(candles['time'])
    candles['open'] = pd.to_numeric(candles['open'])
    candles['high'] = pd.to_numeric(candles['high'])
    candles['low'] = pd.to_numeric(candles['low'])
    candles['close'] = pd.to_numeric(candles['close'])
    candles['vol'] = pd.to_numeric(candles['vol'])
    return candles

def okex_getSpot():
    res = OK.get_ticker('BTC-USDT')

    return float(res['last'])




# if __name__ == '__main__':
#
#     # print(getT(datetime(2020,5,15,8)))
#
#     spot = getSpot()
#
#     spacing = 5
#     skRange = list(range(8500,10001, 250))
#     skRange += [10250,10500,10750,11000,11500,12000,12500]
#
#
#
#     for i in range(len(skRange)):
#         print()
#         print('-----------------------------------')
#
#         if (i+2+spacing) >= len(skRange):
#             break
#
#         sk1 = skRange[i]
#         sk3 = skRange[i+1]
#         sk4 = skRange[i+1+spacing]
#         sk2 = skRange[i+1+spacing+1]
#
#         condor(sk1,sk2,sk3,sk4,bUnits=0.5,spot=spot)















