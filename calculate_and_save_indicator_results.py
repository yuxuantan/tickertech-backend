import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytz
import numpy as np
import pandas as pd
import utils.ticker_getter as tg
import utils.supabase as db
import utils.indicator_helpers as iu
import utils.indicators as ie


def calculate_and_save_indicator_results():
    stock_list = tg.get_all_tickers()

    # Fetch cached data from Supabase
    apex_bull_appear_cache = db.fetch_cached_data_from_supabase("apex_bull_appear")
    apex_bull_raging_cache = db.fetch_cached_data_from_supabase("apex_bull_raging")
    apex_bear_appear_cache = db.fetch_cached_data_from_supabase("apex_bear_appear")
    apex_bear_raging_cache = db.fetch_cached_data_from_supabase("apex_bear_raging")

    def filter_tickers(cache, description):
        sgt = pytz.timezone("Asia/Singapore")
        today_sgt = datetime.now(sgt).replace(hour=5, minute=0, second=0, microsecond=0)

        filtered_tickers = [
            ticker["ticker"]
            for ticker in cache
            if datetime.fromisoformat(
                ticker["created_at"].split(".")[0] + "+00:00"
            ).astimezone(sgt)
            > today_sgt
        ]
        print(f"Tickers no need to screen {description}: {len(filtered_tickers)}")
        return list(set(stock_list) - set(filtered_tickers))

    tickers_to_screen = {
        "bull_appear": filter_tickers(apex_bull_appear_cache, "bull appear"),
        "bull_raging": filter_tickers(apex_bull_raging_cache, "bull raging"),
        "bear_appear": filter_tickers(apex_bear_appear_cache, "bear appear"),
        "bear_raging": filter_tickers(apex_bear_raging_cache, "bear raging"),
    }

    for key, tickers in tickers_to_screen.items():
        print(f"Tickers to screen for {key.replace('_', ' ')}: {len(tickers)}")

    # Track total tickers to screen
    total_unique_tickers_to_screen = len(set(sum(tickers_to_screen.values(), [])))
    tickers_screened = {key: 0 for key in tickers_to_screen}
    tickers_screened_total = 0

    ticker_screened_lock = threading.Lock()

    # Synchronous fetching
    def process_ticker_synchronously(ticker):
        try:
            ticker_data = tg.fetch_stock_data(ticker)  # Fetch data synchronously
            return ticker_data
        except Exception as e:
            print(f"❌ Failed to fetch data for {ticker}: {e}")
            return None

    # Concurrent analysis
    def analyze_ticker(ticker, ticker_data):
        nonlocal tickers_screened_total
        ticker_processed = False

        try:
            for indicator, (get_dates_func, table_name) in {
                "bull_appear": (ie.get_apex_bull_appear_dates, "apex_bull_appear"),
                "bull_raging": (ie.get_apex_bull_raging_dates, "apex_bull_raging"),
                "bear_appear": (ie.get_apex_bear_appear_dates, "apex_bear_appear"),
                "bear_raging": (ie.get_apex_bear_raging_dates, "apex_bear_raging"),
            }.items():
                if ticker in tickers_to_screen[indicator]:
                    dates = get_dates_func(ticker_data)
                    analysis_result = iu.get_analysis_results(dates, ticker_data)
                    analysis_result = convert_to_serializable(analysis_result)

                    # if analysis_result:
                    db.upsert_data_to_supabase(
                        table_name,
                        {
                            "ticker": ticker,
                            "dates": dates,
                            # "analysis": analysis_result,
                            "created_at": "now()",
                        },
                    )
                    print(f"Upserted {indicator} analysis for {ticker}")
                    # else:
                    # print(f"No {indicator} analysis to upsert for {ticker}")

                    with ticker_screened_lock:
                        tickers_screened[indicator] += 1
                        if not ticker_processed:
                            tickers_screened_total += 1
                            ticker_processed = True

        except Exception as e:
            print(f"❌ Failed to process ticker {ticker} during analysis: {e}")

        # Print progress after every analysis
        with ticker_screened_lock:
            print(
                f"Progress: {tickers_screened_total}/{total_unique_tickers_to_screen} tickers screened"
            )
            for key, count in tickers_screened.items():
                print(
                    f"Progress for {key.replace('_', ' ')}: {count}/{len(tickers_to_screen[key])} tickers screened"
                )

    # Fetch data synchronously and analyze concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        for ticker in set(sum(tickers_to_screen.values(), [])):
            ticker_data = process_ticker_synchronously(
                ticker
            )  # Synchronously fetch data
            if ticker_data is not None:
                # Analyze ticker data concurrently
                executor.submit(analyze_ticker, ticker, ticker_data)


def convert_to_serializable(data):
    if isinstance(data, dict):
        return {k: convert_to_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_serializable(i) for i in data]
    elif isinstance(data, pd.Timestamp):
        return data.isoformat()
    elif isinstance(data, np.int64):
        return int(data)
    elif isinstance(data, np.float64):
        return float(data)
    else:
        return data


calculate_and_save_indicator_results()
