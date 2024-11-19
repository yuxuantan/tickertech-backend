import utils.indicators as indicators
import utils.telegram_controller as tc
import time

# import utils.ticker_getter as tg
import requests
import pandas as pd

api_key = "94a3bc39c81e45dd9836712337cc5dec"

def calculate_latest_indicator_and_alert(symbol, interval, interval_units, output_size):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}{interval_units}&outputsize={output_size}&apikey={api_key}"
    print(f"fetching data from {url}")
    response = requests.get(url)
    data = response.json()["values"]

    # convert data which is a json array into dataframe with 'datetime' key as the index
    df = pd.DataFrame(data).set_index("datetime")
    # rename cols. first letter uppercase
    df.columns = [col.capitalize() for col in df.columns]
    # convert string to float
    df = df.astype(float)
    # convert index of df from string to Timedelta
    df.index = pd.to_datetime(df.index)

    # order by ascending date (index)
    df = df.sort_index(ascending=True)
    print(df.tail())


    analysis_results = {}
    print("calculating bull raging dates")
    analysis_results["apex_bull_raging"] = indicators.get_apex_bull_raging_dates(
        df, custom_aggregate_2days=False, flush_treshold=0.5, ratio_of_flush_bars_to_consider_raging=0.4
    )
    print("calculating bull appear dates")
    analysis_results["apex_bull_appear"] = indicators.get_apex_bull_appear_dates(
        df, custom_aggregate_2days=False, only_fetch_last=True
    )
    print("calculating bull uptrend dates")
    analysis_results["apex_bull_uptrend"] = indicators.get_apex_uptrend_dates(
        df, custom_aggregate_2days=False
    )
    print("calculating bear raging dates")
    analysis_results["apex_bear_raging"] = indicators.get_apex_bear_raging_dates(
        df, custom_aggregate_2days=False, flush_treshold=0.5, ratio_of_flush_bars_to_consider_raging=0.4
    )
    print("calculating bear appear dates")
    analysis_results["apex_bear_appear"] = indicators.get_apex_bear_appear_dates(
        df, custom_aggregate_2days=False, only_fetch_last=True
    )
    print("calculating bear downtrend dates")
    analysis_results["apex_bear_downtrend"] = indicators.get_apex_downtrend_dates(
        df, custom_aggregate_2days=False
    )

    for indicator, dates in analysis_results.items():

        if len(dates) == 0:
            print(f"skipping because no {indicator} detected")
            continue

        date = dates[-1]
        
        alert_recency_filter = 2 #bars

        if str(date) not in [str(df.index[-i]) for i in range(1, alert_recency_filter+1)]:
            print(f"skipping because last entry date for {indicator} is {date}, which is not last 2 bar")
            continue
        else:
             print(f"[ALERT] because last entry date for {indicator} is {date}, which is in last 2 bar")
        


        msg = f"🚨 {indicator} detected for {symbol}, {interval} {interval_units} chart!\n"
        msg += "```\n"
        date_minus_3_hours = date - pd.Timedelta(hours=3) # somehow the bar detected is 3 hours ahead
        msg += f"detected bar: {date_minus_3_hours} SGT\n"
        msg += "```"

        tc.send_message(message=msg)
        print(f"sent message: {msg}")
        
        

while True:
    calculate_latest_indicator_and_alert(symbol="USD/JPY", interval=15, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="USD/JPY", interval=30, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="USD/JPY", interval=1, interval_units="h", output_size=5000)

    calculate_latest_indicator_and_alert(symbol="GBP/USD", interval=15, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="GBP/USD", interval=30, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="GBP/USD", interval=1, interval_units="h", output_size=5000)

    calculate_latest_indicator_and_alert(symbol="USD/CAD", interval=15, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="USD/CAD", interval=30, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="USD/CAD", interval=1, interval_units="h", output_size=5000)

    calculate_latest_indicator_and_alert(symbol="NZD/USD", interval=15, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="NZD/USD", interval=30, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="NZD/USD", interval=1, interval_units="h", output_size=5000)

    calculate_latest_indicator_and_alert(symbol="EUR/USD", interval=15, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="EUR/USD", interval=30, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="EUR/USD", interval=1, interval_units="h", output_size=5000)

    calculate_latest_indicator_and_alert(symbol="AUD/USD", interval=15, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="AUD/USD", interval=30, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="AUD/USD", interval=1, interval_units="h", output_size=5000)

    calculate_latest_indicator_and_alert(symbol="USD/CHF", interval=15, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="USD/CHF", interval=30, interval_units="min", output_size=5000)
    calculate_latest_indicator_and_alert(symbol="AUD/USD", interval=1, interval_units="h", output_size=5000)

    sleep_time = 300
    print(f"sleeping for {sleep_time} seconds")
    

    
