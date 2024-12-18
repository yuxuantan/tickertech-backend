# fetch daily SPX data from yfinance
import yfinance as yf
import pandas as pd
import utils.indicators as indicators

data = yf.download("^GSPC", start="2022-01-01", end="2024-12-02", interval="1d")

"""# **** testing ability for opening and 10sma to predict close price **** -> verdict 10sma doesnt predict anything"""
# # calculate 10-day sma for each data point
# data["10d_sma"] = data["Close"].rolling(window=10).mean()

# # when price opens above 10 day sma, calculate the likelihood that it closes above the open price
# data["open_above_10sma"] = (data["Open"] > data["10d_sma"]).astype(int)
# data["open_below_10sma"] = (data["Open"] < data["10d_sma"]).astype(int)
# data["close_above_open"] = (data["Close"] > data["Open"]).astype(int)

# # calculate the percentage of times that the close is above the open when the open is above the 10 day sma
# percentage_close_above_open_given_above_10sma = data[data["open_above_10sma"] == 1]["close_above_open"].mean()
# print(percentage_close_above_open_given_above_10sma)

# percentage_close_below_open_given_below_10sma = 1-data[data["open_below_10sma"] == 1]["close_above_open"].mean()
# print(percentage_close_below_open_given_below_10sma)

# percentage_close_above_open = data["close_above_open"].mean()
# print(percentage_close_above_open)

"""# *** testing ability for opening and 50sma to predict close price *** -> verdict 50sma doesnt predict anything"""
# data["50d_sma"] = data["Close"].rolling(window=50).mean()
# data["open_above_50sma"] = (data["Open"] > data["50d_sma"]).astype(int)
# data["open_below_50sma"] = (data["Open"] < data["50d_sma"]).astype(int)
# data["close_above_open"] = (data["Close"] > data["Open"]).astype(int)
# percentage_close_above_open_given_above_50sma = data[data["open_above_50sma"] == 1]["close_above_open"].mean()
# print(percentage_close_above_open_given_above_50sma)
# percentage_close_below_open_given_below_50sma = 1-data[data["open_below_50sma"] == 1]["close_above_open"].mean()
# print(percentage_close_below_open_given_below_50sma)


"""# *** testing ability for opening and 100sma to predict close price ***  -> verdict 100sma doesnt predict anything"""
# data["100d_sma"] = data["Close"].rolling(window=100).mean()
# data["open_above_100sma"] = (data["Open"] > data["100d_sma"]).astype(int)
# data["open_below_100sma"] = (data["Open"] < data["100d_sma"]).astype(int)
# data["close_above_open"] = (data["Close"] > data["Open"]).astype(int)
# percentage_close_above_open_given_above_100sma = data[data["open_above_100sma"] == 1]["close_above_open"].mean()
# print(percentage_close_above_open_given_above_100sma)
# percentage_close_below_open_given_below_100sma = 1-data[data["open_below_100sma"] == 1]["close_above_open"].mean()
# print(percentage_close_below_open_given_below_100sma)

"""# *** testing ability for opening and 200sma to predict close price ***  -> verdict 200sma doesnt predict anything"""
# data["200d_sma"] = data["Close"].rolling(window=200).mean()
# data["open_above_200sma"] = (data["Open"] > data["200d_sma"]).astype(int)
# data["open_below_200sma"] = (data["Open"] < data["200d_sma"]).astype(int)
# data["close_above_open"] = (data["Close"] > data["Open"]).astype(int)
# percentage_close_above_open_given_above_200sma = data[data["open_above_200sma"] == 1]["close_above_open"].mean()
# print(percentage_close_above_open_given_above_200sma)
# percentage_close_below_open_given_below_200sma = 1-data[data["open_below_200sma"] == 1]["close_above_open"].mean()
# print(percentage_close_below_open_given_below_200sma)

"""testing price increase from yesterday's close to today's open - whether it can predict whether today's close is above yesterday's close -> 70%. this is significant"""
# data["price_increase"] = (data["Open"] > data["Close"].shift(1)).astype(int)

# data["close_above_yesterday_close"] = (data["Close"] > data["Close"].shift(1)).astype(int)

# percentage_close_above_yesterday_close_given_price_increase = data[data["price_increase"] == 1]["close_above_yesterday_close"].mean()
# print(percentage_close_above_yesterday_close_given_price_increase)

# # probability that the low of today is above the closing price of yesterday given that today's open is above yesterday's close
# data["low_above_yesterday_close"] = (data["Low"] > data["Close"].shift(1)).astype(int)
# percentage_low_above_yesterday_close_given_price_increase = data[data["price_increase"] == 1]["low_above_yesterday_close"].mean()
# print(percentage_low_above_yesterday_close_given_price_increase)

# # percentage of price increase days
# percentage_price_increase = data["price_increase"].mean()
# print(percentage_price_increase)


"""testing GAP up (price increase > 0.3%) from yesterday's close to today's open - whether it can predict whether today's close is above yesterday's close -> 70%. this is significant"""
data["gap_up"] = ((data["Open"] > data["Close"].shift(1) * 1.003)).astype(int)
data["gap"] = ((data["Open"] > data["Close"].shift(1) * 1.003) | (data["Open"] < data["Close"].shift(1) * 0.997)).astype(int)

data["close_above_yesterday_close"] = (data["Close"] > data["Close"].shift(1)).astype(int)

percentage_close_above_yesterday_close_given_gap_up = data[data["gap_up"] == 1]["close_above_yesterday_close"].mean()
print(percentage_close_above_yesterday_close_given_gap_up)

# probability that the low of today is above the closing price of yesterday given that today's open is above yesterday's close
data["low_above_yesterday_close"] = (data["Low"] > data["Close"].shift(1)).astype(int)
percentage_low_above_yesterday_close_given_gap_up = data[data["gap_up"] == 1]["low_above_yesterday_close"].mean()
print(percentage_low_above_yesterday_close_given_gap_up)

# percentage of gap up days
percentage_gap_up = data["gap_up"].mean()
print(percentage_gap_up)

# mean gap up percentage given more than 0.3% gap up
gap_up_percentage = data["Open"] / data["Close"].shift(1) - 1
print(gap_up_percentage[data["gap_up"] == 1].mean())

# median gap up percentage given more than 0.3% gap up
print(gap_up_percentage[data["gap_up"] == 1].median())

# chance today's close above today's open
data["today_close_above_open"] = (data["Close"] > data["Open"]).astype(int)
percentage_today_close_above_open_given_gap_up = data[data["gap_up"] == 1]["today_close_above_open"].mean()
print(percentage_today_close_above_open_given_gap_up)

#chance today's close above today open given not gap up OR gap down - 53.6% up
percentage_today_close_above_open_given_not_gap_up = data[data["gap"] == 0]["today_close_above_open"].mean()
print(percentage_today_close_above_open_given_not_gap_up)


# # probability that the close is more than 0.5% below open price, given it is a gap up day - 23.2%
# data["close_at_least_half_percent_below_open"] = (data["Close"] < data["Open"] * 0.995).astype(int)
# percentage_close_at_least_half_percent_below_open_given_gap_up = data[data["gap_up"] == 1]["close_at_least_half_percent_below_open"].mean()
# print(percentage_close_at_least_half_percent_below_open_given_gap_up)

# # CONTROL - probability that close is more than 0.5% above open price, given its a gap up day - 39.78%
# data["close_at_least_half_percent_above_open"] = (data["Close"] > data["Open"] * 1.005).astype(int)
# percentage_close_at_least_half_percent_above_open_given_gap_up = data[data["gap_up"] == 1]["close_at_least_half_percent_above_open"].mean()
# print(percentage_close_at_least_half_percent_above_open_given_gap_up)

"""testing GAP down (price decrease > 0.3%) from yesterday's close to today's open - whether it can predict whether today's close is below yesterday's close """

# data["gap_down"] = ((data["Open"] < data["Close"].shift(1) * 0.997)).astype(int)

# data["close_below_yesterday_close"] = (data["Close"] < data["Close"].shift(1)).astype(int)

# percentage_close_below_yesterday_close_given_gap_down = data[data["gap_down"] == 1]["close_below_yesterday_close"].mean()
# print(percentage_close_below_yesterday_close_given_gap_down)

# # probability that the high of today is below the closing price of yesterday given that today's open is below yesterday's close
# data["high_below_yesterday_close"] = (data["High"] < data["Close"].shift(1)).astype(int)
# percentage_high_below_yesterday_close_given_gap_down = data[data["gap_down"] == 1]["high_below_yesterday_close"].mean()
# print(percentage_high_below_yesterday_close_given_gap_down)

# # percentage of gap down days
# percentage_gap_down = data["gap_down"].mean()
# print(percentage_gap_down)

# # average gap down percentage given more than 0.3% gap down
# gap_down_percentage = data["Open"] / data["Close"].shift(1) - 1
# print(gap_down_percentage[data["gap_down"] == 1].mean())

# # median gap down percentage given more than 0.3% gap down
# print(gap_down_percentage[data["gap_down"] == 1].median())

# # today's close below today's open
# data["today_close_below_open"] = (data["Close"] < data["Open"]).astype(int)
# percentage_today_close_below_open_given_gap_down = data[data["gap_down"] == 1]["today_close_below_open"].mean()
# print(percentage_today_close_below_open_given_gap_down)


""" testing given apex bull appear for 5 mins TF detected in the first 5 intraday bars (2.5 hours). How likely will price close above the detected bar? - not statistically significant"""
# # get 30 min data
# data = yf.download("^GSPC", start="2024-11-01", end="2024-12-02", interval="15m")

# # add column for the "Close" price in the dataframe for the last row of the same Date in Datetime index
# data["day_close"] = data.groupby(data.index.date)["Close"].transform("last")

# # 
# dates = indicators.get_apex_bull_appear_dates(data, False, False)
# # for the above dates (DatetimeIndex type), select the corresponding rows from data with the same DatetimeIndex value
# data["apex_bull_appear"] = 0

# for date in dates:
#     data.loc[date, "apex_bull_appear"] = 1

# # calculate the percentage where the day_close is above the "Close" of the detected apex bull appear bar, given bull appear is detected
# data["day_close_above_bar"] = (data["day_close"] > data["Close"]).astype(int)
# print(data[data["apex_bull_appear"] == 1]["day_close_above_bar"].mean()) #58.8 percent

# print(data[data["apex_bull_appear"] == 1])
# # number of dates
# print(len(dates))
# print(dates)



""" Testing iron condor - whats the likelihood of price changing < 0.3% in the last 30 mins of the day"""

# data = yf.download("^GSPC", start="2023-11-01", end="2024-12-02", interval="1h")

# data["today_open_price"] = data.groupby(data.index.date)["Open"].transform("first")
# data["today_close_price"] = data.groupby(data.index.date)["Close"].transform("last")

# # only select 15:30 data
# data = data[data.index.time == pd.to_datetime("15:30").time()]
# data["price_perc_change_between_open_and_close"] = (data["Close"] - data["Open"]) / data["Open"]
# #likelihood thaht absolute price change is less than 0.2% in the last 30 mins - 78.8%
# print((data["price_perc_change_between_open_and_close"].abs() < 0.002).mean())



