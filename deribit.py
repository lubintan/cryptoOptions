import asyncio
import websockets
import json

# '''
# Deribit Options Format: BTC-22MAY20-12000-C
# '''


async def call_api(msg):
    # async with websockets.connect('wss://test.deribit.com/ws/api/v2') as websocket:
    async with websockets.connect('wss://www.deribit.com/ws/api/v2') as websocket:
       await websocket.send(msg)
       while websocket.open:
            response = await websocket.recv()
            # do something with the response...
            response = json.loads(response)
            try:
                return response['result']
            except:
                print(response)
                exit(1)

def deribitOptionsData(expiry, strike, callPut):
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
    response = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(msg)))

    ask = response['best_ask_price']
    bid = response['best_bid_price']
    delta = response['greeks']['delta']

    return ask,bid,delta

def deribitInstr():
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
    instr = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(msg)))

    return instr


def deribitHV():
    msg = \
        {
            "jsonrpc": "2.0",
            "id": 8387,
            "method": "public/get_historical_volatility",
            "params": {
                "currency": "BTC"
            }
        }
    hv = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(msg)))

    return float(hv[0][1])

def deribitBTCindex():
    msg = \
        {"jsonrpc": "2.0",
         "method": "public/get_index",
         "id": 42,
         "params": {
             "currency": "BTC"}
         }
    spot = asyncio.get_event_loop().run_until_complete(call_api(json.dumps(msg)))

    return float(spot['BTC'])

def deribitStrikes(expiry, callPut):

    instr = deribitInstr()

    strikes = []

    for i in instr:
        if i['instrument_name'] == "BTC-" + expiry + '-' + str(int(i['strike'])) + '-' + callPut:
            strikes.append(int(i['strike']))
    strikes.sort()

    return strikes

if __name__ == '__main__':
    print(deribitInstr())