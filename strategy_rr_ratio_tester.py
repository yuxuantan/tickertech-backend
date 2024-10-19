import utils.indicators as indicators


# import utils.ticker_getter as tg
import requests
import pandas as pd

api_key = "94a3bc39c81e45dd9836712337cc5dec"
# symbol = "XAU/USD"
# gap_for_sl = 0.15
symbol = "BTC/USD"
gap_for_sl = 1.88

interval = 15  # Can be 1min, 5min, 15min, 30min, 1h, etc.
interval_granularity = "min"
output_size = 5000

simulation_sl_per_trade = 2
risk_reward_ratio_to_try = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
# risk_reward_ratio_to_try = [2]


# url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}min&outputsize={output_size}&apikey={api_key}"
from_date = "2023-08-09"
to_date = "2023-12-09"
# break up into 1 month intervals and append to df
time_intervals = pd.date_range(start=from_date, end=to_date, freq="M")
print(time_intervals)
data = []
for time_interval in time_intervals:
    start = time_interval.replace(day=1).strftime("%Y-%m-%d")
    end = (time_interval + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}{interval_granularity}&start_date={start}&end_date={end}&apikey={api_key}"
    # need to find a way to get longer time frame


    print(f"fetching data from {url}")
    response = requests.get(url)
    data.extend(response.json()["values"])

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

print(df.head())
print(df.tail())

# BULL APPEAR
analysis_results = {}
print("calculating bull appear dates")
analysis_results["apex_bull_raging"] = indicators.get_apex_bull_raging_dates(
    df, custom_aggregate_2days=False
)
print("calculating bull raging dates")
analysis_results["apex_bull_appear"] = indicators.get_apex_bull_appear_dates(
    df, custom_aggregate_2days=False
)
print("calculating bull uptrend dates")
analysis_results["apex_bull_uptrend"] = indicators.get_apex_uptrend_dates(
    df, custom_aggregate_2days=False
)
print("calculating bear appear dates")
analysis_results["apex_bear_raging"] = indicators.get_apex_bear_raging_dates(
    df, custom_aggregate_2days=False
)
print("calculating bear raging dates")
analysis_results["apex_bear_appear"] = indicators.get_apex_bear_appear_dates(
    df, custom_aggregate_2days=False
)
print("calculating bear downtrend dates")
analysis_results["apex_bear_downtrend"] = indicators.get_apex_downtrend_dates(
    df, custom_aggregate_2days=False
)

conclusion = []
for indicator, dates in analysis_results.items():
    print(f"*** {indicator} ***")
    # do simulation using different risk reward ratio
    best_risk_reward_ratio = -1
    highest_portfolio_value_till_now = -1

    for risk_reward_ratio in risk_reward_ratio_to_try:
        simulation_portfolio_value = 100
        simulation_take_profit_per_trade = simulation_sl_per_trade * risk_reward_ratio
        num_wins = 0
        total_valid_trades = 0

        # calculate the PNL. this assumes as long as signal appears we will enter no matter if theres existing signal.
        for date in dates:
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
                quantity = simulation_sl_per_trade / (
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
                quantity = simulation_sl_per_trade / (sl_price - entry_sweet_spot_price)

            # SIMPLIFY - find next bar with TP/SL price. If bar hits both TP and SL, dont count it as win or loss
            for i in range(1, 100):
                minutes_later = i * interval
                # if key dont exist in df, break. most likely its because data is not avail yet
                if date + pd.Timedelta(minutes=minutes_later) not in df.index:
                    break
                #  if bar hits both TP and SL, dont count it as win. move on
                elif (
                    "bull" in indicator
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["High"]
                    >= tp_price
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["Low"]
                    <= sl_price
                ) or (
                    "bear" in indicator
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["Low"]
                    <= tp_price
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["High"]
                    >= sl_price
                ):
                    # print("no count")
                    break

                # if bar hits TP, win
                elif (
                    "bull" in indicator
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["High"]
                    >= tp_price
                ) or (
                    "bear" in indicator
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["Low"]
                    <= tp_price
                ):
                    # print(f'✅win {simulation_take_profit_per_trade}')
                    simulation_portfolio_value += simulation_take_profit_per_trade
                    total_valid_trades += 1
                    num_wins += 1
                    break
                # if bar hits SL, lose
                elif (
                    "bull" in indicator
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["Low"]
                    <= sl_price
                ) or (
                    "bear" in indicator
                    and df.loc[date + pd.Timedelta(minutes=minutes_later)]["High"]
                    >= sl_price
                ):
                    # print(f'❌lose {simulation_sl_per_trade}')
                    simulation_portfolio_value -= simulation_sl_per_trade
                    total_valid_trades += 1
                    break

                # if 100 bars later, no TP or SL, break
                # elif i == 99:
                # print("no tp or SL after 99 bars")

        if simulation_portfolio_value > highest_portfolio_value_till_now:
            highest_portfolio_value_till_now = simulation_portfolio_value
            best_risk_reward_ratio = risk_reward_ratio

        print(f"risk reward ratio: {risk_reward_ratio} ***")
        print(f"Total VALUE at the end of simulation: {simulation_portfolio_value}")
        print(f"num wins: {num_wins}")
        print(f"total trades: {len(dates)}")
        print(f"total valid trades: {total_valid_trades}")
        if total_valid_trades == 0:
            print("win rate (out of valid trades): 0%")
        else:
            print(
                f"win rate (out of valid trades): {num_wins / total_valid_trades * 100}%"
            )
        print("======================")

    conclusion.append(
        (indicator, highest_portfolio_value_till_now, best_risk_reward_ratio)
        # f"BEST RISK REWARD RATIO for {indicator} is {best_risk_reward_ratio} with total value of {highest_portfolio_value_till_now}"
    )


print("*********************** CONCLUSION ***********************")
overall_win_loss = 0
for msg in conclusion:
    overall_win_loss += msg[1]
    print(msg)

print("overall win/loss: ", round(overall_win_loss / 6 - 100, 2), "%")
