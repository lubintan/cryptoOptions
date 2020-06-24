import pandas as pd
from plotly.graph_objs import Scatter, Layout, Figure
import plotly
import numpy as np
from scipy.stats import norm
import time
from deribit import *
from okex import *
import forecast
# from okexAPI import *

START = 2000
END = 35000
INTERVAL = 10
RANGE = range(START, END, INTERVAL)
SPOT_PRICE_RANGE = pd.Series(RANGE)
FEE = None
OKEX_FEE_RATE = 0.0008
DERIBIT_FLAT_FEE_IN_BTC = 0.001
# OKEx = 0.0008 #buffered. Actual (taker) fee: 0.0005
# deribit = 12.5%.


def longCall(strike, units, pUSD, pBTC=None, currentBTC=None, feeRate = 0.0004):
    if pBTC == None:
        optionPrice = pUSD
    else:
        optionPrice = pBTC * currentBTC

    FEE = units * feeRate * currentBTC

    profit = pd.Series(SPOT_PRICE_RANGE)

    win = profit >= strike
    lose = profit < strike
    profit[win] = units * (profit-strike-optionPrice) - FEE
    profit[lose] = -1 * units * optionPrice - FEE

    return profit

def shortCall(strike, units, pUSD, pBTC=None, currentBTC = None, feeRate = 0.0004):

    if pBTC == None:
        optionPrice = pUSD
    else:
        optionPrice = pBTC * currentBTC

    FEE = units * feeRate * currentBTC
    profit = pd.Series(SPOT_PRICE_RANGE)

    win = profit <= strike
    lose = profit > strike
    profit[win] = units * optionPrice - FEE
    profit[lose] = -1 * units * (profit - strike - optionPrice) - FEE

    return profit

def longPut(strike, units, pUSD, pBTC=None, currentBTC=None, feeRate = 0.0004):

    if pBTC == None:
        optionPrice = pUSD
    else:
        optionPrice = pBTC * currentBTC

    FEE = units * feeRate * currentBTC
    profit = pd.Series(SPOT_PRICE_RANGE)

    win = profit <= strike
    lose = profit > strike
    profit[win] = units * (strike - profit - optionPrice) - FEE
    profit[lose] = -1 * units * optionPrice - FEE

    return profit

def shortPut(strike, units, pUSD, pBTC=None, currentBTC=None, feeRate = 0.0004):

    if pBTC == None:
        optionPrice = pUSD
    else:
        optionPrice = pBTC * currentBTC

    FEE = units * feeRate * currentBTC
    profit = pd.Series(SPOT_PRICE_RANGE)

    win = profit >= strike
    lose = profit < strike
    profit[win] = units * optionPrice - FEE
    profit[lose] = -1 * units * (strike - profit - optionPrice) - FEE

    return profit


def condor(sk1, sk2, sk3, sk4, bUnits, spot, expiry, useDeribit=True, charts = False):
    print('=== CONDOR ===')
    if useDeribit:
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk1, 'C')
        pBTC1 = ask
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk2, 'C')
        pBTC2 = ask
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk3, 'C')
        pBTC3 = bid
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk4, 'C')
        pBTC4 = bid

    else:
        ask, bid, delta = getOptionData(expiry, sk1, 'C')
        pBTC1 = ask
        ask, bid, delta = getOptionData(expiry, sk2, 'C')
        pBTC2 = ask
        ask, bid, delta = getOptionData(expiry, sk3, 'C')
        pBTC3 = bid
        ask, bid, delta = getOptionData(expiry, sk4, 'C')
        pBTC4 = bid

    print('BTC Index:', spot)
    print('Buy Call Strike:', sk1, 'Ask:',pBTC1, 'BTC Units:', bUnits)
    print('Buy Call Strike:', sk2, 'Bid:',pBTC2, 'BTC Units:', bUnits)
    print('Sell Call Strike:', sk3, 'Ask:',pBTC3, 'BTC Units:', bUnits)
    print('Sell Call Strike:', sk4, 'Bid:', pBTC4, 'BTC Units:', bUnits)

    if pBTC1<=0 or pBTC2<=0 or pBTC3<=0 or pBTC4<=0:
        print('Combination not possible. Exiting.')
        return

    LC1 = longCall(sk1,bUnits,None,pBTC1,spot,)
    LC2 = longCall(sk2, bUnits, None, pBTC2, spot, )
    SC1 = shortCall(sk3, bUnits, None, pBTC3, spot, )
    SC2 = shortCall(sk4, bUnits, None, pBTC4, spot, )

    total = LC1 + LC2 + SC1 + SC2

    maxProfit = max(total)
    maxLoss = min(total)

    print('Max Profit:', maxProfit)
    print('Max Loss:', maxLoss)

    if maxLoss > 0:
        print('100% Win')
        return 'CONDOR', 'Buy Call', sk1,pBTC1, 'Buy Call', sk2,pBTC2, 'Sell Call', sk3,pBTC3, 'Sell Call', sk4,pBTC4, None, None, None, 1,  maxProfit, maxLoss, maxProfit

    elif maxProfit < 0:
        print('100% Loss')
        return 'CONDOR', 'Buy Call', sk1,pBTC1, 'Buy Call', sk2,pBTC2, 'Sell Call', sk3,pBTC3, 'Sell Call', sk4,pBTC4, None, None, None, 0,  maxLoss, maxLoss, maxProfit
    else:
        pos = total > 0
        pos = total[pos]
        ind = pos.index

        lower = SPOT_PRICE_RANGE.iloc[ind[0]]
        upper = SPOT_PRICE_RANGE.iloc[ind[-1]]
        print('Lower:', lower, 'Upper:', upper, 'Size:', upper - lower)

        p = probabilityInRange(lower, upper, spot, expiry)
        print('Prob Profit Zone: %.4f'% (p))

        pseudoER = pseudoExpRet(p, maxProfit, maxLoss)
        print('Pseudo Expected Return: %.4f'%(pseudoER))

        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LC1,LC2,SC1,SC2],total=total, names = ['LC1','LC2','SC1','SC2'], title = title )

        return 'CONDOR', 'Buy Call', sk1,pBTC1, 'Buy Call', sk2,pBTC2, 'Sell Call', sk3,pBTC3, 'Sell Call', sk4,pBTC4, upper, lower, upper-lower, p, pseudoER, maxLoss, maxProfit

def rodnoc(sk1, sk2, sk3, sk4, bUnits, spot, expiry, useDeribit=True, charts = False):
    print('=== INVERSE CONDOR ===')
    if useDeribit:
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk1, 'C')
        pBTC1 = bid
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk2, 'C')
        pBTC2 = bid
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk3, 'C')
        pBTC3 = ask
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk4, 'C')
        pBTC4 = ask

    else:
        ask, bid, delta = getOptionData(expiry, sk1, 'C')
        pBTC1 = bid
        ask, bid, delta = getOptionData(expiry, sk2, 'C')
        pBTC2 = bid
        ask, bid, delta = getOptionData(expiry, sk3, 'C')
        pBTC3 = ask
        ask, bid, delta = getOptionData(expiry, sk4, 'C')
        pBTC4 = ask

    print('BTC Index:', spot)
    print('Sell Call Strike:', sk1, 'Ask:',pBTC1, 'BTC Units:', bUnits)
    print('Sell Call Strike:', sk2, 'Bid:',pBTC2, 'BTC Units:', bUnits)
    print('Buy Call Strike:', sk3, 'Ask:',pBTC3, 'BTC Units:', bUnits)
    print('Buy Call Strike:', sk4, 'Bid:', pBTC4, 'BTC Units:', bUnits)

    if pBTC1<=0 or pBTC2<=0 or pBTC3<=0 or pBTC4<=0:
        print('Combination not possible. Exiting.')
        return

    LC1 = longCall(sk3,bUnits,None,pBTC3,spot, )
    LC2 = longCall(sk4, bUnits, None, pBTC4, spot, )
    SC1 = shortCall(sk1, bUnits, None, pBTC1, spot, )
    SC2 = shortCall(sk2, bUnits, None, pBTC2, spot, )

    total = LC1 + LC2 + SC1 + SC2

    maxProfit = max(total)
    maxLoss = min(total)

    print('Max Profit:', maxProfit)
    print('Max Loss:', maxLoss)

    if maxLoss > 0:
        print('100% Win')
        return 'RODNOC', 'Sell Call', sk1,pBTC1, 'Sell Call', sk2,pBTC2, 'Buy Call', sk3,pBTC3, 'Buy Call', sk4,pBTC4, None, None, None, 1, maxProfit, maxLoss, maxProfit
    elif maxProfit < 0:
        print('100% Loss')
        return 'RODNOC', 'Sell Call', sk1,pBTC1, 'Sell Call', sk2,pBTC2, 'Buy Call', sk3,pBTC3, 'Buy Call', sk4,pBTC4, None, None, None, 0, maxLoss, maxLoss, maxProfit
    else:
        pos = total < 0
        pos = total[pos]
        ind = pos.index

        try:
            lower = SPOT_PRICE_RANGE.iloc[ind[0]-1]
        except:
            lower = SPOT_PRICE_RANGE.iloc[ind[0]]

        try:
            upper = SPOT_PRICE_RANGE.iloc[ind[-1]+1]
        except:
            upper = SPOT_PRICE_RANGE.iloc[ind[-1]]

        print('Lower:', lower, 'Upper:', upper, 'Size:', upper - lower)

        p = probabilityOutRange(lower, upper, spot, expiry)
        print('Prob Profit Zone: %.4f'% (p))

        pseudoER = pseudoExpRet(p, maxProfit, maxLoss)
        print('Pseudo Expected Return: %.4f'%(pseudoER))

        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LC1,LC2,SC1,SC2],total=total, names = ['LC1','LC2','SC1','SC2'], title = title )

        return 'RODNOC', 'Sell Call', sk1,pBTC1, 'Sell Call', sk2,pBTC2, 'Buy Call', sk3,pBTC3, 'Buy Call', sk4,pBTC4, upper, lower, upper - lower, p, pseudoER, maxLoss, maxProfit

def callVert_S(sk1, sk2, bUnits, spot, expiry, useDeribit=True, charts = False):
    print('=== CALL VERTICAL S BULL ===')

    if useDeribit:
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk1, 'C')
        pBTC1 = ask
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk2, 'C')
        pBTC2 = bid

    else:
        ask, bid, delta = getOptionData(expiry, sk1, 'C')
        pBTC1 = ask
        ask, bid, delta = getOptionData(expiry, sk2, 'C')
        pBTC2 = bid

    print('BTC Index:', spot)
    print('Buy Call Strike:', sk1, 'Ask:',pBTC1, 'BTC Units:', bUnits)
    print('Sell call Strike:', sk2, 'Bid:',pBTC2, 'BTC Units:', bUnits)

    if pBTC1<=0 or pBTC2<=0:
        print('Combination not possible. Exiting.')
        return

    LC1 = longCall(sk1,bUnits,None,pBTC1,spot, )
    SC1 = shortCall(sk2, bUnits, None, pBTC2, spot, )

    total = LC1 + SC1

    maxProfit = max(total)
    maxLoss = min(total)

    print('Max Profit:', maxProfit)
    print('Max Loss:', maxLoss)

    if maxLoss > 0:
        print('100% Win')

        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LC1,SC1],total=total, names = ['LC1','SC1'], title = title )

        return 'CALL VERT S (BULL)', 'Buy Call', sk1, pBTC1, 'Sell Call', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 1, maxProfit, maxLoss, maxProfit
    elif maxProfit < 0:
        print('100% Loss')
        return 'CALL VERT S (BULL)', 'Buy Call', sk1, pBTC1, 'Sell Call', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 0, maxLoss, maxLoss, maxProfit
    else:
        pos = total > 0
        pos = total[pos]
        ind = pos.index

        boundary = SPOT_PRICE_RANGE.iloc[ind[0]]
        print('Zero Crossing:', boundary)

        p = probabilityAboveStrike(boundary, spot, expiry)
        print('Prob Profit Zone: %.4f'% (p))

        pseudoER = pseudoExpRet(p, maxProfit, maxLoss)
        print('Pseudo Expected Return: %.4f'%(pseudoER))

        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LC1,SC1],total=total, names = ['LC1','SC1'], title = title )

        return 'CALL VERT S (BULL)', 'Buy Call', sk1, pBTC1, 'Sell Call', sk2, pBTC2, None, None, None, None, None, None, boundary, boundary, None, p, pseudoER, maxLoss, maxProfit

def putVert_S(sk1, sk2, bUnits, spot, expiry, useDeribit=True, charts = False):
    print('=== PUT VERTICAL S BULL ===')

    if useDeribit:
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk1, 'P')
        pBTC1 = ask
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk2, 'P')
        pBTC2 = bid

    else:
        ask, bid, delta = getOptionData(expiry, sk1, 'P')
        pBTC1 = ask
        ask, bid, delta = getOptionData(expiry, sk2, 'P')
        pBTC2 = bid

    print('BTC Index:', spot)
    print('Buy Put Strike:', sk1, 'Ask:',pBTC1, 'BTC Units:', bUnits)
    print('Sell Put Strike:', sk2, 'Bid:',pBTC2, 'BTC Units:', bUnits)

    if pBTC1<=0 or pBTC2<=0:
        print('Combination not possible. Exiting.')
        return

    LP1 = longPut(sk1,bUnits,None,pBTC1,spot, )
    SP1 = shortPut(sk2, bUnits, None, pBTC2, spot, )

    total = LP1 + SP1

    maxProfit = max(total)
    maxLoss = min(total)

    print('Max Profit:', maxProfit)
    print('Max Loss:', maxLoss)

    if maxLoss > 0:
        print('100% Win')
        return 'PUT VERT S (BULL)', 'Buy Put', sk1, pBTC1, 'Sell Put', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 1, maxProfit, maxLoss, maxProfit
    elif maxProfit < 0:
        print('100% Loss')
        return 'PUT VERT S (BULL)', 'Buy Put', sk1, pBTC1, 'Sell Put', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 0, maxLoss, maxLoss, maxProfit
    else:
        pos = total > 0
        pos = total[pos]
        ind = pos.index

        boundary = SPOT_PRICE_RANGE.iloc[ind[0]]
        print('Zero Crossing:', boundary)

        p = probabilityAboveStrike(boundary, spot, expiry)
        print('Prob Profit Zone: %.4f'% (p))

        pseudoER = pseudoExpRet(p, maxProfit, maxLoss)
        print('Pseudo Expected Return: %.4f'%(pseudoER))

        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LP1,SP1],total=total, names = ['LP1','SP1'], title = title )

        return 'PUT VERT S (BULL)', 'Buy Put', sk1, pBTC1, 'Sell Put', sk2, pBTC2, None, None, None, None, None, None, boundary, boundary, None, p, pseudoER, maxLoss, maxProfit

def callVert_Z(sk1, sk2, bUnits, spot, expiry, useDeribit=True, charts = False):
    print('=== CALL VERTICAL Z BEAR ===')
    if useDeribit:
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk1, 'C')
        pBTC1 = bid
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk2, 'C')
        pBTC2 = ask

    else:
        ask, bid, delta = getOptionData(expiry, sk1, 'C')
        pBTC1 = bid
        ask, bid, delta = getOptionData(expiry, sk2, 'C')
        pBTC2 = ask

    print('BTC Index:', spot)
    print('Sell Call Strike:', sk1, 'Bid:',pBTC1, 'BTC Units:', bUnits)
    print('Buy Call Strike:', sk2, 'Ask:',pBTC2, 'BTC Units:', bUnits)

    if pBTC1<=0 or pBTC2<=0:
        print('Combination not possible. Exiting.')
        return

    SC1 = shortCall(sk1,bUnits,None,pBTC1,spot, )
    LC1 = longCall(sk2, bUnits, None, pBTC2, spot, )

    total = LC1 + SC1

    maxProfit = max(total)
    maxLoss = min(total)

    print('Max Profit:', maxProfit)
    print('Max Loss:', maxLoss)

    if maxLoss > 0:
        print('100% Win')
        return 'CALL VERT Z (BEAR)', 'Sell Call', sk1, pBTC1, 'Buy Call', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 1, maxProfit, maxLoss, maxProfit
    elif maxProfit < 0:
        print('100% Loss')
        return 'CALL VERT Z (BEAR)', 'Sell Call', sk1, pBTC1, 'Buy Call', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 0, maxLoss, maxLoss, maxProfit
    else:
        pos = total < 0
        pos = total[pos]
        ind = pos.index

        boundary = SPOT_PRICE_RANGE.iloc[ind[0]]
        print('Zero Crossing:', boundary)

        p = probabilityBelowStrike(boundary, spot, expiry)
        print('Prob Profit Zone: %.4f'% (p))

        pseudoER = pseudoExpRet(p, maxProfit, maxLoss)
        print('Pseudo Expected Return: %.4f'%(pseudoER))

        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LC1,SC1],total=total, names = ['LC1','SC1'], title = title )

        return 'CALL VERT Z (BEAR)', 'Sell Call', sk1, pBTC1, 'Buy Call', sk2, pBTC2, None, None, None, None, None, None, boundary, boundary, None, p, pseudoER, maxLoss, maxProfit

def putVert_Z(sk1, sk2, bUnits, spot, expiry, useDeribit=True, charts = False):
    print('=== PUT VERTICAL Z BEAR ===')
    if useDeribit:
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk1, 'P')
        pBTC1 = bid
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk2, 'P')
        pBTC2 = ask

    else:
        ask, bid, delta = getOptionData(expiry, sk1, 'P')
        pBTC1 = bid
        ask, bid, delta = getOptionData(expiry, sk2, 'P')
        pBTC2 = ask

    print('BTC Index:', spot)
    print('Sell Put Strike:', sk1, 'Bid:',pBTC1, 'BTC Units:', bUnits)
    print('Buy Put Strike:', sk2, 'Ask:',pBTC2, 'BTC Units:', bUnits)

    if pBTC1<=0 or pBTC2<=0:
        print('Combination not possible. Exiting.')
        return

    SP1 = shortPut(sk1,bUnits,None,pBTC1,spot, )
    LP1 = longPut(sk2, bUnits, None, pBTC2, spot, )

    total = SP1 + LP1

    maxProfit = max(total)
    maxLoss = min(total)

    print('Max Profit:', maxProfit)
    print('Max Loss:', maxLoss)

    if maxLoss > 0:
        print('100% Win')
        return 'PUT VERT Z (BEAR)', 'Sell Put', sk1, pBTC1, 'Buy Put', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 1, maxProfit, maxLoss, maxProfit
    elif maxProfit < 0:
        print('100% Loss')
        return 'PUT VERT Z (BEAR)', 'Sell Put', sk1, pBTC1, 'Buy Put', sk2, pBTC2, None, None, None, None, None, None, None, None, None, 0, maxLoss, maxLoss, maxProfit
    else:
        pos = total < 0
        pos = total[pos]
        ind = pos.index

        boundary = SPOT_PRICE_RANGE.iloc[ind[0]]
        print('Zero Crossing:', boundary)

        p = probabilityBelowStrike(boundary, spot, expiry)
        print('Prob Profit Zone: %.4f'% (p))

        pseudoER = pseudoExpRet(p, maxProfit, maxLoss)
        print('Pseudo Expected Return: %.4f'%(pseudoER))
        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LP1,SP1],total=total, names = ['LP1','SP1'], title = title )

        return 'PUT VERT Z (BEAR)', 'Sell Put', sk1, pBTC1, 'Buy Put', sk2, pBTC2, None, None, None, None, None, None, boundary, boundary, None, p, pseudoER, maxLoss, maxProfit

def straddle(sk1, sk2, bUnits, spot, expiry, useDeribit=True, charts = False):

    if useDeribit:
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk1, 'C')
        pBTC1 = ask
        ask, bid, delta = deribitOptionsData(dateStr(expiry), sk2, 'P')
        pBTC2 = ask

    else:
        ask, bid, delta = getOptionData(expiry, sk1, 'C')
        pBTC1 = ask
        ask, bid, delta = getOptionData(expiry, sk2, 'P')
        pBTC2 = ask
    print('=== STRADDLE ===')
    print('BTC Index:', spot)
    print('Buy Call Strike:', sk1, 'Ask:',pBTC1, 'BTC Units:', bUnits)
    print('Buy Put Strike:', sk2, 'Bid:',pBTC2, 'BTC Units:', bUnits)

    if pBTC1<=0 or pBTC2<=0:
        print('Combination not possible. Exiting.')
        return

    LC1 = longCall(sk1,bUnits,None,pBTC1,spot, )
    LP1 = longPut(sk2, bUnits, None, pBTC2, spot, )

    total = LC1 + LP1

    maxProfit = max(total)
    maxLoss = min(total)

    print('Max Profit:', maxProfit)
    print('Max Loss:', maxLoss)

    if maxLoss > 0:
        print('100% Win')
        return 'STRADDLE', 'Buy Call', sk1, pBTC1, 'Buy Put', sk2, pBTC2, None, None, None, None, None, None, None, None,  None, 1, maxProfit, maxLoss, maxProfit
    elif maxProfit < 0:
        print('100% Loss')
        return 'STRADDLE', 'Buy Call', sk1, pBTC1, 'Buy Put', sk2, pBTC2, None, None, None, None, None, None, None, None,  None, 0, maxLoss, maxLoss, maxProfit
    else:
        pos = total < 0
        pos = total[pos]
        ind = pos.index

        lower = SPOT_PRICE_RANGE.iloc[ind[0]]
        upper = SPOT_PRICE_RANGE.iloc[ind[-1]]
        print('Lower:', lower, 'Upper:', upper, 'Size:', upper - lower)

        p = probabilityOutRange(lower, upper, spot, expiry)
        print('Prob Profit Zone: %.4f'% (p))

        pseudoER = pseudoExpRet(p, -1 * maxLoss, maxLoss)
        print('Pseudo Expected Return: %.4f'%(pseudoER),)
        print("Take this value with a pinch of salt for straddles as max profit is unbounded.")

        if charts:
            title = 'BTC-'+dateStr(expiry)+'<br>'+'%.2f'%(spot)
            plotStuff(SPOT_PRICE_RANGE, [LC1,LP1],total=total, names = ['LC1','LP1'], title = title )

        return 'STRADDLE', 'Buy Call', sk1,pBTC1, 'Buy Put', sk2,pBTC2, None, None,None, None, None,None, upper, lower, upper - lower, p, pseudoER, maxLoss, maxProfit



def getT(end, start = None):
    end = unix_time_millis(end)
    if start == None:
        start = time.time() * 1000
    else:
        start = unix_time_millis(start)

    dayMillis = 24 * 60* 60 * 1000

    yearMillis = 365 * dayMillis

    return (end-start) / yearMillis

def unix_time_millis(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds() * 1000.0

def dateStr(dt):

    return dt.strftime('%d%b%y').upper()

def getR():
    yearlyURL = 'https://eservices.mas.gov.sg/api/action/datastore/search.json?' \
                'resource_id=ea5e28f0-fdcd-4408-be63-4cd7b2471113'

    monthlyURL = 'https://eservices.mas.gov.sg/api/action/datastore/search.json?' \
          'resource_id=b5adb5c2-4604-49f3-b924-b69691252380'

    weeklyURL = 'https://eservices.mas.gov.sg/api/action/datastore/search.json?' \
                'resource_id=9a51d255-fec1-4aca-9818-b7a47490243c'

    dailyURL = 'https://eservices.mas.gov.sg/api/action/datastore/search.json?' \
               'resource_id=9a0bf149-308c-4bd2-832d-76c8e6cb47ed'

    url = yearlyURL

    sortYear = '&sort=end_of_year desc'  # change to `end_of_month` for monthlyURL, etc.
    url += '&limit=1'
    url += sortYear

    header = dict()
    header['Content-Type'] = 'application/json'
    header['User-Agent'] = 'Mozilla/5.0'

    response = requests.get(url, headers=header)
    res = response.json()['result']['records']

    r = float(res[0]['standing_facility_deposit']) / 100

    return r

    # for r in res:
    #     for k in r.keys():
    #         print(k, r[k])
    #     print()


def getSigRtT(expiry):
    #sigRtT = sigma * sqrt(t)
    candles = getCandles('BTC-USDT', start=datetime.datetime(2019,1,1), end=expiry)

    num = 24*7 # latest one week's worth of hourly data

    candles = candles[-num:]

    u = np.log(candles.close.shift(-1) / candles.close)
    u = u.dropna()

    sigRtT = np.std(u)

    return sigRtT

def getSig():
    return deribitHV()

def probabilityBelowStrike(strike, spot, expiry):

    t = getT(end=expiry)
    r = getR()

    ##region:if computing historical volatility from past year's annual BTC data
    # sigRtT = getSigRtT(expiry)
    # sigma = sigRtT / (np.sqrt(t))
    ##endregion

    sigma = getSig()
    # print('t', t, 'sigma', sigma)
    sigRtT = sigma * np.sqrt(t)
    mu = r - 0.5 * sigma * sigma
    z = (np.log(strike/spot) - (mu * t))/sigRtT
    Nz = norm.cdf(z)

    return Nz

def probabilityAboveStrike(strike, spot, expiry):

    return 1 - probabilityBelowStrike(strike,spot, expiry)

def probabilityInRange(lower, upper, spot, expiry):

    N_upper = probabilityBelowStrike(upper,spot, expiry)
    N_lower = probabilityBelowStrike(lower, spot, expiry)

    return N_upper - N_lower

def probabilityOutRange(lower, upper, spot, expiry):

    return 1 - probabilityInRange(lower, upper, spot, expiry)

def pseudoExpRet(pWin,win,lose):
    pLose = 1 - pWin

    return (pWin*win) + (pLose*lose)


def plotStuff(spot, data, total, names, title):
    plots = []

    for i in range(len(data)):
        p = Scatter(x=spot, y=data[i], mode='lines', name=names[i], line=dict(width=2, dash='dash'))
        plots.append(p)

    t = Scatter(x=spot, y=total, mode='lines', name='total', line=dict(color='royalblue', width=4, dash='solid'))
    plots.append(t)

    layout = Layout(
        title=title,
        xaxis=dict(
            rangeslider=dict(
                visible=False
            ),
            # range=showXaxisRange,
            showgrid=True,

        ),
        showlegend=True,
    )

    figure=Figure(data=plots, layout=layout)

    htmlFile = plotly.offline.plot(figure,
                                   # show_link=False,
                                   # output_type='div',
                                   # include_plotlyjs=False,
                                   filename='options.html',
                                   auto_open=True,
                                   config={'displaylogo': False,
                                           'modeBarButtonsToRemove': ['sendDataToCloud', 'select2d', 'zoomIn2d',
                                                                      'zoomOut2d',
                                                                      'resetScale2d', 'hoverCompareCartesian',
                                                                      'lasso2d'],
                                           'displayModeBar': True
                                           })


def getCondors(spot, dates, useDeribit = True, bUnits = 0.5, butterfly = False, inverse = False):

    results = []

    if inverse:
        print('****** INVERSE CONDOR ******')
    else:
        print('****** CONDOR ******')

    if useDeribit: spacingRange = [6,8,12]
    else: spacingRange = [4,6]

    for d in dates:
        print('=== DATE:', d.strftime('%d %b %y'), '=======')

        if useDeribit:
            skRange = deribitStrikes(dateStr(d), 'C')
        else:
            skRange = getOptionStrikes_okex(d)

        for spacing in spacingRange:

            for i in range(len(skRange)):
                print()
                print('-----------------------------------')

                if butterfly:

                    if (i + spacing + 2 ) >= len(skRange):
                        break
                    sk1 = skRange[i]
                    sk2 = skRange[i+spacing+2]
                    sk3 = skRange[i+int(spacing/2)+1]
                    sk4 = skRange[i+int(spacing/2)+1]
                else:

                    if (i + 2 + spacing) >= len(skRange):
                        break
                    sk1 = skRange[i]
                    sk3 = skRange[i + 1]
                    sk4 = skRange[i + 1 + spacing]
                    sk2 = skRange[i + 1 + spacing + 1]

                if inverse:
                    r = rodnoc(sk1, sk2, sk3, sk4, bUnits=bUnits, spot=spot, expiry=d, useDeribit=useDeribit)
                else:
                    r = condor(sk1, sk2, sk3, sk4, bUnits=bUnits, spot=spot, expiry=d, useDeribit=useDeribit)

                if r != None:
                    results.append(r)

                print('-----------------------------------')
    return results

def getVerts(spot, dates, useDeribit=True, bUnits = 0.5, S = True, Call = True):
    results = []

    if Call:
        if S:
            print('****** CALL VERTICAL - S ******')
        else:
            print('****** CALL VERTICAL - Z ******')
    else:
        if S:
            print('****** PUT VERTICAL - S ******')
        else:
            print('****** PUT VERTICAL - Z ******')

    if useDeribit: spacingRange = [1,2, 8]
    else: spacingRange = [1,4]

    for d in dates:
        print('=== DATE:', d.strftime('%d %b %y'), '=======')

        if useDeribit:
            skRange = deribitStrikes(dateStr(d), 'C')
        else:
            skRange = getOptionStrikes_okex(d)

        for spacing in spacingRange:

            for i in range(len(skRange)):
                print()
                print('-----------------------------------')

                if (i + spacing) >= len(skRange):
                    break

                sk1 = skRange[i]
                sk2 = skRange[i + spacing]

                if Call:
                    if S:
                        r = callVert_S(sk1, sk2, bUnits=bUnits, spot=spot, expiry =d, useDeribit=useDeribit)
                    else:
                        r = callVert_Z(sk1, sk2, bUnits=bUnits, spot=spot, expiry=d, useDeribit=useDeribit)
                else:
                    if S:
                        r = putVert_S(sk1, sk2, bUnits=bUnits, spot=spot, expiry=d, useDeribit=useDeribit)
                    else:
                        r = putVert_Z(sk1, sk2, bUnits=bUnits, spot=spot, expiry=d, useDeribit=useDeribit)

                if r != None:
                    results.append(r)
                print('-----------------------------------')
    return results

def getStraddles(spot,dates, useDeribit=True, bUnits = 0.5):

    results = []


    print('****** STRADDLE ******')

    if useDeribit: spacingRange = [1,2,4]
    else: spacingRange = [1,2]

    for d in dates:
        print('=== DATE:', d.strftime('%d %b %y'), '=======')

        if useDeribit:
            skRange = deribitStrikes(dateStr(d), 'C')
        else:
            skRange = getOptionStrikes_okex(d)

        for spacing in spacingRange:

            for i in range(len(skRange)):
                print()
                print('-----------------------------------')

                if (i + spacing) >= len(skRange):
                    break

                sk1 = skRange[i]
                sk2 = skRange[i + spacing]
                r = straddle(sk1, sk2, bUnits=bUnits, spot=spot, expiry=d, useDeribit=useDeribit)

                if r!= None:
                    results.append(r)

                print('-----------------------------------')
    return results

def main(spot, dates, useDeribit):
    startTime = time.time()

    if useDeribit:
        exchange = 'Deribit'
    else:
        exchange = 'OKEx'

    columns = ['Type',
               'Buy/Sell C/P 1', 'Strike 1', 'Price 1',
               'Buy/Sell C/P 2', 'Strike 2', 'Price 2',
               'Buy/Sell C/P 3', 'Strike 3', 'Price 3',
               'Buy/Sell C/P 4', 'Strike 4', 'Price 4',
               'Upper', 'Lower', 'Upper - Lower', 'P(Profit Zone)',
               'Pseudo Expected Return', ' Max Loss', 'Max Profit']

    for d in dates:
        overall = []

        # # Condors
        # res = getCondors(spot, [d], useDeribit=useDeribit, bUnits=0.5, butterfly=False, inverse=False)
        # overall += res
        #
        # # #Rverse Condors
        # res = getCondors(spot, [d], useDeribit=useDeribit, bUnits=0.5, butterfly=False, inverse=True)
        # overall += res
        #
        # Straddle
        # res = getStraddles(spot, [d], useDeribit=useDeribit, bUnits=0.5)
        # overall += res
        #
        # # Call Bull
        # res = getVerts(spot, [d], useDeribit=useDeribit, bUnits=0.5, S=True, Call=True)
        # overall += res

        # # Call Bear
        res = getVerts(spot, [d], useDeribit=useDeribit, bUnits=0.5, S=False, Call=True)
        overall += res

        # # # Put Bull
        # res = getVerts(spot, [d], useDeribit=useDeribit, bUnits=0.5, S=True, Call=False)
        # overall += res
        #
        # # # Put Bear
        # res = getVerts(spot, [d], useDeribit=useDeribit, bUnits=0.5, S=False, Call=False)
        # overall += res

        overall = pd.DataFrame(overall, columns=columns)

        # Swap the 'upper' and 'lower' columns
        cols = list(overall.columns)
        a, b = cols.index('Upper'), cols.index('Lower')
        cols[b], cols[a] = cols[a], cols[b]
        overall = overall[cols]

        filename = 'results//' + exchange + '_' + '_EXP-' + dateStr(d) + '_%.2f_' % (
            spot) + datetime.datetime.now().strftime('%d-%b-%y_%H-%M-%S_%z%Z').upper()

        overall.to_csv(filename + '.csv')

        endTime = time.time()
        elapsed = endTime - startTime
        print('Time taken %.2f seconds.' % (elapsed))


if __name__ == '__main__':

    useDeribit = True  # Deribit or Okex

    # if useDeribit:
    #     FEE = 0.01
    # else:
    #     FEE = 0.0008

    spot = deribitBTCindex()
    dates = [
        # datetime.datetime(2020,5,11,8),
        # datetime.datetime(2020, 5, 14, 8),
        #  datetime.datetime(2020,5,17,8),
        # datetime.datetime(2020, 5, 29, 8),
        datetime.datetime(2020, 6, 26, 8),
        # datetime.datetime(2020, 12, 25, 8),

    ]

    # main(spot, dates, useDeribit)
    # #
    # for d in dates:
    #
    #     yhat, upper, lower = forecast.forecast(d,showPlot=False,histPeriodDays=90, periodsAhead=1500)
    #     print('************************************************')
    #     print(d, 'yhat:', yhat, 'upper:', upper, 'lower', lower, '||', 'spot', spot)
    #     print('************************************************')
    #     print()
    #
    # #
    # exit()
    #
    # #
    putVert_S(2500, 3500, bUnits=20, spot=spot, expiry=dates[0], useDeribit=useDeribit, charts=True)
    # callVert_Z(9000,9500,bUnits=19,spot = spot,expiry=dates[0],useDeribit=useDeribit,charts=True)
    # exit()












