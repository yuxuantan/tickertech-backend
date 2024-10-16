import utils.indicators as indicators


import utils.ticker_getter as tg

data = tg.fetch_stock_data("BA")
print(indicators.get_apex_bull_appear_dates(data))
