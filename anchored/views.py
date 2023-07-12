
import os 
import datetime as dt
import requests
import pandas as pd
import numpy as np
import time

from django.shortcuts import render
from django.http import JsonResponse
from dateutil.relativedelta import relativedelta
from scipy.signal import argrelextrema
from dtaidistance import dtw

from dotenv import load_dotenv



load_dotenv()
#fantasy labs username
EOD = os.getenv("EOD")


def get_daily_equity(request):

    stock_ticker = request.GET.get('stock_ticker', 'AAPL')
    anchor_date = request.GET.get('anchor_date', dt.datetime.today().strftime('%Y-%m-%d'))

    stop = dt.datetime.today()
    start = stop - relativedelta(years=1)

    req = requests.get('https://eodhistoricaldata.com/api/eod' +
                       '/{0}.US?api_token={1}&fmt=json'.format(stock_ticker, EOD) +
                       '&period=d&from={0}&to={1}'.format(start.strftime('%Y-%m-%d'),
                                                          stop.strftime('%Y-%m-%d')
                                                          ))
    df = pd.DataFrame.from_dict(req.json())

    df['adj_ratio'] = df['close']/df['adjusted_close']
    df['adjusted_open'] = (df['open']/df['adj_ratio']).round(2)
    df['adjusted_high'] = (df['high']/df['adj_ratio']).round(2)
    df['adjusted_low'] = (df['low']/df['adj_ratio']).round(2)


    #get index values for all custom vwaps
    max_idx = argrelextrema(df['adjusted_close'].values, np.greater, order=1)[0]
    max_values = [df['adjusted_close'].iloc[x] for x in max_idx]
    maxloc = max_idx[max_values.index(max(max_values))]
    min_idx = argrelextrema(df['adjusted_close'].values, np.less, order=1)[0]
    min_values = [df['adjusted_close'].iloc[x] for x in min_idx]
    minloc = min_idx[min_values.index(min(min_values))]

    try:
        customloc = df[df['date']==anchor_date].index[0]
    except:
        customloc = None

    vol_nodes = df['volume'].iloc[125:].nlargest(1).index



    df['vwap_maxloc'] = (df['adjusted_close'] * df['volume']).iloc[maxloc:].expanding().sum() / \
                      df['volume'].iloc[maxloc:].expanding().sum()
    df['vwap_minloc'] = (df['adjusted_close'] * df['volume']).iloc[minloc:].expanding().sum() / \
                      df['volume'].iloc[minloc:].expanding().sum()
    if customloc != None:
        df['vwap_customloc'] = (df['adjusted_close'] * df['volume']).iloc[customloc:].expanding().sum() / \
                        df['volume'].iloc[customloc:].expanding().sum()
    
    df['vwap_highvol'] = (df['adjusted_close'] * df['volume']).iloc[vol_nodes[0]:].expanding().sum() / \
                      df['volume'].iloc[vol_nodes[0]:].expanding().sum()
    
    df['date'] = df['date'].apply(lambda x: int(time.mktime(dt.datetime.strptime(x, "%Y-%m-%d").timetuple())))
    data = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','adjusted_open','adjusted_high', 'adjusted_low','adjusted_close']].values.tolist()]
    maxloc = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','vwap_maxloc','vwap_maxloc','vwap_maxloc','vwap_maxloc']].dropna().values.tolist()]
    minloc = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','vwap_minloc','vwap_minloc','vwap_minloc','vwap_minloc']].dropna().values.tolist()]
    if customloc != None:
        customloc = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','vwap_customloc','vwap_customloc','vwap_customloc','vwap_customloc']].dropna().values.tolist()]
    volloc = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','vwap_highvol','vwap_highvol','vwap_highvol','vwap_highvol']].dropna().values.tolist()]
    
    if customloc != None:
        context = {
            "data": data,
            "maxloc":maxloc,
            "minloc":minloc,
            "volloc":volloc,
            'stock': stock_ticker,
            'anchor_date':anchor_date,
            "miny": df['adjusted_low'].min()*.98,
            "maxy": df['adjusted_high'].max()*1.02,
            "customloc":customloc
            }
    else:
        context = {
            "data": data,
            "maxloc":maxloc,
            "minloc":minloc,
            "volloc":volloc,
            'stock': stock_ticker,
            'anchor_date':anchor_date,
            "miny": df['adjusted_low'].min()*.98,
            "maxy": df['adjusted_high'].max()*1.02,    
            }


    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context)
    else:
        return render(request, 'index.html', context=context)
    
def get_analogs(request):
    
    stock_ticker = request.GET.get('stock_ticker_analog', '')

    if stock_ticker != '':

        stop = dt.datetime.today()
        start = stop - relativedelta(years=10)

        req = requests.get('https://eodhistoricaldata.com/api/eod' +
                            '/{0}.US?api_token={1}&fmt=json'.format(stock_ticker, EOD) +
                            '&period=d&from={0}&to={1}'.format(start.strftime('%Y-%m-%d'),
                                                                stop.strftime('%Y-%m-%d')
                                                                ))
        df = pd.DataFrame.from_dict(req.json())


        # Compute log-returns
        df['Return'] = df['adjusted_close'].pct_change()
        df['LogReturn'] = np.log1p(df['adjusted_close'].pct_change())



        df = df.dropna()

        # Get the log-returns for the last 90 days
        current_period = df.tail(90)['LogReturn'].to_numpy()

        # Initialize the top 10 best matches list
        top_matches = pd.DataFrame([], columns=['start','stop','distance'])

        # Loop over historical periods and find the best matches
        for i in range(90, len(df) - 90):

            historical_period = df.iloc[i-90:i][['adjusted_close','LogReturn']]
            distance = dtw.distance(current_period, historical_period['LogReturn'].to_numpy())
            
            top_matches.loc[i,'start'] = i-90
            top_matches.loc[i,'stop'] = i
            top_matches.loc[i,'distance'] = distance

            top_matches.sort_values('distance',inplace=True)
            top_matches.reset_index(drop=True,inplace=True)

        top_ten_filtered = pd.DataFrame([], columns=['start','stop','distance'])
        top_ten_filtered.loc[i,'start'] = top_matches.loc[0,'start']
        top_ten_filtered.loc[i,'stop'] = top_matches.loc[0,'stop']
        top_ten_filtered.loc[i,'distance'] = top_matches.loc[0,'distance']

        count=0
        for i in top_matches.index[1:]:
            if all([(abs((l - top_matches.loc[i,'start']))>20) for l in top_ten_filtered['start']])==True:
                top_ten_filtered.loc[i,'start'] = top_matches.loc[i,'start']
                top_ten_filtered.loc[i,'stop'] = top_matches.loc[i,'stop']
                top_ten_filtered.loc[i,'distance'] = top_matches.loc[i,'distance']
                count+=1
                if count>8:
                    break

        # Calculate the forecast for the top 10 best matches

        current_w_projs = []
        for match, ix in zip(top_ten_filtered.index, np.arange(len(top_ten_filtered))):
            historical_period = df.iloc[top_ten_filtered.loc[match]['start']:top_ten_filtered.loc[match]['stop']+30].reset_index(drop=True)
            
            combo = pd.concat([df.tail(90)['Return'],historical_period.iloc[-30:]['Return']]).reset_index(drop=True)
            combo.name = ix

            current_w_projs.append(combo)

        data = pd.concat(current_w_projs,axis=1)
        data['average'] = data.mean(axis=1)
        data['median'] = data.median(axis=1)
        data_proj_only = data.iloc[-30:]
        data = (1+data).cumprod()

        context = {
            "average": data['average'].values.tolist(),
            "median": data['median'].values.tolist(),
            "bestfit": data[0].values.tolist(),
            'stock': stock_ticker,
            }
    else:

        context = {
            "average": [],
            'stock': 'Enter Stock Ticker To Calulcate Analog',
            }
        

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context)
    else:
        return render(request, 'analogs.html', context=context)

def rolling_comparison(request):

    stock1 = request.GET.get('stock1', 'RSP')
    stock2 = request.GET.get('stock2', 'SPY')

    stop = dt.datetime.today()
    start = stop - relativedelta(years=10)

    req1 = requests.get('https://eodhistoricaldata.com/api/eod' +
                       '/{0}.US?api_token={1}&fmt=json'.format(stock1, EOD) +
                       '&period=d&from={0}&to={1}'.format(start.strftime('%Y-%m-%d'),
                                                          stop.strftime('%Y-%m-%d')
                                                          ))
    req2 = requests.get('https://eodhistoricaldata.com/api/eod' +
                       '/{0}.US?api_token={1}&fmt=json'.format(stock2, EOD) +
                       '&period=d&from={0}&to={1}'.format(start.strftime('%Y-%m-%d'),
                                                          stop.strftime('%Y-%m-%d')
                                                          ))
    num = pd.DataFrame.from_dict(req1.json())
    num['adj_ratio'] = num['close']/num['adjusted_close']
    num['adjusted_open'] = (num['open']/num['adj_ratio']).round(2)
    num['adjusted_high'] = (num['high']/num['adj_ratio']).round(2)
    num['adjusted_low'] = (num['low']/num['adj_ratio']).round(2)

    denom = pd.DataFrame.from_dict(req2.json())

    num['date'] = num['date'].apply(lambda x: int(time.mktime(dt.datetime.strptime(x, "%Y-%m-%d").timetuple())))
    denom['date'] = denom['date'].apply(lambda x: int(time.mktime(dt.datetime.strptime(x, "%Y-%m-%d").timetuple())))
    num.set_index('date', inplace=True)
    denom.set_index('date', inplace=True)

    df = (num['adjusted_close'].pct_change(periods=8).rank(pct=True)-denom['adjusted_close'].pct_change(periods=8).rank(pct=True)).reset_index()
    fiftydf = (num['adjusted_close'].pct_change(periods=55).rank(pct=True)-denom['adjusted_close'].pct_change(periods=55).rank(pct=True)).reset_index()
    eightydf = (num['adjusted_close'].pct_change(periods=89).rank(pct=True)-denom['adjusted_close'].pct_change(periods=89).rank(pct=True)).reset_index()

    data = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in num.reset_index()[['date','adjusted_open','adjusted_high', 'adjusted_low','adjusted_close']].values.tolist()]
    dfdata = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df.dropna()[['date','adjusted_close','adjusted_close', 'adjusted_close','adjusted_close']].values.tolist()]
    fiftydata = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in fiftydf.dropna()[['date','adjusted_close','adjusted_close', 'adjusted_close','adjusted_close']].values.tolist()]
    eightydata = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in eightydf.dropna()[['date','adjusted_close','adjusted_close', 'adjusted_close','adjusted_close']].values.tolist()]
    
    high = (df.quantile(.95)['adjusted_close'] + fiftydf.quantile(.95)['adjusted_close'] + eightydf.quantile(.95)['adjusted_close'])/3
    low = (df.quantile(.05)['adjusted_close'] + fiftydf.quantile(.05)['adjusted_close'] + eightydf.quantile(.05)['adjusted_close'])/3
    context = {'data':data,
               'df1':dfdata,
               'df2':fiftydata,
               'df3':eightydata,
               "miny": -1,
               "maxy": 1,
               "num":stock1,
               "denom":stock2,
               "high":high,
               "low":low,
               }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context)
    else:
        return render(request, 'relative.html', context=context)

def landing(request):
    return render(request, 'landing.html')

   

    
  