import json
import asyncio
from websockets import connect
import datetime, time
import pandas as pd
from plotly.graph_objs import Scatter, Layout, Figure
import plotly
import forecast

FEE_RATE = 0.0006
TOL = 0.2
pd.set_option('display.width', 160)
pd.set_option('display.max_columns', 11)
pd.set_option('display.max_rows', None)


# URL = 'ws://localhost:8000'

class Handler:

    def __init__(self, uri):
        self.ws = None
        self.uri = uri
        self.loop = asyncio.get_event_loop()
        # perform a synchronous connect
        self.loop.run_until_complete(self.__async__connect())

    async def __async__connect(self):
        print("attempting connection to {}".format(self.uri))
        # perform async connect, and store the connected WebSocketClientProtocol
        # object, for later reuse for send & recv
        self.ws = await connect(self.uri)
        print("connected")

    async def auth(self):
        id = open('dbID.key', 'r').read()
        secret = open('dbSecret.key', 'r').read()

        msg = \
            {
                "jsonrpc": "2.0",
                "id": 9929,
                "method": "public/auth",
                "params": {
                    "grant_type": "client_credentials",
                    "client_id": id,
                    "client_secret": secret
                }
            }
        await self.ws.send(json.dumps(msg))

    def command(self, cmd):
        return self.loop.run_until_complete(self.__async__command(cmd))

    async def __async__command(self, cmd):
        await self.ws.send(json.dumps(cmd))
        return json.loads(await self.ws.recv())['result']


def getMargin(handler):
    msg = \
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "private/get_margins",
            "params": {
                "instrument_name": "BTC-PERPETUAL",
                "amount": 10000,
                "price": 3725
            }
        }
    handler.command(msg)


def getSpot(handler):
    msg = \
        {"jsonrpc": "2.0",
         "method": "public/get_index",
         "id": 42,
         "params": {
             "currency": "BTC"}
         }
    return float(handler.command(msg)['BTC'])

def getInstruments(handler):
    msg = \
            {
                "jsonrpc": "2.0",
                "id": 7617,
                "method": "public/get_instruments",
                "params": {
                    "currency": "BTC",
                    "kind": "option",
                    "expired": False
                }
            }
    return handler.command(msg)

def getQuotes(handler, expiry, strike, callPut):
    msg = \
        {
            "jsonrpc": "2.0",
            "id": 8106,
            "method": "public/ticker",
            "params": {
                "instrument_name": "BTC-" + expiry + '-' + str(strike) + '-' + callPut
            }
        }

    # print(expiry, strike, callPut)
    response = handler.command(msg)

    return response['best_bid_price'], response['best_bid_amount'], \
           response['best_ask_price'], response['best_ask_amount'],

def LC(strike, units, range, optionPrice, spot, feeRate = FEE_RATE):
    fee = units * feeRate * spot
    optionPrice = optionPrice * spot

    profit = pd.Series(range)

    win = profit >= strike
    lose = profit < strike
    profit[win] = units * (profit - strike - optionPrice) - fee
    profit[lose] = -1 * units * optionPrice - fee

    return profit

def SC(strike, units, range, optionPrice, spot, feeRate = FEE_RATE):
    fee = feeRate * spot * units
    optionPrice = optionPrice * spot

    profit = pd.Series(range)

    win = profit <= strike
    lose = profit > strike
    profit[win] = units * optionPrice - fee
    profit[lose] = -1 * units * (profit - strike - optionPrice) - fee

    return profit


def LP(strike, units, range, optionPrice, spot, feeRate = FEE_RATE):
    fee = feeRate * spot * units
    optionPrice = optionPrice * spot

    profit = pd.Series(range)

    win = profit <= strike
    lose = profit > strike
    profit[win] = units * (strike - profit - optionPrice) - fee
    profit[lose] = -1 * units * optionPrice - fee

    return profit

def SP(strike, units, range, optionPrice, spot, feeRate = FEE_RATE):
    fee = feeRate * spot * units
    optionPrice = optionPrice * spot

    profit = pd.Series(range)

    win = profit >= strike
    lose = profit < strike
    profit[win] = units * optionPrice - fee
    profit[lose] = -1 * units * (strike - profit - optionPrice) - fee

    return profit


def plotStuff(spot, data, total, names, title):
    plots = []

    for i in range(len(data)):
        p = Scatter(x=spot, y=data[i], mode='lines', name=names[i], line=dict(width=2, dash='dash'))
        plots.append(p)

    if total != None:
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



def verticals(test = False, dates = [], charts = False, verbose = False):

    if test:
        uri = 'wss://test.deribit.com/ws/api/v2'
        print('===  TESTNET  ===')
    else:
        uri = 'wss://www.deribit.com/ws/api/v2'
        print('===  MAINNET  ===')

    handler = Handler(uri)

    # handler.auth()

    # exit()

    instruments = getInstruments(handler)

    for d in dates:
        d = d.strftime('%-d%b%y').upper()
        print('===',d,'===')

        # all[d + '_CALL'] = []
        # all[d + '_PUT'] = []
        strikes = []

        s_results = []
        z_results = []

        for instr in instruments:
            if instr['instrument_name'] == "BTC-" + d + '-' + str(int(instr['strike'])) + '-' + 'C':
                strikes.append(int(instr['strike']))

        strikes.sort(reverse=False)
        l = len(strikes)
        spot = getSpot(handler)

        print('=== Index:', spot, '===')
        print('=== Lower Bound: %i'% ((1 - TOL) * spot), '===')
        print('=== Upper Bound: %i'% ((1 + TOL) * spot), '===')

        # Put Vertical S (Bull)
        for i in range(l - 1):
            s1 = strikes[i]
            bid1, bidAmt1, ask1, askAmt1 = getQuotes(handler, d, s1, 'P')
            if ask1 <= 0:
                if verbose: print('s1 price N.A')
                continue

            for j in range(i + 1, l):
                s2 = strikes[j]
                bid2, bidAmt2, ask2, askAmt2 = getQuotes(handler, d, s2, 'P')

                if verbose: print(s1, s2)

                if bid2 <= 0:
                    if verbose: print('s2 price N.A')
                    continue

                if (ask1 >= bid2):
                    if verbose: print(ask1, bid2)
                    if verbose: print('Too expensive')
                    continue

                units = min(bidAmt2, askAmt1)

                fee = FEE_RATE * spot * units
                optionPrice1 = ask1 * spot      #long put
                optionPrice2 = bid2 * spot      #short put

                maxProfit = units * (optionPrice2 - optionPrice1) - fee - fee
                maxLoss = units * (s1 - s2 + optionPrice2 - optionPrice1) - fee - fee

                m = (maxProfit - maxLoss) / (s2-s1)
                c = maxProfit - (m * s2)
                boundary = -1 * (c/m)

                if charts:
                    INTERVAL = 5
                    START = s1 - INTERVAL - 500
                    END = s2 + INTERVAL + 500
                    RANGE = range(START, END, INTERVAL)
                    SPOT_PRICE_RANGE = pd.Series(RANGE)

                    long = LP(s1, units, SPOT_PRICE_RANGE, ask1, spot)
                    short = SP(s2, units, SPOT_PRICE_RANGE, bid2, spot)
                    total = short + long
                    # maxProfit = max(total)
                    # maxLoss = min(total)

                if maxProfit < 0:
                    if verbose: print('100% Loss')
                    continue
                elif maxLoss > 0:
                    print('@@@@@@@@@@@@@@@@ 100% Win @@@@@@@@@@@@@@@@@')
                    boundary = 0
                else:
                    # pos = total > 0
                    # pos = total[pos]
                    # ind = pos.index
                    # boundary = SPOT_PRICE_RANGE.iloc[ind[0]]

                    if boundary >= ((1-TOL) * spot):
                        continue

                #     print('Profit if above %i' %(boundary))
                # print('Max: %i'%(maxProfit), 'Min: %i'%(maxLoss))
                # print('Buy Put: Strike', s1, 'at', ask1, '|| Sell Put:', s2, 'at', bid2, '|| Units:', units)
                # print()

                if charts:
                    title = 'BTC-' + d + '<br>' + '%.2f' % (spot)
                    plotStuff(SPOT_PRICE_RANGE, [long, short], total=total, names=['Long Put', 'Short Put'],
                              title=title)

                s_results.append([boundary, maxProfit/units, maxProfit, maxLoss, 'Buy Put', s1, ask1, 'Sell Put', s2, bid2, units])

        s_df = pd.DataFrame(s_results, columns=['Profit if above', 'unitProfit', 'maxProfit', 'maxLoss',
                                                'Order 1 Type', 'Strike 1', 'Price 1',
                                                'Order 2 Type', 'Strike 2', 'Price 2',
                                                'units'])

        s_df = s_df.sort_values(by=['Profit if above'])
        print(s_df)
        print()


    #region:Call Vertical Z (Bear)
        for i in range(l-1):
            s1 = strikes[i]
            bid1, bidAmt1, ask1, askAmt1 = getQuotes(handler, d, s1, 'C')
            if bid1 <= 0:
                if verbose: print('s1 price N.A')
                continue

            for j in range(i+1, l):
                s2 = strikes[j]
                bid2, bidAmt2, ask2, askAmt2 = getQuotes(handler, d, s2, 'C')

                if verbose: print(s1, s2)

                if ask2 <=0:
                    if verbose: print('s2 price N.A')
                    continue

                if (ask2 >= bid1):
                    if verbose: print(bid1, ask2)
                    if verbose: print('Too expensive')
                    continue

                units = min(bidAmt1, askAmt2)

                fee = FEE_RATE * spot * units
                optionPrice1 = bid1 * spot  # short call
                optionPrice2 = ask2 * spot  # long call

                maxProfit = units * (optionPrice1 - optionPrice2) - fee - fee
                maxLoss = units * (s1 + optionPrice1 - s2 - optionPrice2 ) - fee - fee

                m = (maxLoss - maxProfit) / (s2 - s1)
                c = maxProfit - (m * s1)
                boundary = -1 * (c / m)
                if charts:
                    INTERVAL = 50
                    START = s1 - INTERVAL - 10
                    END = s2 + INTERVAL + 10
                    RANGE = range(START, END, INTERVAL)
                    SPOT_PRICE_RANGE = pd.Series(RANGE)

                    short = SC(s1, units, SPOT_PRICE_RANGE, bid1, spot)
                    long = LC(s2,units,SPOT_PRICE_RANGE,ask2, spot)
                    total = short + long

                if maxProfit < 0:
                    if verbose: print('100% Loss')
                    continue
                elif maxLoss > 0:
                    print('@@@@@@@@@@@@@@@@ 100% Win @@@@@@@@@@@@@@@@@')
                    boundary = 999999999
                else:
                    if boundary <= ((1 + TOL) * spot):
                        continue
                #     print('Profit if below %i'%(boundary))
                # print('Max: %i'%(maxProfit), 'Min: %i'%(maxLoss))
                # print('Sell Call: Strike', s1, 'at', bid1, '|| Buy Call:',s2,'at',ask2,'|| Units:',units)
                # print()

                if charts:
                    title = 'BTC-' + d + '<br>' + '%.2f'%(spot)
                    plotStuff(SPOT_PRICE_RANGE, [short, long], total=total, names=['Short Call', 'Long Call'], title=title)

                z_results.append([boundary, maxProfit/units, maxProfit, maxLoss, 'Sell Call', s1, ask1, 'Buy Call', s2, bid2, units])

        z_df = pd.DataFrame(z_results, columns=['Profit if below', 'unitProfit', 'maxProfit', 'maxLoss',
                                                'Order 1 Type', 'Strike 1', 'Price 1',
                                                'Order 2 Type', 'Strike 2', 'Price 2',
                                                'units'])

        z_df = z_df.sort_values(by=['Profit if below'], ascending=False)
        print(z_df)
        print()
    #endregion



def bare(test = False, dates = [], charts = False, verbose = False, useProphet = False):

    if test:
        uri = 'wss://test.deribit.com/ws/api/v2'
        print('===  TESTNET  ===')
    else:
        uri = 'wss://www.deribit.com/ws/api/v2'
        print('===  MAINNET  ===')

    handler = Handler(uri)

    instruments = getInstruments(handler)

    for d in dates:
        dd = d
        d = d.strftime('%-d%b%y').upper()
        print('===',d,'===')

        # all[d + '_CALL'] = []
        # all[d + '_PUT'] = []
        strikes = []

        s_results = []
        z_results = []

        for instr in instruments:
            if instr['instrument_name'] == "BTC-" + d + '-' + str(int(instr['strike'])) + '-' + 'C':
                strikes.append(int(instr['strike']))

        strikes.sort(reverse=False)
        l = len(strikes)
        spot = getSpot(handler)

        print('=== Index:', spot, '===')

        if useProphet:
            print('=== Using Prophet... ===')
            yhat, upper, lower = forecast.forecast(dd, showPlot=False, histPeriodDays=750, periodsAhead=1000)
            lowerBound = lower
            upperBound = upper


        else:
            print('=== Using Tolerance ± %.1f %%===' % (TOL * 100.0))
            lowerBound = (1 - TOL) * spot
            upperBound = (1 + TOL) * spot

        print('=== Lower Bound: %i' % (lowerBound), '===')
        print('=== Upper Bound: %i' % (upperBound), '===')


        # Put Vertical S (Bull)


        for j in range(l):
            s2 = strikes[j]
            bid2, bidAmt2, ask2, askAmt2 = getQuotes(handler, d, s2, 'P')

            if verbose: print(s2)

            if bid2 <= 0:
                if verbose: print('s2 price N.A')
                continue

            if (lowerBound <= s2):
                if verbose: print(s2)
                if verbose: print('Not in range')
                continue

            units = bidAmt2

            fee = FEE_RATE * spot * units
            optionPrice2 = bid2 * spot      #short put

            maxProfit = units * (optionPrice2) - fee

            boundary = s2 + FEE_RATE - optionPrice2

            unitProfit = maxProfit/units
            unitPercentGain = (unitProfit/spot) * 10 * 100

            if charts:
                INTERVAL = 5
                START = s2 - INTERVAL - 500
                END = s2 + INTERVAL + 500
                RANGE = range(START, END, INTERVAL)
                SPOT_PRICE_RANGE = pd.Series(RANGE)

                short = SP(s2, units, SPOT_PRICE_RANGE, bid2, spot)


            if maxProfit < 0:
                if verbose: print('100% Loss')
                continue

            if charts:
                title = 'BTC-' + d + '<br>' + '%.2f' % (spot)
                plotStuff(SPOT_PRICE_RANGE, [short], total=None, names=['Short Put'],
                          title=title)

            s_results.append([boundary, unitPercentGain, unitProfit, maxProfit, 'Sell Put', s2, bid2, units])

        s_df = pd.DataFrame(s_results, columns=['Profit if above', 'percent gain(%%)','unitProfit', 'maxProfit',
                                                'Order 2 Type', 'Strike 2', 'Price 2',
                                                'units'])

        s_df = s_df.sort_values(by=['Profit if above'])
        print(s_df)
        print()


    #region:Call Vertical Z (Bear)
        for i in range(l):
            s1 = strikes[i]
            bid1, bidAmt1, ask1, askAmt1 = getQuotes(handler, d, s1, 'C')
            if bid1 <= 0:
                if verbose: print('s1 price N.A')
                continue

            if (upperBound >= s1):
                if verbose: print(s1)
                if verbose: print('Not in range')
                continue

            units = bidAmt1

            fee = FEE_RATE * spot * units
            optionPrice1 = bid1 * spot  # short call

            maxProfit = units * (optionPrice1) - fee

            boundary = optionPrice1 - FEE_RATE + s1

            unitProfit = maxProfit / units
            unitPercentGain = (unitProfit / spot) * 10 * 100

            if charts:
                    INTERVAL = 50
                    START = s1 - INTERVAL - 10
                    END = s1 + INTERVAL + 10
                    RANGE = range(START, END, INTERVAL)
                    SPOT_PRICE_RANGE = pd.Series(RANGE)

                    short = SC(s1, units, SPOT_PRICE_RANGE, bid1, spot)

            if maxProfit < 0:
                if verbose: print('100% Loss')
                continue

            if charts:
                title = 'BTC-' + d + '<br>' + '%.2f'%(spot)
                plotStuff(SPOT_PRICE_RANGE, [short], total=None, names=['Short Call'], title=title)

            z_results.append([boundary, unitPercentGain, unitProfit, maxProfit, 'Sell Call', s1, bid1,  units])

        z_df = pd.DataFrame(z_results, columns=['Profit if below', 'percent gain(%%)','unitProfit', 'maxProfit',
                                                'Order 1 Type', 'Strike 1', 'Price 1',
                                                'units'])

        z_df = z_df.sort_values(by=['Profit if below'], ascending=False)
        print(z_df)
        print()
    #endregion



if __name__ == '__main__':

    # uri = 'wss://www.deribit.com/ws/api/v2'
    # handler = Handler(uri)
    # res = getInstruments(handler)
    #
    # for r in res:
    #     print(r)
    #
    # exit()

    # yhat, upper, lower = forecast.forecast(d, showPlot=False, histPeriodDays=500, periodsAhead=40 * 24 /4)
    #     print('************************************************')
    #     print(d, 'yhat:', yhat, 'upper:', upper, 'lower', lower, '||', 'spot', spot)
    #     print('************************************************')
    #     print()

    dates = [
        datetime.datetime(2020, 6, 20, 8),
        # datetime.datetime(2020, 6, 5, 8),
    ]

    begin = time.time()

    bare(
        test=       False,
        dates=      dates,
        charts=     False,
        verbose=    False,
        useProphet= True,
         )

    # verticals(
    #     test=False,
    #      dates=dates,
    #      charts=False,
    #      verbose=False,
    #      )

    end = time.time()

    print('Time taken: %.2f'%(end-begin))