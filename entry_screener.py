import utils.indicators as indicators
import utils.telegram_controller as tc
import time

# import utils.ticker_getter as tg
import requests
import pandas as pd

api_key = "94a3bc39c81e45dd9836712337cc5dec"

def calculate_latest_indicator_and_alert(symbol, interval, output_size, gap_for_sl, max_loss_per_trade, risk_reward_ratio):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}min&outputsize={output_size}&apikey={api_key}"
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
        df, custom_aggregate_2days=False
    )
    print("calculating bull appear dates")
    analysis_results["apex_bull_appear"] = indicators.get_apex_bull_appear_dates(
        df, custom_aggregate_2days=False
    )
    print("calculating bull uptrend dates")
    analysis_results["apex_bull_uptrend"] = indicators.get_apex_uptrend_dates(
        df, custom_aggregate_2days=False
    )
    print("calculating bear raging dates")
    analysis_results["apex_bear_raging"] = indicators.get_apex_bear_raging_dates(
        df, custom_aggregate_2days=False
    )
    print("calculating bear appear dates")
    analysis_results["apex_bear_appear"] = indicators.get_apex_bear_appear_dates(
        df, custom_aggregate_2days=False
    )
    print("calculating bear downtrend dates")
    analysis_results["apex_bear_downtrend"] = indicators.get_apex_downtrend_dates(
        df, custom_aggregate_2days=False
    )

    conclusion = []
    for indicator, dates in analysis_results.items():
        
        # do simulation using different risk reward ratio
        best_risk_reward_ratio = -1
        highest_portfolio_value_till_now = -1

        take_profit_per_trade = max_loss_per_trade * risk_reward_ratio

        if len(dates) == 0:
            print(f"skipping because no {indicator} detected")
            continue

        date = dates[-1]
        
        alert_recency_filter = 2 #bars

        if str(date) not in [str(df.index[-i]) for i in range(1, alert_recency_filter+1)]:
            print(f"skipping because last entry date for {indicator} is {date}, which is not last 2 bar")
            continue
        
        if "bull" in indicator:
                entry_sweet_spot_price = (
                    df.loc[date]["Low"]
                    + (df.loc[date]["High"] - df.loc[date]["Low"]) * 3 / 4
                )  # open at top quarter of appear bar
                sl_price = df.loc[date]["Low"] - gap_for_sl  # for btc, example sl
                tp_price = (
                    entry_sweet_spot_price
                    + (entry_sweet_spot_price - sl_price) * risk_reward_ratio
                )
                quantity = max_loss_per_trade / (
                    entry_sweet_spot_price - sl_price
                )  # quantity = 2% of total portfolio / (entry - stop loss)
        else:
            entry_sweet_spot_price = (
                df.loc[date]["High"]
                - (df.loc[date]["High"] - df.loc[date]["Low"]) * 3 / 4
            )  # open at bottom quarter of appear bar
            sl_price = df.loc[date]["High"] + gap_for_sl  # for btc, example sl
            tp_price = (
                entry_sweet_spot_price
                - (sl_price - entry_sweet_spot_price) * risk_reward_ratio
            )
            quantity = max_loss_per_trade / (sl_price - entry_sweet_spot_price)
        
        msg = f"🚨 {indicator} detected for {symbol}! ***\n"
        msg += "```\n"
        msg += f"detected bar: {date}\n"
        msg += f"entry_sweet_spot_price: {entry_sweet_spot_price}\n"
        msg += f"sl_price: {sl_price}\n"
        msg += f"tp_price: {tp_price}\n"
        msg += f"quantity: {quantity}\n"
        msg += f"JUST order market order asap as long as price is in sweet spot range. ensure right quantity"
        msg += "```"

        tc.send_message(message=msg)
        print(f"sent message: {msg}")
        
        

while True:
    calculate_latest_indicator_and_alert(symbol="BTC/USD", interval=15, output_size=5000, gap_for_sl=0.08, max_loss_per_trade=20, risk_reward_ratio=2)
    calculate_latest_indicator_and_alert(symbol="XAU/USD", interval=15, output_size=5000, gap_for_sl=0.08, max_loss_per_trade=20, risk_reward_ratio=2)
    # sleep 5 minute, then repeat
    time.sleep(300)
    

    
