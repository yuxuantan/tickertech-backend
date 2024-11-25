## research
# Research shows that approximately 65.6% of the time, SPX closes within 0.20% of its price at 2 PM, indicating a tendency for prices to stabilize as the day progresses
# Similarly, there is a 56.1% chance that SPX will close within 0.20% of its price at 1:30 PM2. This data highlights specific times when traders might find favorable conditions for entering or exiting trades.
# The rate of theta decay accelerates significantly in the late afternoon. Traders who enter positions during this time can benefit from rapid premium erosion, especially if they are selling options or employing strategies like iron condors
# Reversals are more common at 2PM


import yfinance as yf
import pandas as pd
import numpy as np
import datetime

capital = 150000

start_date = "2024-01-01"
end_date = "2024-11-24"
# Download SPX data at 30-minute intervals
data = yf.download("^GSPC", start=start_date, end=end_date, interval="1h")
print(data)

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


final_data["option_type"] = np.where(
    final_data["entry"] > final_data["Open"], "call", "put" # go against the trend, expect reversal
)



# Calculate the percentage change between 'Open' and 'entry' prices
final_data["percent_change"] = np.abs(
    (final_data["entry"] - final_data["Open"]) / final_data["Open"]
)

percent_from_strike = 0.005 # each 0.1% away is around 6
final_data["percent_from_strike"] = percent_from_strike

final_data["option_strike"] = np.where(
    final_data["option_type"] == "call",
    np.ceil(final_data["entry"] * (1 + percent_from_strike) / 5) * 5,
    np.floor(final_data["entry"] * (1 - percent_from_strike) / 5) * 5,
)


# cut loss roughly 10 away from strike. in reality is 5% for cut off but will use 10 % conservatively to account for IV spikes since we are using stops
final_data["cut_loss_price"] = np.where(
    final_data["option_type"] == "call",
    final_data["option_strike"] - 10, 
    final_data["option_strike"] + 10,
)

final_data["win"] = np.where(
    (
        (final_data["option_type"] == "call")
        & (final_data["Close"] < final_data["cut_loss_price"])
    )
    | (
        (final_data["option_type"] == "put")
        & (final_data["Close"] > final_data["cut_loss_price"])
    ),
    1,
    0,
)

# calculate win rate
win_rate = round(final_data["win"].sum() / len(final_data) * 100, 2)

# for every win, add 1.6% of capital to capital, each loss subtract 5% from capital. compounded
final_data["capital"] = capital
final_data["cum_profit_loss"] = 0
for i in range(len(final_data)):
    if final_data["win"].iloc[i] == 1:
        final_data["capital"][i] = round(final_data["capital"].iloc[i - 1] * 1.016, 2)
    else:
        final_data["capital"][i] = round(final_data["capital"].iloc[i - 1] * 0.95, 2)

final_data["cum_profit_loss"] = round(final_data["capital"] - capital, 2)


# reorder columns Date, Open, entry, Close, option_type, option_strike, win
final_data = final_data[
    [
        "Date",
        "Open",
        "entry",
        "Close",
        "option_type",
        "percent_from_strike",
        "option_strike",
        "cut_loss_price",
        "win",
        "capital",
        "cum_profit_loss",
    ]
]
print(final_data)
print(f"Win rate: {win_rate}%")
