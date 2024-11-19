
# GOALS
# follow the trend strategy works better after 3am (eg if price went up, sell put. If price went down, sell call)
# willing to lower win rate, for higher gains (and higher losses)
# excess liquidity to have 3x of premium leftover. Eg target 3k usd premium, have to have 9k usd as excess liquidity. max loss 6k

# INSIGHTS
# pure put has (1%) higher win rate than discretionary
# not much difference whether put or call.. cant find a factor that makes a diff. just anyhow choose one.
# dont do 0.3 percent away again. too scary. If i get through this unscathed, i will do minimum 0.5 percent away and I wont think of get rich quick anymore.

## research
# Research shows that approximately 65.6% of the time, SPX closes within 0.20% of its price at 2 PM, indicating a tendency for prices to stabilize as the day progresses
# Similarly, there is a 56.1% chance that SPX will close within 0.20% of its price at 1:30 PM2. This data highlights specific times when traders might find favorable conditions for entering or exiting trades.
# The rate of theta decay accelerates significantly in the late afternoon. Traders who enter positions during this time can benefit from rapid premium erosion, especially if they are selling options or employing strategies like iron condors
# Overall, while there is a possibility of price reversals at 2 PM, historical patterns suggest that this time is more conducive to breakouts and trend continuations rather than significant reversals. Traders should approach this time with an understanding of these tendencies, utilizing them to inform their strategies effectively.
import yfinance as yf
import pandas as pd
import numpy as np
import datetime


start_date = "2023-01-01"
end_date = "2024-11-12"
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


# Calculate RSI (14-period)
def calculate_rsi(data, period=14):
    # Calculate price change
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()

    # Calculate Relative Strength (RS)
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


day_granular_data = yf.download(
    "^GSPC",
    start=(pd.to_datetime(start_date) - pd.Timedelta(days=50)).strftime("%Y-%m-%d"),
    end="2024-11-12",
    interval="1d",
)
# Apply RSI calculation to the data
day_granular_data["RSI"] = calculate_rsi(day_granular_data)


# Calculate ADX (14-period)
def calculate_adx(data, period=14):
    # Step 1: Calculate True Range (TR)
    data["High-Low"] = data["High"] - data["Low"]
    data["High-Close"] = np.abs(data["High"] - data["Close"].shift(1))
    data["Low-Close"] = np.abs(data["Low"] - data["Close"].shift(1))
    data["TR"] = data[["High-Low", "High-Close", "Low-Close"]].max(axis=1)

    # Step 2: Calculate +DM and -DM
    data["+DM"] = np.where(
        (data["High"] - data["High"].shift(1)) > (data["Low"].shift(1) - data["Low"]),
        np.maximum(data["High"] - data["High"].shift(1), 0),
        0,
    )
    data["-DM"] = np.where(
        (data["Low"].shift(1) - data["Low"]) > (data["High"] - data["High"].shift(1)),
        np.maximum(data["Low"].shift(1) - data["Low"], 0),
        0,
    )

    # Step 3: Smooth TR, +DM, -DM
    data["TR_Smoothed"] = data["TR"].rolling(window=period, min_periods=1).sum()
    data["+DM_Smoothed"] = data["+DM"].rolling(window=period, min_periods=1).sum()
    data["-DM_Smoothed"] = data["-DM"].rolling(window=period, min_periods=1).sum()

    # Step 4: Calculate +DI and -DI
    data["+DI"] = 100 * (data["+DM_Smoothed"] / data["TR_Smoothed"])
    data["-DI"] = 100 * (data["-DM_Smoothed"] / data["TR_Smoothed"])

    # Step 5: Calculate DX
    data["DX"] = (np.abs(data["+DI"] - data["-DI"]) / (data["+DI"] + data["-DI"])) * 100

    # Step 6: Smooth DX to get ADX
    data["ADX"] = data["DX"].rolling(window=period, min_periods=1).mean()

    return data["ADX"]


# Apply ADX calculation to the data
day_granular_data["ADX"] = calculate_adx(day_granular_data)

day_granular_data["Date"] = day_granular_data.index.date
# drop index
day_granular_data = day_granular_data.reset_index(drop=True)
# Merge RSI and ADX values to the merged_data based on Date
final_data = pd.merge(
    df_entry,
    day_granular_data[["Date", "Open", "Close", "RSI", "ADX"]],
    on="Date",
    how="outer",
)

# Sort by Date for readability
final_data = final_data.sort_values(by="Date").reset_index(drop=True)

# only include data where 1330 open is not Nan
final_data = final_data[final_data["entry"].notna()]


final_data["option_type"] = np.where(
    # final_data["entry"] > final_data["Open"], "call", "put" # go against the trend, expect reversal
    # final_data["entry"] > final_data["Open"], "put", "call" # go with the trend
    ((final_data["entry"] > final_data["Open"]) & final_data["RSI"] > 70), # overbought
    # False,
    "call" ,
    "put"
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


# cut loss roughly 10 away from strike
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
    ]
]
print(final_data)
print(f"Win rate: {win_rate}%")
