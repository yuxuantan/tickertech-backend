import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

def calculate_adx(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate the ADX indicator.
    """
    # Calculate TR (True Range)
    data['Close_shift1'] = data['Close'].shift(1)
    data['TR'] = data.apply(
        lambda row: max(row['High'] - row['Low'], 
                        abs(row['High'] - row['Close_shift1']), 
                        abs(row['Low'] - row['Close_shift1'])), axis=1)
    
    # Calculate +DM and -DM
    data['+DM'] = data['High'].diff()
    data['-DM'] = -data['Low'].diff()
    data['+DM'] = data['+DM'].where((data['+DM'] > data['-DM']) & (data['+DM'] > 0), 0.0)
    data['-DM'] = data['-DM'].where((data['-DM'] > data['+DM']) & (data['-DM'] > 0), 0.0)
    
    # Smooth the TR, +DM, and -DM
    data['TR_smooth'] = data['TR'].rolling(window=period).sum()
    data['+DM_smooth'] = data['+DM'].rolling(window=period).sum()
    data['-DM_smooth'] = data['-DM'].rolling(window=period).sum()
    
    # Calculate +DI and -DI
    data['+DI'] = 100 * (data['+DM_smooth'] / data['TR_smooth'])
    data['-DI'] = 100 * (data['-DM_smooth'] / data['TR_smooth'])
    
    # Calculate DX
    data['DX'] = 100 * abs(data['+DI'] - data['-DI']) / (data['+DI'] + data['-DI'])
    
    # Calculate ADX
    data['ADX'] = data['DX'].rolling(window=period).mean()  # Initial ADX as rolling average of DX
    
    # Fill NaN values that may appear due to rolling calculations
    data = data.dropna(subset=['ADX'])
    
    return data

def get_market_trend(at_datetime: datetime, data) -> str:
    
    # Calculate ADX
    data = calculate_adx(data)
    
    # Filter data for inflection points for highs and lows
    data['Higher_High'] = (data['High'] > data['High'].shift(1)) & \
                          (data['High'] > data['High'].shift(2)) & \
                          (data['High'] > data['High'].shift(3)) & \
                          (data['High'] > data['High'].shift(-1)) & \
                          (data['High'] > data['High'].shift(-2)) & \
                          (data['High'] > data['High'].shift(-3))
    
    data['Lower_Low'] = (data['Low'] < data['Low'].shift(1)) & \
                        (data['Low'] < data['Low'].shift(2)) & \
                        (data['Low'] < data['Low'].shift(3)) & \
                        (data['Low'] < data['Low'].shift(-1)) & \
                        (data['Low'] < data['Low'].shift(-2)) & \
                        (data['Low'] < data['Low'].shift(-3))
    
    # Filter only the inflection points
    highs = data[data['Higher_High']][['Datetime', 'High']]
    lows = data[data['Lower_Low']][['Datetime', 'Low']]
    
    # Check if there are at least two inflection points before the given datetime
    highs = highs[highs['Datetime'] < at_datetime]
    lows = lows[lows['Datetime'] < at_datetime]
    
    if len(highs) < 2 or len(lows) < 2:
        return "Not enough data for trend determination."
    
    # Get the last two inflection points for highs and lows before the given datetime
    last_two_highs = highs['High'].iloc[-2:].values
    last_two_lows = lows['Low'].iloc[-2:].values

    
    # Get the ADX value at the given datetime
    adx_value = data.loc[data['Datetime'] <= at_datetime, 'ADX'].iloc[-1]
    print("ADX value:", adx_value)

    # Determine the trend based on ADX and inflection points
    if adx_value < 25:
        return "ranging"
    elif last_two_highs[1] > last_two_highs[0] and last_two_lows[1] > last_two_lows[0]:
        return "bull"
    elif last_two_highs[1] < last_two_highs[0] and last_two_lows[1] < last_two_lows[0]:
        return "bear"
    else:
        return "ranging"

# Example usage
# Define the datetime in Eastern Standard Time
eastern = pytz.timezone('US/Eastern')
# at_datetime = eastern.localize(datetime(2024, 11, 8, 13, 20))
# print(get_market_trend(at_datetime))



# if ranging 15 min chart, do vertical spread opposite of the price movement since start of day, 1% of price away. eg price went up, do call spread, if price went down, do put spread
# if bullish/bearish 15 min chart, do vertical spread in the direction of the trend, 1% of price away. eg if bullish, do put spread

start_date = datetime(2024, 10, 8)
end_date = datetime(2024, 11, 9)
def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

wins = 0
losses = 0
# for each day, get the trend at 1:30pm EST
# Define a time window around the given datetime to gather sufficient data for trend analysis

for single_date in daterange(start_date, end_date):
    at_datetime = eastern.localize(datetime(single_date.year, single_date.month, single_date.day, 13, 30))
    start_date = at_datetime - timedelta(days=1) 
    end_date = at_datetime + timedelta(days=1)  # A bit beyond the datetime for completeness

    # Download 15-minute interval data within the date range
    data = yf.download("^GSPC", interval="5m", start=start_date, end=end_date)
    if data.empty:
        print( "No data available for the specified date range.")
        continue

    # Reset the index to make it easier to work with
    data = data.reset_index()

    trend = get_market_trend(at_datetime, data)
    print(data)
    print(at_datetime)
    entry_price = data[data["Datetime"] == at_datetime]["Close"].values[0]
    # open price of the day
    open_price = data.iloc[0]["Open"]
    # close price of the day
    close_price = data.iloc[-1]["Close"]

    strike_price_of_vertical = 0
    type_of_vertical = None # call or put

    if trend == "ranging":
        print(f"Market is ranging on {single_date}")
        if entry_price > open_price:
            print("Price went up since open, do a call spread")
            strike_price_of_vertical = entry_price * 1.01
            type_of_vertical = "call"
        else:
            print("Price went down since open, do a put spread")
            strike_price_of_vertical = entry_price * 0.99
            type_of_vertical = "put"

    elif trend == "bull":
        print(f"Market is bullish on {single_date}")
        strike_price_of_vertical = entry_price * 0.99
        type_of_vertical = "put"
    elif trend == "bear":
        print(f"Market is bearish on {single_date}")
        strike_price_of_vertical = entry_price * 1.01
        type_of_vertical = "call"
    else:
        print(f"Market trend could not be determined on {single_date}")

    # calculate win or loss
    if type_of_vertical == "call":
        if close_price > strike_price_of_vertical:
            wins += 1
        else:
            losses += 1
    elif type_of_vertical == "put":
        if close_price < strike_price_of_vertical:
            wins += 1
        else:
            losses += 1

print(f"Wins: {wins}, Losses: {losses}")