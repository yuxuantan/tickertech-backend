# import requests
# api_key = "94a3bc39c81e45dd9836712337cc5dec"
# # symbol = "XAU/USD"
# # gap_for_sl = 0.15
# symbol = "BTC/USD"
# gap_for_sl = 1.88

# interval = 15  # Can be 1min, 5min, 15min, 30min, 1h, etc.
# output_size = 5000

# sl_per_trade = 20
# risk_reward_ratio = 2


# url = "https://api.twelvedata.com/commodities"

# print(f"fetching data from {url}")
# response = requests.get(url)
# data = response.json()

# print(data)

import utils.indicators as indicators
import utils.ticker_getter as tg

data = tg.fetch_stock_data("ISRG")
# print(data.tail())
results = indicators.get_apex_downtrend_dates(data)
print(results)