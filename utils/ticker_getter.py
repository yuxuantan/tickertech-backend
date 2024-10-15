import pandas as pd
import yfinance as yf

from pytickersymbols import PyTickerSymbols
from get_all_tickers import get_tickers as gt


import yfinance as yf
import time
import random

def fetch_stock_data(ticker, period="max", interval="1d", retries=3, backoff_factor=2) -> pd.DataFrame:
    """
    Fetch stock data for a given ticker. If the first attempt fails, it retries up to `retries` times
    with exponential backoff (delays between retries).
    
    Parameters:
    ticker (str): Stock ticker symbol.
    period (str): Data period to fetch (e.g., '1d', '5d', 'max').
    interval (str): Data interval (e.g., '1d', '1wk', '1mo').
    retries (int): Number of retry attempts.
    backoff_factor (int): Factor by which to increase the delay between retries.

    Returns:
    pd.DataFrame: Stock data as a pandas DataFrame, or None if failed.
    """
    # time.sleep(3)  # Random sleep to avoid overloading the server
    for attempt in range(retries):
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=False,
                prepost=False,
                threads=True,
                proxy=None,
            )
            if not data.empty:
                print(f"✅ Fetched data for {ticker}.")
                return data
            else:
                print(f"❌ No data found for {ticker}.")
                return None

        except Exception as e:
            print(f"😡 Failed to fetch data for {ticker} on attempt {attempt+1}. Error: {str(e)}")
            
            if attempt < retries - 1:  # Only backoff if we are not on the last attempt
                sleep_time = backoff_factor ** attempt + random.uniform(0, 1)
                print(f"Retrying after {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"❌ All attempts failed for {ticker}. Moving on.")
                return None



# @st.cache_data(ttl="1d")
# import requests


def fetch_next_earnings_date(ticker_symbol):
    # Fetch the stock data
    stock = yf.Ticker(ticker_symbol)

    # Get the earnings dates DataFrame
    earnings_dates_df = stock.earnings_dates

    # Ensure the current time has the same timezone as the earnings dates DataFrame

    # Get the next upcoming earnings date by filtering dates greater than current time
    if earnings_dates_df is not None and not earnings_dates_df.empty:
        current_time = pd.Timestamp.now().tz_localize(earnings_dates_df.index.tz)
        next_earnings_date = earnings_dates_df[
            earnings_dates_df.index > current_time
        ].index.min()
        return next_earnings_date
    else:
        print(f"No earnings dates found for {ticker_symbol}")
        return None


def get_all_tickers():
    # # fetch from file sec_company_tickers.json
    # url = "sec_company_tickers.json"
    # data = pd.read_json(url)
    # # switch row and column
    # data = data.T
    # # get ticker symbols
    # tickers = data['ticker'].tolist()

    tickers = gt.get_tickers()
    # exclude all tickers which are not characters
    tickers = [ticker for ticker in tickers if ticker.isalpha()]
    return tickers


# @st.cache_data(ttl="1d")
def get_snp_500():
    stock_data = PyTickerSymbols()
    sp500_tickers = [
        stock["symbol"] for stock in stock_data.get_stocks_by_index("S&P 500")
    ]
    return sp500_tickers


# @st.cache_data(ttl="1d")
def get_dow_jones():
    stock_data = PyTickerSymbols()
    dow_jones_tickers = [
        stock["symbol"] for stock in stock_data.get_stocks_by_index("Dow Jones")
    ]
    return dow_jones_tickers
