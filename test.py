import utils.indicators as indicators


import utils.ticker_getter as tg

data = tg.fetch_stock_data("AAPL")
print(indicators.get_apex_downtrend_dates(data))
