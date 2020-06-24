import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.pylab import rcParams
plt.style.use('ggplot')
import _pickle as pickle
import getBinanceData, time, datetime

from fbprophet import Prophet as proph

def forecast(date=None, showPlot = False, histPeriodDays=30, periodsAhead=100):

    date = date.strftime('%Y-%m-%d %H:%M:%S')
    start = time.time()

    # Get data from binance
    ts = getBinanceData.getData('BTCUSDT', interval=getBinanceData.Client.KLINE_INTERVAL_4HOUR, minutes= histPeriodDays * 24 * 60)
    # print(ts.tail())

    # Resetting the index back so Dates are no longer indexed
    ts.reset_index(inplace=True)

    # Renaming the columns for use in FB prophet
    ts.rename(columns={'DateTime': 'ds', 'close': 'y'}, inplace=True)

    # Fitting and training
    mod = proph(interval_width=0.95,daily_seasonality=True,)

    #region:add daily
    # m = Prophet(weekly_seasonality=False)
    mod.fit(ts)
    #endregion

    # Setting up predictions to be made
    future = mod.make_future_dataframe(periods=periodsAhead, freq='4H')
    future.tail()

    # Making predictions
    forecast = mod.predict(future)

    forecast.to_csv('forecast.csv')

    end = time.time()

    print('Time taken: %.2f s' % (end - start))

    # Plotting the model
    if showPlot:
        mod.plot(forecast, uncertainty=True)
        plt.title('Facebook Prophet Forecast and Fitting')
        plt.show()

    selected = forecast.ds == date
    selected = forecast[selected]

    upper = selected.yhat_upper.values[0]
    lower = selected.yhat_lower.values[0]
    yhat = selected.yhat.values[0]

    return yhat, upper, lower

if __name__ == '__main__':
    date = datetime.datetime(year=2020, month=5, day=15, hour=8)
    yhat, upper ,lower = forecast(date)
    print(yhat, upper, lower)
    print((upper+lower)/2, yhat)
