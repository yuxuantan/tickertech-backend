## research
# Research shows that approximately 65.6% of the time, SPX closes within 0.20% of its price at 2 PM, indicating a tendency for prices to stabilize as the day progresses
# Similarly, there is a 56.1% chance that SPX will close within 0.20% of its price at 1:30 PM2. This data highlights specific times when traders might find favorable conditions for entering or exiting trades.
# The rate of theta decay accelerates significantly in the late afternoon. Traders who enter positions during this time can benefit from rapid premium erosion, especially if they are selling options or employing strategies like iron condors
# Reversals are more common at 2PM


import yfinance as yf
import pandas as pd
import numpy as np
import datetime

capital = 170000

start_date = "2024-01-01"
end_date = "2024-12-02"
# Download SPX data at 30-minute intervals
data = yf.download("^GSPC", start=start_date, end=end_date, interval="1h")

# Add Date and Time columns
data["Time"] = data.index.time
data["Date"] = data.index.date

# Filter and rename each time's Open/Close values separately
df_entry = data[(data["Time"] == datetime.time(13, 30))][["Date", "Open"]].rename(
    columns={"Open": "entry"}
)


day_granular_data = yf.download(
    "^GSPC",
    start=(pd.to_datetime(start_date) - pd.Timedelta(days=50)).strftime("%Y-%m-%d"),
    end=end_date,
    interval="1d",
)


day_granular_data["Date"] = day_granular_data.index.date
# drop index
day_granular_data = day_granular_data.reset_index(drop=True)
# Merge RSI and ADX values to the merged_data based on Date
final_data = pd.merge(
    df_entry,
    day_granular_data[["Date", "Open", "Close"]],
    on="Date",
    how="outer",
)

# Sort by Date for readability
final_data = final_data.sort_values(by="Date").reset_index(drop=True)

# only include data where 1330 open is not Nan
final_data = final_data[final_data["entry"].notna()]
# reset index
final_data = final_data.reset_index(drop=True)


# bullish or bearish
final_data["bullish"] = np.where(
    final_data["entry"] > final_data["Open"], 1, 0
)

base_strike_percentage_away = 0.005
strike_advantage_discount = 0.001
# for iron condor. if bullish, call strike is 0.35% above, and put strike is 0.25% below. if bearish will be opposite
final_data['call_strike'] = np.where(final_data['bullish'] == 1, np.round(final_data['entry'] * (1+base_strike_percentage_away) / 5) * 5, np.round(final_data['entry'] * (1+base_strike_percentage_away-strike_advantage_discount) / 5) * 5)
final_data['put_strike'] = np.where(final_data['bullish'] == 1, np.round(final_data['entry'] * (1-base_strike_percentage_away+strike_advantage_discount) / 5) * 5, np.round(final_data['entry'] * (1-base_strike_percentage_away) / 5) * 5)


# calculate cut off put, and cut off call strike. it will be 5 points above and below the put and call strike
final_data['cut_off_call'] = final_data['call_strike'] - 5
final_data['cut_off_put'] = final_data['put_strike'] + 5

# calculate win rate
final_data['win'] = np.where((final_data['Close'] < final_data['cut_off_call']) & (final_data['Close'] > final_data['cut_off_put']), 1, 0)

# calculate capital at the end, given every win gives 2% return and every loss gives 2% loss
final_data['capital'] = capital
for i in range(1, len(final_data)):
    if final_data.loc[i-1, 'win'] == 1:
        final_data.loc[i, 'capital'] = final_data.loc[i-1, 'capital'] * 1.02
    else:
        final_data.loc[i, 'capital'] = final_data.loc[i-1, 'capital'] * 0.98

# Format capital to display as plain numbers
final_data['capital'] = final_data['capital'].map('{:,.2f}'.format)

print(final_data)
# print win rate
print(final_data['win'].sum() / len(final_data))

