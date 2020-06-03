import datetime
import time
import json
import math
import pandas as pd
import numpy as np
from pandas_datareader import data as fin_data
from time import sleep
from datetime import timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from sklearn.linear_model import LinearRegression

from django.conf import settings
from django.utils import timezone

# 3rd Party APIs
from yahoo_earnings_calendar import YahooEarningsCalendar
import yfinance as yf
from finta import TA


from .models import IndicesData, StockData
from .k_utils import change_check, gap_1_check, date_obj_to_date, week_values, week_color

class Stock():

    def __init__(self, ticker,stock_id, table_index, ):
        self.today = datetime.datetime.today()
        self.ticker = ticker
        self.stock_id = stock_id
        self.table_index = 1
        self.date = ''
        self.displayed_date = ''

        self.stock_price = None
        self.prev_close = None
        self.todays_open = None

        self.trend_30 = None
        self.trend_14 = None
        self.macd_30 = None
        self.macd_14 = None
        self.mfi_30 = None
        self.mfi_14 = None

        self.week_1 = None
        self.week_1_min = None
        self.week_1_max = None

        self.week_2 = None
        self.week_2_min = None
        self.week_2_max = None

        self.week_3 = None
        self.week_3_min = None
        self.week_3_max = None

        self.week_5 = None
        self.week_5_min =None
        self.week_5_max = None

        self.week_1_color = ''
        self.week_2_color = ''
        self.week_3_color = ''
        self.week_5_color = ''

        self.gap_1 = None
        self.gap_1_color = ''
        # updading_gap_1_flag = models.BooleanField(default=False, null=True)

        self.macd_30_clash = False
        self.macd_14_clash = False

        self.macd_30_color = ''
        self.macd_14_color = ''

        self.mfi_30_clash = False
        self.mfi_14_clash = False

        self.mfi_30_color = ''
        self.mfi_14_color = ''

        self.rsi = None
        self.rsi_color = ''

        self.earnings_call = None
        self.earnings_call_displayed = ''
        self.earnings_warning = ''

        self.dividend_date = ''
        self.dividend = None
        self.dividend_warning = ''
    
    def update_stock(self):
    
        self.stock_df = fin_data.get_data_yahoo(str(self.ticker), start=self.today - timedelta(44), end=self.today)

        self.stock_price = round(self.stock_df.loc[self.stock_df.index[-1]]['Close'],2)

        # self.prev_close = round(self.stock_df.loc[self.stock_df.index[-2]]['Close'],2)
        # self.todays_open = round(self.stock_df.loc[self.stock_df.index[-1]]['Open'],2)

        self.prev_close = StockData.objects.filter(ticker=self.ticker).first().prev_close
        self.todays_open = StockData.objects.filter(ticker=self.ticker).first().todays_open
        self.gap_1, self.gap_1_color = gap_1_check(self.prev_close, self.todays_open)

        self.date = self.stock_df.index[-1]

        
        self.date = self.stock_df.index[-1]
        self.displayed_date = date_obj_to_date(pd.Timestamp("today"), date_format='slash')

        self.week_1, self.week_1_min, self.week_1_max = week_values(self.stock_df, 90)
        self.week_2, self.week_2_min, self.week_2_max = week_values(self.stock_df, 10)
        self.week_3, self.week_3_min, self.week_3_max = week_values(self.stock_df, 15)
        self.week_5, self.week_5_min, self.week_5_max = week_values(self.stock_df, 25)

        self.week_1_color = week_color(self.week_1, week3=True)
        self.week_2_color = week_color(self.week_2)
        self.week_3_color = week_color(self.week_3, week3=True)
        self.week_5_color = week_color(self.week_5)

        self.trend_30 = self.stock_regression(30)
        self.trend_14 = self.stock_regression(14)

        self.macd_30 = self.macd_regression(30)
        self.macd_14 = self.macd_regression(14)

        self.mfi_30 = self.mfi_regression(30)
        self.mfi_14 = self.mfi_regression(14)

        tan_deviation_angle = math.tan(math.radians(settings.DEVIATION_ANGLE))

        # MACD
        if np.abs(self.macd_30) > tan_deviation_angle:                    

            if (self.trend_30 > 0 and self.macd_30 < 0) or (self.trend_30 < 0 and self.macd_30 > 0):
                self.macd_30_clash = True
                self.macd_30_color = 'red'
            elif (self.trend_30 < 0 and self.macd_30 < 0) or (self.trend_30 > 0 and self.macd_30 > 0):
                self.macd_30_clash = False
                self.macd_30_color = 'green'
        else:
            self.macd_30_clash = False
            self.macd_30_color = 'green'

        if np.abs(self.macd_14) > tan_deviation_angle:                    

            if (self.trend_14 > 0 and self.macd_14 < 0) or (self.trend_14 < 0 and self.macd_14 > 0):
                self.macd_14_clash = True
                self.macd_14_color = 'red'
            elif (self.trend_14 < 0 and self.macd_14 < 0) or (self.trend_14 > 0 and self.macd_14 > 0):
                self.macd_14_clash = False
                self.macd_14_color = 'green'
        else:
            self.macd_14_clash = False
            self.macd_14_color = 'green'

        # MFI
        if np.abs(self.mfi_30) > tan_deviation_angle:                    

            if (self.trend_30 > 0 and self.mfi_30 < 0) or (self.trend_30 < 0 and self.mfi_30 > 0):
                self.mfi_30_clash = True
                self.mfi_30_color = 'red'
            elif (self.trend_30 < 0 and self.mfi_30 < 0) or (self.trend_30 > 0 and self.mfi_30 > 0):
                self.mfi_30_clash = False
                self.mfi_30_color = 'green'
        else:
            self.mfi_30_clash = False
            self.mfi_30_color = 'green'


        if np.abs(self.mfi_14) > tan_deviation_angle:                    

            if (self.trend_14 > 0 and self.mfi_14 < 0) or (self.trend_14 < 0 and self.mfi_14 > 0):
                self.mfi_14_clash = True
                self.mfi_14_color = 'red'
            elif (self.trend_14 < 0 and self.mfi_14 < 0) or (self.trend_14 > 0 and self.mfi_14 > 0):
                self.mfi_14_clash = False
                self.mfi_14_color = 'green'
        else:
            self.mfi_14_clash = False
            self.mfi_14_color = 'green'

        # RSI 
        self.rsi = self.last_rsi(30)
        
        if self.rsi > 0 and self.rsi <=30:
            self.rsi_color = 'red'
        elif self.rsi > 30 and self.rsi <= 65:
            self.rsi_color = 'orange'
        elif self.rsi > 65 and self.rsi <=100:
            self.rsi_color = 'green'
        else:
            self.rsi_color = ''

        self.earnings_warning = self.check_earnings_alert()
        self.dividend_warning = self.check_dividend_alert()


    def stock_regression(self, period):
        df = self.stock_df.tail(period).copy().reset_index()
        prices = df['Close'].tolist()
        dates = df.index.tolist()
        dates = np.reshape(dates, (len(dates),1))
        prices = np.reshape(prices, (len(prices),1))
        regressor = LinearRegression().fit(dates, prices)

        # Slop of Y = ax + b    
        a = regressor.coef_[0]
        return a
    
    def macd_regression(self,period):
        df = self.stock_df.tail(period).copy().reset_index()
        dates = df.index.tolist()
        dates = np.reshape(dates, (len(dates),1))
        df_ohlc = df.rename(columns={"High": "high", "Low": "low", 'Open':'open', 'Close':'close', 'Volume':'volume', 'Adj Close':'adj close'})
        df_macd = TA.MACD(df_ohlc)
        df_macd_list = df_macd['MACD'].tolist()
        df_macd_points = np.reshape(df_macd_list, (len(df_macd_list),1))

        macd_regressor = LinearRegression().fit(dates,df_macd_points)

        macd_a = macd_regressor.coef_[0]
        macd_b = macd_regressor.intercept_
        return macd_a
    
    def mfi_regression(self,period):
        df = self.stock_df.tail(period+14).copy().reset_index()
        dates = df.index.tolist()
        dates = np.reshape(dates, (len(dates),1))
        df_ohlc = df.rename(columns={"High": "high", "Low": "low", 'Open':'open', 'Close':'close', 'Volume':'volume', 'Adj Close':'adj close'})
        df_mfi = TA.MFI(df_ohlc,14)
        df_mfi.fillna(0, inplace=True)

        mfi_regressor = LinearRegression().fit(dates[-14:],df_mfi.values[-14:])
        
        mfi_a = mfi_regressor.coef_[0]
        mfi_b = mfi_regressor.intercept_
        return mfi_a

    def last_rsi(self, period):
        df = self.stock_df.tail(period).copy().reset_index()
        df_ohlc = df.rename(columns={"High": "high", "Low": "low", 'Open':'open', 'Close':'close', 'Volume':'volume', 'Adj Close':'adj close'})
        df_rsi = TA.RSI(df_ohlc,14)
        return round(df_rsi.tail(1).values[0],2)

    def check_dividend_alert(self):
        stock = StockData.objects.filter(ticker=self.ticker).first() # the "first" is because there might be same ticker two tables.
        dividend_date = stock.dividend_date

        try:
            # Convert from text date to timestamp
            dividend_ts = time.mktime(datetime.datetime.strptime(dividend_date, "%d/%m/%Y").timetuple())
            
            today_ts = datetime.datetime.timestamp(self.today)
            dividend_dt = datetime.datetime.fromtimestamp(dividend_ts)
            today_dt = datetime.datetime.fromtimestamp(today_ts)

            if (dividend_dt - today_dt).days <= 7 and (dividend_dt - today_dt).days >= 0:
                dividend_alert_signal = "blink-bg"
            elif (dividend_dt - today_dt).days < 0:
                dividend_alert_signal = "PAST"
            else:
                dividend_alert_signal = ""
        except Exception as e:
            print(f'Failed to find dividend for {self.ticker}. Reason: {e}')
            dividend_alert_signal = ""

        return dividend_alert_signal


    def check_earnings_alert(self):
        stock = StockData.objects.filter(ticker=self.ticker).first() # the "first" is because there might be same ticker two tables.
        # Removing the earnings alert for earnings date passed
        try:
            earnings_ts = datetime.datetime.timestamp(stock.earnings_call)
            today_ts = datetime.datetime.timestamp(self.today)
            earnings_dt = datetime.datetime.fromtimestamp(earnings_ts)
            today_dt = datetime.datetime.fromtimestamp(today_ts)
            
            if (earnings_dt - today_dt).days <= 7 and (earnings_dt - today_dt).days >= 0:
                earnings_alert_signal = "blink-bg"
            elif (earnings_dt - today_dt).days < 0:
                earnings_alert_signal = "PAST"
            else:
                earnings_alert_signal = ""
        except Exception as e:
            print(f'Failed to find earnings for {self.ticker}. Reason: {e}')
            earnings_alert_signal = ""
            # There is no earnings date registered, so checking if there is. 
            # Should run only when there is no earnings date in DB for that stock
            # TODO
            # Add check of stocks that have no earnings call in DB
            # stock_earnings_update(ticker)

        return earnings_alert_signal


    # def get_dividened(self):
    #     try:
    #         st = yf.Ticker(self.ticker).dividends.tail(1)
    #         stock_data.dividend = float(st.values)
    #         date_arr = str(st.index[0]).split(' ')[0].split('-')
    #         year = date_arr[0]
    #         month = date_arr[1]
    #         day = date_arr[2]
    #         self.dividend_date = day + '/' + month + '/' + year
    #     except:
    #         stock_data.dividend = None
    #         stock_data.dividend_date = None