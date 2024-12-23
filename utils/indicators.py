import pandas as pd
import logging


from utils.indicator_helpers import (
    get_2day_aggregated_data,
    get_high_inflexion_points,
    get_low_inflexion_points,
    find_lowest_bear_trap_within_price_range,
    find_highest_bull_trap_within_price_range,
    find_bear_traps,
    find_bull_traps,
)

## Uncomment line below to log debug messages
# logging.basicConfig(encoding='utf-8', level=logging.DEBUG)

# MY definition of flush down is big magnitude of price movement per bar (2x), compared to the median for all the data (high - low). 
def get_apex_bull_raging_dates(data, custom_aggregate_2days = True, flush_treshold = 2, ratio_of_flush_bars_to_consider_raging = 0.3, only_fetch_last = False):
    if custom_aggregate_2days:
        data = get_2day_aggregated_data(data)

    median_price_movement_per_bar = (data["High"] - data["Low"]).median()

    high_inflexion_points = get_high_inflexion_points(data)
    potential_bear_traps = get_low_inflexion_points(data)

    future_bear_traps = potential_bear_traps.copy()

    bull_raging_dates = []

    for high_point in high_inflexion_points:
        high_point_date, high_point_value = high_point
        # logging.info(f"************ checking {high_point_date}: ************")
        if high_point_date not in data.index:
            continue

        # Find the stopping point (which is the next bear trap)
        stopping_point_date = next(
            (
                trap[0]
                for trap in future_bear_traps
                if trap[0] > high_point_date and trap[1] < high_point_value
            ),
            data.index[-1],
        )
        future_bear_traps = [
            trap for trap in future_bear_traps if trap[0] >= high_point_date
        ]

        # logging.info(f"stopping point date: {stopping_point_date}")

        previous_bear_trap = find_lowest_bear_trap_within_price_range(
            tuple(potential_bear_traps),
            high_point_date,
            data.loc[stopping_point_date]["Low"],
            high_point_value,
        )

        if previous_bear_trap is None:
            # logging.info("❌ no previous bear trap found")
            continue
        # logging.info(f"previous_bear_trap: {previous_bear_trap}")

        mid_point = (
            previous_bear_trap[1] + (high_point_value - previous_bear_trap[1]) / 2
        )

        # Analyze the range from high point to stopping point
        range_data = data.loc[high_point_date:stopping_point_date]
        flush_down_mask = (range_data["High"] - range_data["Low"]) > flush_treshold * median_price_movement_per_bar
        flush_down_bars = range_data[flush_down_mask]

        if flush_down_bars.empty or flush_down_bars.iloc[0]["High"] < mid_point:
            # logging.info(
            #     "❌ first flush down started after mid point, or didn't happen at all"
            # )
            continue
        # logging.info(
        #     f"✅ first flush down started at {flush_down_bars.iloc[0]['High']} before mid point {mid_point}"
        # )

        # Find the date which broke below bear trap
        break_below_bear_trap = range_data.index[
            range_data["Low"] < previous_bear_trap[1]
        ]
        if break_below_bear_trap.empty:
            # logging.info(
            #     f"❌ no break below bear trap {previous_bear_trap} before the price reaches stopping point"
            # )
            continue
        date_which_broke_below_bear_trap = break_below_bear_trap[0]
        # logging.info(
        #     f"✅ date_which_broke_below_bear_trap: {date_which_broke_below_bear_trap}"
        # )

        total_bar_count = len(range_data)
        flush_down_count = flush_down_mask.sum()
        if total_bar_count < 5 or flush_down_count / total_bar_count < ratio_of_flush_bars_to_consider_raging:
            # logging.info(
            #     f"❌ less than 5 bars or not majority flush down, flush down bars: {flush_down_count}, total bars: {total_bar_count}"
            # )
            continue
        # logging.info(
        #     f"✅ > 5 bars and majority flush down, flush down bars: {flush_down_count}, total bars: {total_bar_count}"
        # )

        # Check 6 bars after break below bear trap
        post_break_data = data.loc[date_which_broke_below_bear_trap:].head(6)
        for i, (date, row) in enumerate(post_break_data.iterrows(), 1):
            if row["Close"] > previous_bear_trap[1] and (
                row["Close"] - row["Open"] > 0.5 * (row["High"] - row["Low"])
                or (
                    row["Open"] > row["Low"] + 4 / 5 * (row["High"] - row["Low"])
                    and row["Close"] > row["Low"] + 4 / 5 * (row["High"] - row["Low"])
                )
            ):
                # logging.info(
                #     f"🚀 {date} closed at {row['Close']}; above bear trap. All Conditions met!"
                # )
                bull_raging_dates.append(date)
                break
            # else:
            # logging.info(f"❌ check bar {i}, no bullish bar closing above stop loss zone")

    if only_fetch_last:
        return bull_raging_dates[-1:]
    
    return bull_raging_dates


def get_apex_bear_raging_dates(data, custom_aggregate_2days = True, flush_treshold = 2, ratio_of_flush_bars_to_consider_raging = 0.3, only_fetch_last = False):

    if custom_aggregate_2days:
        data = get_2day_aggregated_data(data)

    median_price_movement_per_bar = (data["High"] - data["Low"]).median()

    low_inflexion_points = get_low_inflexion_points(data)
    potential_bull_traps = get_high_inflexion_points(data)

    future_bull_traps = potential_bull_traps.copy()

    bear_raging_dates = []

    for low_point in low_inflexion_points:
        low_point_date, low_point_value = low_point
        # logging.info(f"************ checking {low_point_date}: ************")
        if low_point_date not in data.index:
            continue

        # Find the stopping point (which is the next bull trap) - TODO: might not be true. as long as majority flush up, keep goings
        stopping_point_date = next(
            (
                trap[0]
                for trap in future_bull_traps
                if trap[0] > low_point_date and trap[1] > low_point_value
            ),
            data.index[-1],
        )
        future_bull_traps = [
            trap for trap in future_bull_traps if trap[0] >= low_point_date
        ]

        # logging.info(f"stopping point date: {stopping_point_date}")

        previous_bull_trap = find_highest_bull_trap_within_price_range(
            tuple(potential_bull_traps),
            low_point_date,
            low_point_value,
            data.loc[stopping_point_date]["High"],
        )

        if previous_bull_trap is None:
            # logging.info("❌ no previous bull trap found")
            continue
        # logging.info(f"previous_bull_trap: {previous_bull_trap}")

        mid_point = (
            previous_bull_trap[1] + (low_point_value - previous_bull_trap[1]) / 2
        )

        # Analyze the range from low point to stopping point
        range_data = data.loc[low_point_date:stopping_point_date]
        flush_down_mask = (range_data["High"] - range_data["Low"]) > flush_treshold * median_price_movement_per_bar
        flush_up_bars = range_data[flush_down_mask]

        if flush_up_bars.empty or flush_up_bars.iloc[0]["Low"] > mid_point:
            # logging.info("❌ first flush up started after mid point, or didn't happen at all")
            continue
        # logging.info(
        #     f"✅ first flush up started at {flush_up_bars.iloc[0]['Low']} before mid point {mid_point}"
        # )

        # Find the date which broke above bull trap
        break_above_bull_trap = range_data.index[
            range_data["High"] > previous_bull_trap[1]
        ]
        if break_above_bull_trap.empty:
            # logging.info(
            #     f"❌ no break above bull trap {previous_bull_trap} before the price reaches stopping point"
            # )
            continue
        date_which_broke_above_bull_trap = break_above_bull_trap[0]
        # logging.info(
        #     f"✅ date_which_broke_above_bull_trap: {date_which_broke_above_bull_trap}"
        # )

        total_bar_count = len(range_data)
        flush_down_count = flush_down_mask.sum()

        if total_bar_count < 5 or flush_down_count / total_bar_count < ratio_of_flush_bars_to_consider_raging:
            # logging.info(
            #     f"❌ less than 5 bars or not majority flush up, flush up bars: {flush_up_count}, total bars: {total_bar_count}"
            # )
            continue
        # logging.info(
        #     f"✅ > 5 bars and majority flush up, flush up bars: {flush_up_count}, total bars: {total_bar_count}"
        # )

        # Check 6 bars after break above bull trap
        post_break_data = data.loc[date_which_broke_above_bull_trap:].head(6)

        for i, (date, row) in enumerate(post_break_data.iterrows(), 1):
            if row["Close"] < previous_bull_trap[1] and (
                row["Open"] - row["Close"] > 0.5 * (row["High"] - row["Low"])
                or (
                    row["Open"] < row["High"] - 4 / 5 * (row["High"] - row["Low"])
                    and row["Close"] < row["High"] - 4 / 5 * (row["High"] - row["Low"])
                )
            ):
                # logging.info(
                #     f"🚀 {date} closed at {row['Close']}; below bull trap {previous_bull_trap[1]}. All Conditions met!"
                # )
                bear_raging_dates.append(date)
                break
            # else:
            # logging.info(f"❌ check bar {i}, no bearish bar closing below stop loss zone")
    if only_fetch_last:
        return bear_raging_dates[-1:]
    return bear_raging_dates


# @st.cache_data(ttl="1d")
def get_apex_uptrend_dates(data, custom_aggregate_2days = True, only_fetch_last = False):
    
    if custom_aggregate_2days:
        data = get_2day_aggregated_data(data)

    data["SMA_50"] = data["Close"].rolling(window=50).mean()
    data["SMA_200"] = data["Close"].rolling(window=200).mean()

    high_inflexion_points = pd.DataFrame()
    low_inflexion_points = pd.DataFrame()
    for i in range(1, len(data) - 2):
        if (
            data["High"].iloc[i - 1]
            < data["High"].iloc[i]
            > data["High"].iloc[i + 1]
        ) and (
            data["High"].iloc[i - 2]
            < data["High"].iloc[i]
            > data["High"].iloc[i + 2]
        ):
            # add series into dataframe. name of series is the index of df
            high_inflexion_points = pd.concat([high_inflexion_points, data.iloc[i].to_frame().T])

        if (
            data["Low"].iloc[i - 1]
            > data["Low"].iloc[i]
            < data["Low"].iloc[i + 1]
        ) and (
            data["Low"].iloc[i - 2] > data["Low"].iloc[i] < data["Low"].iloc[i + 2]
        ):
            low_inflexion_points = pd.concat([low_inflexion_points, data.iloc[i].to_frame().T])

    uptrend_dates = []
    # LIGHTNING formation check
    # loop through each
    for index, row in high_inflexion_points.iterrows():
        high_inflexion_point = row
        logging.info(
            f"checking for lightning formation starting at high inflexion point {high_inflexion_point.name}"
        )

        # Get price of first inflexion point
        point_a = high_inflexion_point
        
        # get point b which is the next low inflexion point that is after position of point a
        point_b = next(
            (point for index, point in low_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_b is None:
            logging.info("❌ no low inflexion point found after point A")
            continue

        # get point c which is the next high inflexion point that is after position of point a
        point_c = next(
            (point for index, point in high_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_c is None:
            logging.info("❌ no high inflexion point found after point B")
            continue

        # get point d which is the next low inflexion point that is after position of point b
        point_d = next(
            (point for index, point in low_inflexion_points.iterrows() if index > point_b.name),
            None,
        )
        if point_d is None:
            logging.info("❌ no low inflexion point found after point C")
            continue

        if not (point_a.name < point_b.name < point_c.name < point_d.name):
            logging.info("❌ Points A, B, C, D are not in chronological order")
            continue

        # get the higher and lower value of open and close for each point
        point_a_high_open_close = max(
            point_a["Open"], point_a["Close"]
        )
        point_a_low_open_close = min(
            point_a["Open"], point_a["Close"]
        )
        point_b_high_open_close = max(
            point_b["Open"], point_b["Close"]
        )
        point_b_low_open_close = min(
            point_b["Open"], point_b["Close"]
        )
        point_c_high_open_close = max(
            point_c["Open"], point_c["Close"]
        )
        point_c_low_open_close = min(
            point_c["Open"], point_c["Close"]
        )
        point_d_high_open_close = max(
            point_d["Open"], point_d["Close"]
        )
        point_d_low_open_close = min(
            point_d["Open"], point_d["Close"]
        )

        # Check for lightning. must start with high inflexion point, C must be lower than A ,   D must be lower than B and cross back to B (assume it just have to reverse in the direction, but havent reach B)
        if (
            point_d["High"] < point_b["High"] < point_c["High"] < point_a["High"]
            and point_d["Low"] < point_b["Low"] < point_c["Low"] < point_a["Low"]
            and point_d_high_open_close
            < point_b_high_open_close
            < point_c_high_open_close
            < point_a_high_open_close
            and point_d_low_open_close
            < point_b_low_open_close
            < point_c_low_open_close
            < point_a_low_open_close
        ):
            logging.info("✅ VALID LIGHTNING FORMATION")
        else:
            logging.info("❌ not a lightning formation")
            continue

        # Between A to D, Check if at least 5 bars are FULLY above sma50 and sma200

        num_bars_above_sma_50 = 0
        num_bars_above_sma_200 = 0
        # loop through each bar between point a and d in data
        for i in range(
            data.index.get_loc(point_a.name),
            data.index.get_loc(point_d.name) + 1,
        ):
            if (
                data.loc[data.index[i], "Close"]
                > data.loc[data.index[i], "SMA_50"]
            ):
                num_bars_above_sma_50 += 1
            if (
                data.loc[data.index[i], "Close"]
                > data.loc[data.index[i], "SMA_200"]
            ):
                num_bars_above_sma_200 += 1

        if num_bars_above_sma_50 < 5 or num_bars_above_sma_200 < 5:
            logging.info("❌ not enough bars above sma50 or sma200")
            continue
        else:
            logging.info("✅ enough bars (5) above sma50 and sma200")

        # entry bar is the D, which is the reversal point of the trap
        uptrend_dates.append(point_d.name)
        # log out all the dateindex of 4 inflexion points abcd
        logging.info(
            [
                "Lightning formation",
                point_a.name,
                point_b.name,
                point_c.name,
                point_d.name,
            ]
        )

    # M formation check: D must be higher than B and cross back to C to reach E (above A)
    for index, row in low_inflexion_points.iterrows():
        low_inflexion_point = row
        logging.info(
            f"checking for M formation starting at low inflexion point {low_inflexion_point.name}"
        )

        # Get price of first inflexion point
        point_a = low_inflexion_point

        # get point b which is the next high inflexion point that is after position of point a
        point_b = next(
            (point for index, point in high_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_b is None:
            logging.info("❌ no high inflexion point found after point A")
            continue

        # get point c which is the next low inflexion point that is after position of point b
        point_c = next(
            (point for index, point in low_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_c is None:
            logging.info("❌ no low inflexion point found after point B")
            continue

        # get point d which is the next high inflexion point that is after position of point c
        point_d = next(
            (point for index, point in high_inflexion_points.iterrows() if index > point_b.name),
            None,
        )
        if point_d is None:
            logging.info("❌ no high inflexion point found after point C")
            continue

        # get point e which is the next low inflexion point that is after position of point d
        point_e = next(
            (point for index, point in low_inflexion_points.iterrows() if index > point_c.name),
            None,
        )
        if point_e is None:
            logging.info("❌ no low inflexion point found after point D")
            continue

        if not (point_a.name < point_b.name < point_c.name < point_d.name < point_e.name):
            logging.info("❌ Points A, B, C, D, E are not in chronological order")
            continue
        # get the higher and lower value of open and close for each point
        point_a_high_open_close = max(
            point_a["Open"], point_a["Close"]
        )
        point_a_low_open_close = min(
            point_a["Open"], point_a["Close"]
        )
        point_b_high_open_close = max(
            point_b["Open"], point_b["Close"]
        )
        point_b_low_open_close = min(
            point_b["Open"], point_b["Close"]
        )
        point_c_high_open_close = max(
            point_c["Open"], point_c["Close"]
        )
        point_c_low_open_close = min(
            point_c["Open"], point_c["Close"]
        )
        point_d_high_open_close = max(
            point_d["Open"], point_d["Close"]
        )
        point_d_low_open_close = min(
            point_d["Open"], point_d["Close"]
        )
        point_e_high_open_close = max(
            point_e["Open"], point_e["Close"]
        )
        point_e_low_open_close = min(
            point_e["Open"], point_e["Close"]
        )

        # Check for M formation. must start with low inflexion point, D must be higher than B, and cross back to C to reach E (above A)
        if (
            point_d["High"] > point_b["High"] > point_c["High"] > point_e["High"] > point_a["High"]
            and point_d["Low"] > point_b["Low"] > point_c["Low"] > point_e["Low"] > point_a["Low"]
            and point_d_high_open_close > point_b_high_open_close > point_c_high_open_close > point_e_high_open_close > point_a_high_open_close
            and point_d_low_open_close > point_b_low_open_close > point_c_low_open_close > point_e_low_open_close > point_a_low_open_close
        ):
            logging.info("✅ VALID M FORMATION")
        else:
            logging.info("❌ not a M formation")
            continue

        # Between A to E, Check if at least 5 bars are FULLY above sma50 and sma200

        num_bars_above_sma_50 = 0
        num_bars_above_sma_200 = 0
        # loop through each bar between point a and e in data
        for i in range(
            data.index.get_loc(point_a.name),
            data.index.get_loc(point_e.name) + 1,
        ):
            if (
                data.loc[data.index[i], "Close"]
                > data.loc[data.index[i], "SMA_50"]
            ):
                num_bars_above_sma_50 += 1
            if (
                data.loc[data.index[i], "Close"]
                > data.loc[data.index[i], "SMA_200"]
            ):
                num_bars_above_sma_200 += 1

        if num_bars_above_sma_50 < 5 or num_bars_above_sma_200 < 5:
            logging.info("❌ not enough bars above sma50 or sma200")
            continue
        else:
            logging.info("✅ enough bars (5) above sma50 and sma200")

        # entry bar is the E, which is the reversal point of the trap
        uptrend_dates.append(point_e.name)
        # log out all the dateindex of 5 inflexion points abcde
        logging.info(
            [
                "M formation",
                point_a.name,
                point_b.name,
                point_c.name,
                point_d.name,
                point_e.name,
            ]
        )

    # sort uptrend_dates in ascending order
    uptrend_dates = sorted(uptrend_dates)

    if only_fetch_last:
        return uptrend_dates[-1:]
    
    return uptrend_dates


# @st.cache_data(ttl="1d")
def get_apex_downtrend_dates(data, custom_aggregate_2days = True, only_fetch_last = False):
    
    if custom_aggregate_2days:
        data = get_2day_aggregated_data(data)

    data["SMA_20"] = data["Close"].rolling(window=20).mean()
    data["SMA_50"] = data["Close"].rolling(window=50).mean()
    data["SMA_200"] = data["Close"].rolling(window=200).mean()

    high_inflexion_points = pd.DataFrame()
    low_inflexion_points = pd.DataFrame()
    for i in range(1, len(data) - 2):
        if (
            data["High"].iloc[i - 1]
            < data["High"].iloc[i]
            > data["High"].iloc[i + 1]
        ) and (
            data["High"].iloc[i - 2]
            < data["High"].iloc[i]
            > data["High"].iloc[i + 2]
        ):
            high_inflexion_points = pd.concat([high_inflexion_points, data.iloc[i].to_frame().T])
        elif (
            data["Low"].iloc[i - 1]
            > data["Low"].iloc[i]
            < data["Low"].iloc[i + 1]
        ) and (
            data["Low"].iloc[i - 2]
            > data["Low"].iloc[i]
            < data["Low"].iloc[i + 2]
        ):
            low_inflexion_points = pd.concat([low_inflexion_points, data.iloc[i].to_frame().T])

    downtrend_dates = []

    # N formation check
    for index, row in low_inflexion_points.iterrows():
        high_inflexion_point = row
        logging.info(
            f"checking for N formation starting at low inflexion point {high_inflexion_point.name}"
        )

        # Get price of first inflexion point
        point_a = high_inflexion_point

        # get point b which is the next high inflexion point that is after position of point a
        point_b = next(
            (point for index, point in high_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_b is None:
            logging.info("❌ no high inflexion point found after point A")
            continue

        # get point c which is the next low inflexion point that is after position of point a
        point_c = next(
            (point for index, point in low_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_c is None:
            logging.info("❌ no low inflexion point found after point B")
            continue

        # get point d which is the next high inflexion point that is after position of point c
        point_d = next(
            (point for index, point in high_inflexion_points.iterrows() if index > point_b.name),
            None,
        )
        if point_d is None:
            logging.info("❌ no high inflexion point found after point C")
            continue

        if not (point_a.name < point_b.name < point_c.name < point_d.name):
            logging.info("❌ Points A, B, C, D are not in chronological order")
            continue
        

        point_a_high_open_close = max(
            data.loc[point_a.name, "Open"], data.loc[point_a.name, "Close"]
        )
        point_a_low_open_close = min(
            data.loc[point_a.name, "Open"], data.loc[point_a.name, "Close"]
        )
        point_b_high_open_close = max(
            data.loc[point_b.name, "Open"], data.loc[point_b.name, "Close"]
        )
        point_b_low_open_close = min(
            data.loc[point_b.name, "Open"], data.loc[point_b.name, "Close"]
        )
        point_c_high_open_close = max(
            data.loc[point_c.name, "Open"], data.loc[point_c.name, "Close"]
        )
        point_c_low_open_close = min(
            data.loc[point_c.name, "Open"], data.loc[point_c.name, "Close"]
        )
        point_d_high_open_close = max(
            data.loc[point_d.name, "Open"], data.loc[point_d.name, "Close"]
        )
        point_d_low_open_close = min(
            data.loc[point_d.name, "Open"], data.loc[point_d.name, "Close"]
        )

        # Check for N. must start with low inflexion point, C must be higher than A , D must be higher than B and cross back to B (assume it just have to reverse in the direction, but havent reach B)
        if (
            point_d["Low"] > point_b["Low"] > point_c["Low"] > point_a["Low"]
            and point_d["High"] > point_b["High"] > point_c["High"] > point_a["High"]
            and point_d_high_open_close
            > point_b_high_open_close
            > point_c_high_open_close
            > point_a_high_open_close
            and point_d_low_open_close
            > point_b_low_open_close
            > point_c_low_open_close
            > point_a_low_open_close
        ):
            logging.info("VALID N FORMATION")
        else:
            logging.info("❌ not a N formation")
            continue

        # Between A to D, Check if at least 5 bars are FULLY below sma50

        num_bars_below_sma_50 = 0
        # loop through each bar between point a and d in data
        for i in range(
            data.index.get_loc(point_a.name),
            data.index.get_loc(point_d.name) + 1,
        ):
            # check if sma 200 is between sma 20 and sma 50, if between, then it is invalid N formation
            if (
                data.loc[data.index[i], "SMA_50"]
                > data.loc[data.index[i], "SMA_200"]
                > data.loc[data.index[i], "SMA_20"]
                or data.loc[data.index[i], "SMA_50"]
                < data.loc[data.index[i], "SMA_200"]
                < data.loc[data.index[i], "SMA_20"]
            ):
                logging.info("❌ sma200 is between sma20 and sma50")
                continue

            if (
                data.loc[data.index[i], "Close"]
                < data.loc[data.index[i], "SMA_50"]
            ):
                num_bars_below_sma_50 += 1

        if num_bars_below_sma_50 < 5:
            logging.info("❌ not enough bars below sma50")
            continue
        else:
            logging.info("✅ enough bars (5) below sma50")

        downtrend_dates.append(point_d.name)
        # log all the dateindex of 4 inflexion points abcd
        logging.info(
            [
                "N formation",
                point_a.name,
                point_b.name,
                point_c.name,
                point_d.name
            ]
        )

    # W formation check: D must be lower than  B and cross back to C to reach E (below A)
    for index, row in high_inflexion_points.iterrows():
        high_inflexion_point = row
        logging.info(
            f"checking for W formation starting at high inflexion point {high_inflexion_point.name}"
        )
        # Get price of first inflexion point
        point_a = high_inflexion_point
        
        point_b = next(
            (point for index, point in low_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_b is None:
            logging.info("❌ no low inflexion point found after point A")
            continue

        point_c = next(
            (point for index, point in high_inflexion_points.iterrows() if index > point_a.name),
            None,
        )
        if point_c is None:
            logging.info("❌ no high inflexion point found after point B")
            continue

        point_d = next(
            (point for index, point in low_inflexion_points.iterrows() if index > point_b.name),
            None,
        )
        if point_d is None:
            logging.info("❌ no low inflexion point found after point C")
            continue

        point_e = next(
            (point for index, point in high_inflexion_points.iterrows() if index > point_c.name),
            None,
        )
        if point_e is None:
            logging.info("❌ no high inflexion point found after point D")
            continue

        if not (point_a.name < point_b.name < point_c.name < point_d.name < point_e.name):
            logging.info("❌ Points A, B, C, D, E are not in chronological order")
            continue

        point_a_high_open_close = max(
            data.loc[point_a.name, "Open"], data.loc[point_a.name, "Close"]
        )
        point_a_low_open_close = min(
            data.loc[point_a.name, "Open"], data.loc[point_a.name, "Close"]
        )
        point_b_high_open_close = max(
            data.loc[point_b.name, "Open"], data.loc[point_b.name, "Close"]
        )
        point_b_low_open_close = min(
            data.loc[point_b.name, "Open"], data.loc[point_b.name, "Close"]
        )
        point_c_high_open_close = max(
            data.loc[point_c.name, "Open"], data.loc[point_c.name, "Close"]
        )
        point_c_low_open_close = min(
            data.loc[point_c.name, "Open"], data.loc[point_c.name, "Close"]
        )
        point_d_high_open_close = max(
            data.loc[point_d.name, "Open"], data.loc[point_d.name, "Close"]
        )
        point_d_low_open_close = min(
            data.loc[point_d.name, "Open"], data.loc[point_d.name, "Close"]
        )
        point_e_high_open_close = max(
            data.loc[point_e.name, "Open"], data.loc[point_e.name, "Close"]
        )
        point_e_low_open_close = min(
            data.loc[point_e.name, "Open"], data.loc[point_e.name, "Close"]
        )


        # Check for M formation. must start with low inflexion point, D must be lower than  B and cross back to C to reach E (below A)
        if (
            point_d["Low"]
            < point_b["Low"]
            < point_c["Low"]
            < point_e["Low"]
            < point_a["Low"]
            and point_d["High"]
            < point_b["High"]
            < point_c["High"]
            < point_e["High"]
            < point_a["High"]
            and point_d_high_open_close
            < point_b_high_open_close
            < point_c_high_open_close
            < point_e_high_open_close
            < point_a_high_open_close
            and point_d_low_open_close
            < point_b_low_open_close
            < point_c_low_open_close
            < point_e_low_open_close
            < point_a_low_open_close
        ):
            logging.info("VALID W FORMATION")
        else:
            logging.info("❌ not a W formation")
            continue

        # Between A to E, Check if at least 5 bars are FULLY below sma50

        num_bars_below_sma_50 = 0

        # loop through each bar between point a and e in data
        for i in range(
            data.index.get_loc(point_a.name),
            data.index.get_loc(point_e.name) + 1,
        ):
            # check if sma 200 is between sma 20 and sma 50, if between, then it is invalid N formation
            if (
                data.loc[data.index[i], "SMA_50"]
                > data.loc[data.index[i], "SMA_200"]
                > data.loc[data.index[i], "SMA_20"]
                or data.loc[data.index[i], "SMA_50"]
                < data.loc[data.index[i], "SMA_200"]
                < data.loc[data.index[i], "SMA_20"]
            ):
                logging.info("❌ sma200 is between sma20 and sma50")
                continue

            if (
                data.loc[data.index[i], "Close"]
                < data.loc[data.index[i], "SMA_50"]
            ):
                num_bars_below_sma_50 += 1
            

        if num_bars_below_sma_50 < 5:
            logging.info("❌ not enough bars below sma50")
            continue
        else:
            logging.info("✅ enough bars (5) below sma50")


        downtrend_dates.append(point_e.name)
        # log all the dateindex of 4 inflexion points abcd
        logging.info(
            [
                "W formation",
                point_a.name,
                point_b.name,
                point_c.name,
                point_d.name,
                point_e.name
            ]
        )

    # sort downtrend_dates in ascending order
    downtrend_dates = sorted(downtrend_dates)

    if only_fetch_last:
        return downtrend_dates[-1:]
    
    return downtrend_dates


def get_apex_bull_appear_dates(data, custom_aggregate_2days = True, only_fetch_last = False):

    if custom_aggregate_2days:
        data = get_2day_aggregated_data(data)

    if "Close" not in data.columns:
        # logging.info("The 'Close' column is missing from the data. Skipping...")
        return None
    
    data["SMA_20"] = data["Close"].rolling(window=20).mean()
    data["SMA_50"] = data["Close"].rolling(window=50).mean()
    data["SMA_200"] = data["Close"].rolling(window=200).mean()

    # Find dates where the high of the current day is lower than the high of the previous day = Kangaroo wallaby formation
    condition = (data["High"] < data["High"].shift(1)) & (
        data["Low"] > data["Low"].shift(1)
    )
    wallaby_dates = data.index[condition]
    if only_fetch_last:
        wallaby_dates = wallaby_dates[-1:]

    bull_appear_dates = []
    potential_bear_traps = get_low_inflexion_points(data)

    for date in wallaby_dates:
        # logging.info(f"======{date}======")
        wallaby_pos = data.index.get_loc(date)
        kangaroo_pos = wallaby_pos - 1

        # Get date index 1 year before date, approximately 126 indexes before
        start_index = max(0, wallaby_pos - 126)
        end_index = kangaroo_pos - 3

        active_bear_traps = find_bear_traps(
            potential_bear_traps,
            data.index[start_index],
            data.index[end_index],
        )

        any_bar_went_below_kangaroo = False
        bullish_bar_went_back_up_to_range = False

        # Condition 1: 200 SMA should slope upwards
        if (
            kangaroo_pos + 5 < len(data)
            and data["SMA_200"].iloc[kangaroo_pos]
            > data["SMA_200"].iloc[kangaroo_pos + 5]
        ):
            logging.info("Condition 1 not met: 200 SMA should slope upward")
            continue
        else:
            logging.info("Condition 1 met: 200 SMA slopes upwards")

        # Check the next 4 trading dates from wallaby date
        for i in range(1, 5):
            logging.info(f"Checking {i} days after wallaby date")
            target_pos = wallaby_pos + i
            if target_pos >= len(data):
                break

            curr_data = data.iloc[target_pos]
            curr_date = data.index[target_pos]

            # if high is higher than kangaroo, exit
            if (
                not any_bar_went_below_kangaroo
                and curr_data["High"] > data.iloc[kangaroo_pos]["High"]
            ):
                logging.info("Exiting because high is higher than kangaroo")
                break

            # Condition 2: Low below the low of the kangaroo wallaby,
            if (
                not any_bar_went_below_kangaroo
                and curr_data["Low"] < data.iloc[kangaroo_pos]["Low"]
            ):
                any_bar_went_below_kangaroo = True
                logging.info("Condition 3 met: broke below kangaroo lows")

            # Condition 3: must have one of 3 bullish bars (after going out of K range), close between low and high of kangaroo wallaby
            if (
                any_bar_went_below_kangaroo
                and not bullish_bar_went_back_up_to_range
                and data.iloc[kangaroo_pos]["Low"]
                <= curr_data["Close"]
                <= data.iloc[kangaroo_pos]["High"]
            ):
                if (
                    curr_data["Open"]
                    > curr_data["Low"] + 4 / 5 * (curr_data["High"] - curr_data["Low"])
                    and curr_data["Close"]
                    > curr_data["Low"] + 4 / 5 * (curr_data["High"] - curr_data["Low"])
                ) or curr_data["Close"] - curr_data["Open"] > 0.5 * (
                    curr_data["High"] - curr_data["Low"]
                ):
                    bullish_bar_went_back_up_to_range = True
                    logging.info(
                        "Condition 4 met: bullish bar close between low and high "
                    )
                    break

        if not any_bar_went_below_kangaroo or not bullish_bar_went_back_up_to_range:
            continue

        # Condition 4: active bear trap must be taken between K-3 and K+5
        # OR if K-K+5 touches 20sma, 50 sma or 200 sma from below
        for i in range(0, 6):
            curr_pos = end_index + i
            if curr_pos >= len(data):
                break
            curr_data = data.iloc[curr_pos]
            logging.info(
                f"Trying to find bear trap or touching of sma for {curr_data.name}"
            )
            if any(
                trap[1] > curr_data["Low"] and trap[1] < curr_data["High"]
                for trap in active_bear_traps
            ):
                pass
                logging.info(f"Condition 5a met: bear trap met!, {active_bear_traps}")

            # else if touches sma20, sma50 or sma200
            elif (
                i > 0  # only valid if K onwards touches sma (Try between low and close)
                and (
                    curr_data["Low"]
                    <= data["SMA_20"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= data["SMA_50"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= data["SMA_200"].iloc[curr_pos]
                    <= curr_data["High"]
                )
            ):
                pass
                logging.info(
                    f"Condition 5b met: touches SMA 20, 50 or 200: {curr_data['Low']}, {curr_data['High']}"
                )
                logging.info(
                    f"SMAs are {data['SMA_20'].iloc[curr_pos]}, {data['SMA_50'].iloc[curr_pos]}, {data['SMA_200'].iloc[curr_pos]}"
                )
            else:
                continue

            bull_appear_dates.append(curr_date)

            logging.info(
                "✅ Wallaby date: "
                + str(date)
                + "; Bull appear date: "
                + str(curr_date)
            )
            break

    return pd.DatetimeIndex(bull_appear_dates)


def get_apex_bear_appear_dates(data, custom_aggregate_2days = True, only_fetch_last = False):

    if custom_aggregate_2days:
        data = get_2day_aggregated_data(data)

    if "Close" not in data.columns:
        logging.info("The 'Close' column is missing from the data. Skipping...")
        return None
    data["SMA_20"] = data["Close"].rolling(window=20).mean()
    data["SMA_50"] = data["Close"].rolling(window=50).mean()
    data["SMA_200"] = data["Close"].rolling(window=200).mean()

    # Find dates where the high of the current day is lower than the high of the previous day = Kangaroo wallaby formation
    condition = (data["High"] < data["High"].shift(1)) & (
        data["Low"] > data["Low"].shift(1)
    )
    wallaby_dates = data.index[condition]

    if only_fetch_last:
        wallaby_dates = wallaby_dates[-1:]
    bear_appear_dates = []
    potential_bull_traps = get_high_inflexion_points(data)

    for date in wallaby_dates:
        logging.info(f"======{date}======")
        wallaby_pos = data.index.get_loc(date)
        kangaroo_pos = wallaby_pos - 1

        # Get date index 1 year before date, approximately 126 indexes before
        start_index = max(0, wallaby_pos - 126)
        end_index = kangaroo_pos - 3

        active_bull_traps = find_bull_traps(
            potential_bull_traps,
            data.index[start_index],
            data.index[end_index],
        )

        any_bar_went_above_kangaroo = False
        bearish_bar_went_back_down_to_range = False

        # Condition 1: 50 SMA should slope downwards??
        if (
            kangaroo_pos + 5 < len(data)
            and data["SMA_50"].iloc[kangaroo_pos]
            < data["SMA_50"].iloc[kangaroo_pos + 5]
        ):
            logging.info("Condition 1 FAILED: 50 SMA slopes upwards when it should slope downwards")
            continue
        else:
            logging.info("Condition 1 met: 50 SMA slopes downwards")

        # Check the next 4 trading dates from wallaby date
        for i in range(1, 5):
            # logging.info(f"Checking {i} days after wallaby date")
            target_pos = wallaby_pos + i
            if target_pos >= len(data):
                break

            curr_data = data.iloc[target_pos]
            curr_date = data.index[target_pos]

            # if low is lower than kangaroo, exit
            if (
                not any_bar_went_above_kangaroo
                and curr_data["Low"] < data.iloc[kangaroo_pos]["Low"]
            ):
                logging.info("Exiting because low is lower than kangaroo")
                break

            # Condition 2: High above the high of the kangaroo wallaby,
            if (
                not any_bar_went_above_kangaroo
                and curr_data["High"] > data.iloc[kangaroo_pos]["High"]
            ):
                any_bar_went_above_kangaroo = True
                logging.info("Condition 3 met: broke above kangaroo highs")

            # Condition 3: must have one of 3 bearish bars (after going out of K range), close between low and high of kangaroo wallaby
            if (
                any_bar_went_above_kangaroo
                and not bearish_bar_went_back_down_to_range
                and data.iloc[kangaroo_pos]["Low"]
                <= curr_data["Close"]
                <= data.iloc[kangaroo_pos]["High"]
            ):
                if (
                    curr_data["Open"]
                    < curr_data["Low"] + 1 / 5 * (curr_data["High"] - curr_data["Low"])
                    and curr_data["Close"]
                    < curr_data["Low"] + 1 / 5 * (curr_data["High"] - curr_data["Low"])
                ) or curr_data["Open"] - curr_data["Close"] > 0.5 * (
                    curr_data["High"] - curr_data["Low"]
                ):
                    bearish_bar_went_back_down_to_range = True
                    logging.info("Condition 4 met: bullish bar close between low and high ")
                    break

        if not any_bar_went_above_kangaroo or not bearish_bar_went_back_down_to_range:
            continue

        # Condition 4: active bear trap must be taken between K-3 and K+5
        # OR if K-K+5 touches 20sma, 50 sma or 200 sma from below
        for i in range(0, 6):
            curr_pos = end_index + i
            if curr_pos >= len(data):
                break
            curr_data = data.iloc[curr_pos]
            logging.info(f"Trying to find bear trap or touching of sma for {curr_data.name}")
            if any(
                trap[1] > curr_data["Low"] and trap[1] < curr_data["High"]
                for trap in active_bull_traps
            ):
                pass
                logging.info(f"Condition 5a met: bear trap met!, {active_bull_traps}")

            # else if touches sma20, sma50 or sma200
            elif (
                i > 0  # only valid if K onwards touches sma (Try between low and close)
                and (
                    curr_data["Low"]
                    <= data["SMA_20"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= data["SMA_50"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= data["SMA_200"].iloc[curr_pos]
                    <= curr_data["High"]
                )
            ):
                pass
                logging.info(
                    f"Condition 5b met: touches SMA 20, 50 or 200: {curr_data['Low']}, {curr_data['High']}"
                )
                # logging.info(f"SMAs are {data["SMA_20"].iloc[curr_pos]}, {data["SMA_50"].iloc[curr_pos]}, {data["SMA_200"].iloc[curr_pos]}")
            else:
                continue

            bear_appear_dates.append(curr_date)

            logging.info(
                "✅ Wallaby date: "
                + str(date)
                + "; Bear appear date: "
                + str(curr_date)
            )
            break

    return pd.DatetimeIndex(bear_appear_dates)


def get_golden_cross_sma_dates(data, short_window=50, long_window=200):
    data[f"SMA_{short_window}"] = data["Close"].rolling(window=short_window).mean()
    data[f"SMA_{long_window}"] = data["Close"].rolling(window=long_window).mean()
    data[f"Prev_SMA_{short_window}"] = data[f"SMA_{short_window}"].shift(1)
    data[f"Prev_SMA_{long_window}"] = data[f"SMA_{long_window}"].shift(1)

    golden_cross = (data[f"SMA_{short_window}"] > data[f"SMA_{long_window}"]) & (
        data[f"Prev_SMA_{short_window}"] <= data[f"Prev_SMA_{long_window}"]
    )

    golden_cross_dates = golden_cross[golden_cross].index
    return golden_cross_dates


def get_death_cross_sma_dates(data, short_window=50, long_window=200):
    data[f"SMA_{short_window}"] = data["Close"].rolling(window=short_window).mean()
    data[f"SMA_{long_window}"] = data["Close"].rolling(window=long_window).mean()
    data[f"Prev_SMA_{short_window}"] = data[f"SMA_{short_window}"].shift(1)
    data[f"Prev_SMA_{long_window}"] = data[f"SMA_{long_window}"].shift(1)

    death_cross = (data[f"SMA_{short_window}"] < data[f"SMA_{long_window}"]) & (
        data[f"Prev_SMA_{short_window}"] >= data[f"Prev_SMA_{long_window}"]
    )
    death_cross_dates = death_cross[death_cross].index

    return death_cross_dates


# def get_rsi_overbought_dates(data, threshold=70):
#     delta = data["Close"].diff()
#     gain = delta.where(delta > 0, 0)
#     loss = -delta.where(delta < 0, 0)
#     avg_gain = gain.ewm(com=13, adjust=False).mean()
#     avg_loss = loss.ewm(com=13, adjust=False).mean()
#     rs = avg_gain / avg_loss
#     data["RSI"] = 100 - (100 / (1 + rs))
#     if data["RSI"].empty:
#         return False
#     overbought = data["RSI"] > threshold
#     overbought_dates = overbought[overbought].index

#     return overbought_dates


# def get_rsi_oversold_dates(data, threshold=30):
#     delta = data["Close"].diff()
#     gain = delta.where(delta > 0, 0)
#     loss = -delta.where(delta < 0, 0)
#     avg_gain = gain.ewm(com=13, adjust=False).mean()
#     avg_loss = loss.ewm(com=13, adjust=False).mean()
#     rs = avg_gain / avg_loss
#     data["RSI"] = 100 - (100 / (1 + rs))

#     oversold = data["RSI"] < threshold
#     oversold_dates = oversold[oversold].index
#     return oversold_dates


# def get_macd_bullish_dates(data, short_window=12, long_window=26, signal_window=9):
#     data["Short_EMA"] = data["Close"].ewm(span=short_window, adjust=False).mean()
#     data["Long_EMA"] = data["Close"].ewm(span=long_window, adjust=False).mean()
#     data["MACD"] = data["Short_EMA"] - data["Long_EMA"]
#     data["Signal_Line"] = data["MACD"].ewm(span=signal_window, adjust=False).mean()

#     bullish = (data["MACD"] > data["Signal_Line"]) & (
#         data["MACD"].shift(1) <= data["Signal_Line"].shift(1)
#     )
#     bullish_dates = bullish[bullish].index
#     return bullish_dates


# def get_macd_bearish_dates(data, short_window=12, long_window=26, signal_window=9):
#     data["Short_EMA"] = data["Close"].ewm(span=short_window, adjust=False).mean()
#     data["Long_EMA"] = data["Close"].ewm(span=long_window, adjust=False).mean()
#     data["MACD"] = data["Short_EMA"] - data["Long_EMA"]
#     data["Signal_Line"] = data["MACD"].ewm(span=signal_window, adjust=False).mean()

#     bearish = (data["MACD"] < data["Signal_Line"]) & (
#         data["MACD"].shift(1) >= data["Signal_Line"].shift(1)
#     )
#     bearish_dates = bearish[bearish].index
#     return bearish_dates


# def get_bollinger_band_squeeze_dates(data, window=20, num_std_dev=2):
#     data["Middle_Band"] = data["Close"].rolling(window=window).mean()
#     data["Upper_Band"] = (
#         data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
#     )
#     data["Lower_Band"] = (
#         data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
#     )

#     squeeze = (data["Upper_Band"] - data["Lower_Band"]) / data["Middle_Band"] <= 0.05
#     squeeze_dates = squeeze[squeeze].index
#     return squeeze_dates


# def get_bollinger_band_expansion_dates(data, window=20, num_std_dev=2):
#     data["Middle_Band"] = data["Close"].rolling(window=window).mean()
#     data["Upper_Band"] = (
#         data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
#     )
#     data["Lower_Band"] = (
#         data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
#     )

#     expansion = (data["Upper_Band"] - data["Lower_Band"]) / data["Middle_Band"] >= 0.1
#     expansion_dates = expansion[expansion].index
#     return expansion_dates


# def get_bollinger_band_breakout_dates(data, window=20, num_std_dev=2):
#     data["Middle_Band"] = data["Close"].rolling(window=window).mean()
#     data["Upper_Band"] = (
#         data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
#     )
#     data["Lower_Band"] = (
#         data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
#     )

#     breakout = data["Close"] > data["Upper_Band"]
#     breakout_dates = breakout[breakout].index
#     return breakout_dates


# def get_bollinger_band_pullback_dates(data, window=20, num_std_dev=2):
#     data["Middle_Band"] = data["Close"].rolling(window=window).mean()
#     data["Upper_Band"] = (
#         data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
#     )
#     data["Lower_Band"] = (
#         data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
#     )

#     pullback = data["Close"] < data["Lower_Band"]
#     pullback_dates = pullback[pullback].index
#     return pullback_dates


# def get_volume_spike_dates(data, window=20, num_std_dev=2):
#     data["Volume_MA"] = data["Volume"].rolling(window=window).mean()
#     data["Volume_MA_std"] = data["Volume"].rolling(window=window).std()

#     spike = data["Volume"] > data["Volume_MA"] + num_std_dev * data["Volume_MA_std"]
#     spike_dates = spike[spike].index
#     return spike_dates
