
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

from dotenv import load_dotenv



load_dotenv()
#fantasy labs username
EOD = os.getenv("EOD")


def get_daily_equity(request):

    stock_ticker = request.GET.get('stock_ticker', 'AAPL')

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

    max_idx = argrelextrema(df['adjusted_close'].iloc[:-14].values, np.greater, order=14)[0]
    max_values = [df['adjusted_close'].iloc[x] for x in max_idx]
    maxloc = max_idx[max_values.index(max(max_values))]
    min_idx = argrelextrema(df['adjusted_close'].values, np.less, order=14)[0]
    min_values = [df['adjusted_close'].iloc[x] for x in min_idx]
    minloc = min_idx[min_values.index(min(min_values))]

    vol_nodes = df['volume'].iloc[125:].nlargest(1).index

    df['vwap_maxloc'] = (df['adjusted_close'] * df['volume']).iloc[maxloc:].expanding().sum() / \
                      df['volume'].iloc[maxloc:].expanding().sum()
    df['vwap_minloc'] = (df['adjusted_close'] * df['volume']).iloc[minloc:].expanding().sum() / \
                      df['volume'].iloc[minloc:].expanding().sum()
    
    df['vwap_highvol'] = (df['adjusted_close'] * df['volume']).iloc[vol_nodes[0]:].expanding().sum() / \
                      df['volume'].iloc[vol_nodes[0]:].expanding().sum()
    
    df['date'] = df['date'].apply(lambda x: int(time.mktime(dt.datetime.strptime(x, "%Y-%m-%d").timetuple())))
    data = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','adjusted_open','adjusted_high', 'adjusted_low','adjusted_close']].values.tolist()]
    maxloc = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','vwap_maxloc','vwap_maxloc','vwap_maxloc','vwap_maxloc']].dropna().values.tolist()]
    minloc = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','vwap_minloc','vwap_minloc','vwap_minloc','vwap_minloc']].dropna().values.tolist()]
    volloc = [[int(x[0]*1000),x[1],x[2],x[3],x[4]] for x in df[['date','vwap_highvol','vwap_highvol','vwap_highvol','vwap_highvol']].dropna().values.tolist()]
    context = {
        "data": data,
        "maxloc":maxloc,
        "minloc":minloc,
        "volloc":volloc,
        'stock': stock_ticker,
        "miny": df['adjusted_low'].min()*.98,
        "maxy": df['adjusted_high'].max()*1.02
        }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context)
    else:
        return render(request, 'index.html', context=context)
    

def landing(request):
    return render(request, 'landing.html')
    

    
  