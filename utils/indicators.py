import pandas as pd

from utils.indicator_helpers import (
    get_2day_aggregated_data,
    get_high_inflexion_points,
    get_low_inflexion_points,
    find_lowest_bear_trap_within_price_range,
    find_highest_bull_trap_within_price_range,
    find_bear_traps,
    find_bull_traps,
)

def get_apex_bull_raging_dates(data):
    data = get_2day_aggregated_data(data)

    high_inflexion_points = get_high_inflexion_points(data)
    potential_bear_traps = get_low_inflexion_points(data)

    future_bear_traps = potential_bear_traps.copy()

    bull_raging_dates = []

    for high_point in high_inflexion_points:
        high_point_date, high_point_value = high_point
        # print(f"************ checking {high_point_date}: ************")
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

        # print(f"stopping point date: {stopping_point_date}")

        previous_bear_trap = find_lowest_bear_trap_within_price_range(
            tuple(potential_bear_traps),
            high_point_date,
            data.loc[stopping_point_date]["Low"],
            high_point_value,
        )

        if previous_bear_trap is None:
            # print("❌ no previous bear trap found")
            continue
        # print(f"previous_bear_trap: {previous_bear_trap}")

        mid_point = (
            previous_bear_trap[1] + (high_point_value - previous_bear_trap[1]) / 2
        )

        # Analyze the range from high point to stopping point
        range_data = data.loc[high_point_date:stopping_point_date]
        flush_down_mask = (range_data["Open"] - range_data["Close"]) > 0.7 * (
            range_data["High"] - range_data["Low"]
        )
        flush_down_bars = range_data[flush_down_mask]

        if flush_down_bars.empty or flush_down_bars.iloc[0]["High"] < mid_point:
            # print(
            #     "❌ first flush down started after mid point, or didn't happen at all"
            # )
            continue
        # print(
        #     f"✅ first flush down started at {flush_down_bars.iloc[0]['High']} before mid point {mid_point}"
        # )

        # Find the date which broke below bear trap
        break_below_bear_trap = range_data.index[
            range_data["Low"] < previous_bear_trap[1]
        ]
        if break_below_bear_trap.empty:
            # print(
            #     f"❌ no break below bear trap {previous_bear_trap} before the price reaches stopping point"
            # )
            continue
        date_which_broke_below_bear_trap = break_below_bear_trap[0]
        # print(
        #     f"✅ date_which_broke_below_bear_trap: {date_which_broke_below_bear_trap}"
        # )

        total_bar_count = len(range_data)
        flush_down_count = flush_down_mask.sum()
        if total_bar_count < 5 or flush_down_count / total_bar_count < 0.3:
            # print(
            #     f"❌ less than 5 bars or not majority flush down, flush down bars: {flush_down_count}, total bars: {total_bar_count}"
            # )
            continue
        # print(
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
                # print(
                #     f"🚀 {date} closed at {row['Close']}; above bear trap. All Conditions met!"
                # )
                bull_raging_dates.append(date)
                break
            # else:
            # print(f"❌ check bar {i}, no bullish bar closing above stop loss zone")

    return bull_raging_dates


def get_apex_bear_raging_dates(data):
    data = get_2day_aggregated_data(data)

    low_inflexion_points = get_low_inflexion_points(data)
    potential_bull_traps = get_high_inflexion_points(data)

    future_bull_traps = potential_bull_traps.copy()

    bear_raging_dates = []

    for low_point in low_inflexion_points:
        low_point_date, low_point_value = low_point
        # print(f"************ checking {low_point_date}: ************")
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

        # print(f"stopping point date: {stopping_point_date}")

        previous_bull_trap = find_highest_bull_trap_within_price_range(
            tuple(potential_bull_traps),
            low_point_date,
            low_point_value,
            data.loc[stopping_point_date]["High"],
        )

        if previous_bull_trap is None:
            # print("❌ no previous bull trap found")
            continue
        # print(f"previous_bull_trap: {previous_bull_trap}")

        mid_point = (
            previous_bull_trap[1] + (low_point_value - previous_bull_trap[1]) / 2
        )

        # Analyze the range from low point to stopping point
        range_data = data.loc[low_point_date:stopping_point_date]
        flush_up_mask = (range_data["Close"] - range_data["Open"]) > 0.7 * (
            range_data["High"] - range_data["Low"]
        )
        flush_up_bars = range_data[flush_up_mask]

        if flush_up_bars.empty or flush_up_bars.iloc[0]["Low"] > mid_point:
            # print("❌ first flush up started after mid point, or didn't happen at all")
            continue
        # print(
        #     f"✅ first flush up started at {flush_up_bars.iloc[0]['Low']} before mid point {mid_point}"
        # )

        # Find the date which broke above bull trap
        break_above_bull_trap = range_data.index[
            range_data["High"] > previous_bull_trap[1]
        ]
        if break_above_bull_trap.empty:
            # print(
            #     f"❌ no break above bull trap {previous_bull_trap} before the price reaches stopping point"
            # )
            continue
        date_which_broke_above_bull_trap = break_above_bull_trap[0]
        # print(
        #     f"✅ date_which_broke_above_bull_trap: {date_which_broke_above_bull_trap}"
        # )

        total_bar_count = len(range_data)
        flush_up_count = flush_up_mask.sum()

        if total_bar_count < 5 or flush_up_count / total_bar_count < 0.3:
            # print(
            #     f"❌ less than 5 bars or not majority flush up, flush up bars: {flush_up_count}, total bars: {total_bar_count}"
            # )
            continue
        # print(
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
                # print(
                #     f"🚀 {date} closed at {row['Close']}; below bull trap {previous_bull_trap[1]}. All Conditions met!"
                # )
                bear_raging_dates.append(date)
                break
            # else:
                # print(f"❌ check bar {i}, no bearish bar closing below stop loss zone")

    return bear_raging_dates


# @st.cache_data(ttl="1d")
def get_apex_uptrend_dates(data):
    data["SMA_50"] = data["Close"].rolling(window=50).mean()
    data["SMA_200"] = data["Close"].rolling(window=200).mean()

    agg_data = get_2day_aggregated_data(data)

    high_inflexion_points = []
    low_inflexion_points = []
    for i in range(1, len(agg_data) - 2):
        if (
            agg_data["High"][i - 1] < agg_data["High"][i] > agg_data["High"][i + 1]
        ) and (agg_data["High"][i - 2] < agg_data["High"][i] > agg_data["High"][i + 2]):
            high_inflexion_points.append(agg_data.index[i])
        elif (
            agg_data["Low"][i - 1] > agg_data["Low"][i] < agg_data["Low"][i + 1]
        ) and (agg_data["Low"][i - 2] > agg_data["Low"][i] < agg_data["Low"][i + 2]):
            low_inflexion_points.append(agg_data.index[i])

    inflexion_points = sorted(high_inflexion_points + low_inflexion_points)
    inflexion_data = agg_data.loc[inflexion_points, ["High", "Low"]]
    inflexion_data = pd.DataFrame(inflexion_data)

    uptrend_dates = []

    # LIGHTNING formation check
    for inflexion_point in high_inflexion_points:
        print(
            f"checking lightning formation for high inflexion point {inflexion_point}"
        )
        # get index of inflexion point
        inflexion_point_pos = inflexion_data.index.get_loc(inflexion_point)

        # if inflexion point is one of the last 4 datapoints, skip
        if inflexion_point_pos >= len(inflexion_data) - 4:
            print("broke out because too close to the end")
            break

        # TODO: ensure its alternate. high, low, high, low

        # Get price of first inflexion point
        point_a = inflexion_data.iloc[inflexion_point_pos]
        point_b = inflexion_data.iloc[inflexion_point_pos + 1]
        point_c = inflexion_data.iloc[inflexion_point_pos + 2]
        point_d = inflexion_data.iloc[inflexion_point_pos + 3]

        # Check for lightning. must start with high inflexion point, C must be lower than A ,   D must be lower than B and cross back to B (assume it just have to reverse in the direction, but havent reach B)
        if (
            point_d["High"] < point_b["High"] < point_c["High"] < point_a["High"]
            and point_d["Low"] < point_b["Low"] < point_c["Low"] < point_a["Low"]
        ):
            # Check if all points are above sma50 and sma200
            if (
                (point_a["Low"] < data.loc[point_a.name, "SMA_50"])
                or (point_a["Low"] < data.loc[point_a.name, "SMA_200"])
                or (point_b["Low"] < data.loc[point_b.name, "SMA_50"])
                or (point_b["Low"] < data.loc[point_b.name, "SMA_200"])
                or (point_c["Low"] < data.loc[point_c.name, "SMA_50"])
                or (point_c["Low"] < data.loc[point_c.name, "SMA_200"])
                or (point_d["Low"] < data.loc[point_d.name, "SMA_50"])
                or (point_d["Low"] < data.loc[point_d.name, "SMA_200"])
            ):
                print("❌exit because below sma")
                continue

            print("✅ all above sma")

            # add all the dateindex of 4 inflexion points abcd
            uptrend_dates.append(inflexion_data.index[inflexion_point_pos + 3])
            print(
                [
                    "Lightning formation",
                    inflexion_point,
                    inflexion_data.index[inflexion_point_pos + 1],
                    inflexion_data.index[inflexion_point_pos + 2],
                    inflexion_data.index[inflexion_point_pos + 3],
                ]
            )

    # M formation check: D must be higher than  B and cross back to C to reach E (above A)
    for inflexion_point in low_inflexion_points:
        print(f"checking M formation for low inflexion point {inflexion_point}")
        # get index of inflexion point
        inflexion_point_pos = inflexion_data.index.get_loc(inflexion_point)
        # if inflexion point is one of the last 5 datapoints, skip
        if inflexion_point_pos >= len(inflexion_data) - 5:
            break

        # Get price of first inflexion point
        point_a = inflexion_data.iloc[inflexion_point_pos]
        point_b = inflexion_data.iloc[inflexion_point_pos + 1]
        point_c = inflexion_data.iloc[inflexion_point_pos + 2]
        point_d = inflexion_data.iloc[inflexion_point_pos + 3]
        point_e = inflexion_data.iloc[inflexion_point_pos + 4]

        # Check for M formation. must start with low inflexion point, D must be higher than B, and cross back to C to reach E (above A)
        if (
            point_d["High"]
            > point_b["High"]
            > point_c["High"]
            > point_e["High"]
            > point_a["High"]
            and point_d["Low"]
            > point_b["Low"]
            > point_c["Low"]
            > point_e["Low"]
            > point_a["Low"]
        ):
            # Check if all points are above sma50 and sma200
            if (
                (point_a["Low"] < data.loc[point_a.name, "SMA_50"])
                or (point_a["Low"] < data.loc[point_a.name, "SMA_200"])
                or (point_b["Low"] < data.loc[point_b.name, "SMA_50"])
                or (point_b["Low"] < data.loc[point_b.name, "SMA_200"])
                or (point_c["Low"] < data.loc[point_c.name, "SMA_50"])
                or (point_c["Low"] < data.loc[point_c.name, "SMA_200"])
                or (point_d["Low"] < data.loc[point_d.name, "SMA_50"])
                or (point_d["Low"] < data.loc[point_d.name, "SMA_200"])
                or (point_e["Low"] < data.loc[point_e.name, "SMA_50"])
                or (point_e["Low"] < data.loc[point_e.name, "SMA_200"])
            ):
                continue
            # add all the dateindex of 4 inflexion points abcd
            uptrend_dates.append(inflexion_data.index[inflexion_point_pos + 4])
            print(
                [
                    "M formation",
                    inflexion_point,
                    inflexion_data.index[inflexion_point_pos + 1],
                    inflexion_data.index[inflexion_point_pos + 2],
                    inflexion_data.index[inflexion_point_pos + 3],
                    inflexion_data.index[inflexion_point_pos + 4],
                ]
            )

    return uptrend_dates


# @st.cache_data(ttl="1d")
def get_apex_downtrend_dates(data):
    data["SMA_50"] = data["Close"].rolling(window=50).mean()

    agg_data = get_2day_aggregated_data(data)

    high_inflexion_points = []
    low_inflexion_points = []
    for i in range(1, len(agg_data) - 2):
        if (
            agg_data["High"][i - 1] < agg_data["High"][i] > agg_data["High"][i + 1]
        ) and (agg_data["High"][i - 2] < agg_data["High"][i] > agg_data["High"][i + 2]):
            high_inflexion_points.append(agg_data.index[i])
        elif (
            agg_data["Low"][i - 1] > agg_data["Low"][i] < agg_data["Low"][i + 1]
        ) and (agg_data["Low"][i - 2] > agg_data["Low"][i] < agg_data["Low"][i + 2]):
            low_inflexion_points.append(agg_data.index[i])

    inflexion_points = sorted(high_inflexion_points + low_inflexion_points)
    inflexion_data = agg_data.loc[inflexion_points, ["High", "Low"]]
    inflexion_data = pd.DataFrame(inflexion_data)

    downtrend_dates = []

    # N formation check
    for inflexion_point in low_inflexion_points:
        # get index of inflexion point
        inflexion_point_pos = inflexion_data.index.get_loc(inflexion_point)
        # if inflexion point is one of the last 4 datapoints, skip
        if inflexion_point_pos >= len(inflexion_data) - 4:
            break

        # Get price of first inflexion point
        point_a = inflexion_data.iloc[inflexion_point_pos]
        point_b = inflexion_data.iloc[inflexion_point_pos + 1]
        point_c = inflexion_data.iloc[inflexion_point_pos + 2]
        point_d = inflexion_data.iloc[inflexion_point_pos + 3]

        # Check for N. must start with low inflexion point, C must be higher than A , D must be higher than B and cross back to B (assume it just have to reverse in the direction, but havent reach B)
        if (
            point_d["Low"] > point_b["Low"] > point_c["Low"] > point_a["Low"]
            and point_d["High"] > point_b["High"] > point_c["High"] > point_a["High"]
        ):
            # Check if all points are below sma50
            if (
                (point_a["Low"] > data.loc[point_a.name, "SMA_50"])
                or (point_b["Low"] > data.loc[point_b.name, "SMA_50"])
                or (point_c["Low"] > data.loc[point_c.name, "SMA_50"])
                or (point_d["Low"] > data.loc[point_d.name, "SMA_50"])
            ):
                continue

            # add all the dateindex of 4 inflexion points abcd
            downtrend_dates.append(inflexion_data.index[inflexion_point_pos + 3])
            print(
                [
                    "N formation",
                    inflexion_point,
                    inflexion_data.index[inflexion_point_pos + 1],
                    inflexion_data.index[inflexion_point_pos + 2],
                    inflexion_data.index[inflexion_point_pos + 3],
                ]
            )

    # W formation check: D must be lower than  B and cross back to C to reach E (below A)
    for inflexion_point in high_inflexion_points:
        # get index of inflexion point
        inflexion_point_pos = inflexion_data.index.get_loc(inflexion_point)
        # if inflexion point is one of the last 5 datapoints, skip
        if inflexion_point_pos >= len(inflexion_data) - 5:
            break

        # Get price of first inflexion point
        point_a = inflexion_data.iloc[inflexion_point_pos]
        point_b = inflexion_data.iloc[inflexion_point_pos + 1]
        point_c = inflexion_data.iloc[inflexion_point_pos + 2]
        point_d = inflexion_data.iloc[inflexion_point_pos + 3]
        point_e = inflexion_data.iloc[inflexion_point_pos + 4]

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
        ):
            # Check if all points are below sma50
            if (
                (point_a["Low"] > data.loc[point_a.name, "SMA_50"])
                or (point_b["Low"] > data.loc[point_b.name, "SMA_50"])
                or (point_c["Low"] > data.loc[point_c.name, "SMA_50"])
                or (point_d["Low"] > data.loc[point_d.name, "SMA_50"])
                or (point_e["Low"] > data.loc[point_e.name, "SMA_50"])
            ):
                continue
            # add all the dateindex of 4 inflexion points abcd
            downtrend_dates.append(inflexion_data.index[inflexion_point_pos + 4])
            print(
                [
                    "W formation",
                    inflexion_point,
                    inflexion_data.index[inflexion_point_pos + 1],
                    inflexion_data.index[inflexion_point_pos + 2],
                    inflexion_data.index[inflexion_point_pos + 3],
                ]
            )

    return downtrend_dates


def get_apex_bull_appear_dates(data):
    aggregated_data = get_2day_aggregated_data(data)

    if "Close" not in aggregated_data.columns:
        # print("The 'Close' column is missing from the data. Skipping...")
        return None
    aggregated_data["SMA_20"] = aggregated_data["Close"].rolling(window=20).mean()
    aggregated_data["SMA_50"] = aggregated_data["Close"].rolling(window=50).mean()
    aggregated_data["SMA_200"] = aggregated_data["Close"].rolling(window=200).mean()

    # Find dates where the high of the current day is lower than the high of the previous day = Kangaroo wallaby formation
    condition = (aggregated_data["High"] < aggregated_data["High"].shift(1)) & (
        aggregated_data["Low"] > aggregated_data["Low"].shift(1)
    )
    wallaby_dates = aggregated_data.index[condition]

    bull_appear_dates = []
    potential_bear_traps = get_low_inflexion_points(aggregated_data)

    for date in wallaby_dates:
        # print(f"======{date}======")
        wallaby_pos = aggregated_data.index.get_loc(date)
        kangaroo_pos = wallaby_pos - 1

        # Get date index 1 year before date, approximately 126 indexes before
        start_index = max(0, wallaby_pos - 126)
        end_index = kangaroo_pos - 3

        active_bear_traps = find_bear_traps(
            potential_bear_traps,
            aggregated_data.index[start_index],
            aggregated_data.index[end_index],
        )

        any_bar_went_below_kangaroo = False
        bullish_bar_went_back_up_to_range = False

        # Condition 1: 200 SMA should slope upwards
        if (
            kangaroo_pos + 5 < len(aggregated_data)
            and aggregated_data["SMA_200"].iloc[kangaroo_pos]
            > aggregated_data["SMA_200"].iloc[kangaroo_pos + 5]
        ):
            # print("Condition 1 not met: 200 SMA should slope upward")
            continue
        # else:
        #     print("Condition 1 met: 200 SMA slopes upwards")

        # Condition 2: Should be above 50 sma (roughly)
        if (
            aggregated_data["Low"].iloc[kangaroo_pos]
            > aggregated_data["SMA_50"].iloc[kangaroo_pos]
        ):
            pass
            # print(
            #     f"Condition 2 met: K Low is above 50 sma: {aggregated_data['Low'].iloc[kangaroo_pos]} {aggregated_data['SMA_50'].iloc[kangaroo_pos]}"
            # )
        else:
            # print(
            #     f"Condition 2 not met: K Low should be above 50 sma {aggregated_data['Low'].iloc[kangaroo_pos]} {aggregated_data['SMA_50'].iloc[kangaroo_pos]}"
            # )
            continue

        # Check the next 4 trading dates from wallaby date
        for i in range(1, 5):
            # print(f"Checking {i} days after wallaby date")
            target_pos = wallaby_pos + i
            if target_pos >= len(aggregated_data):
                break

            curr_data = aggregated_data.iloc[target_pos]
            curr_date = aggregated_data.index[target_pos]

            # if high is higher than kangaroo, exit
            if (
                not any_bar_went_below_kangaroo
                and curr_data["High"] > aggregated_data.iloc[kangaroo_pos]["High"]
            ):
                # print("Exiting because high is higher than kangaroo")
                break

            # Condition 2: Low below the low of the kangaroo wallaby,
            if (
                not any_bar_went_below_kangaroo
                and curr_data["Low"] < aggregated_data.iloc[kangaroo_pos]["Low"]
            ):
                any_bar_went_below_kangaroo = True
                # print("Condition 3 met: broke below kangaroo lows")

            # Condition 3: must have one of 3 bullish bars (after going out of K range), close between low and high of kangaroo wallaby
            if (
                any_bar_went_below_kangaroo
                and not bullish_bar_went_back_up_to_range
                and aggregated_data.iloc[kangaroo_pos]["Low"]
                <= curr_data["Close"]
                <= aggregated_data.iloc[kangaroo_pos]["High"]
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
                    # print("Condition 4 met: bullish bar close between low and high ")
                    break

        if not any_bar_went_below_kangaroo or not bullish_bar_went_back_up_to_range:
            continue

        # Condition 4: active bear trap must be taken between K-3 and K+5
        # OR if K-K+5 touches 20sma, 50 sma or 200 sma from below
        for i in range(0, 6):
            curr_pos = end_index + i
            if curr_pos >= len(aggregated_data):
                break
            curr_data = aggregated_data.iloc[curr_pos]
            # print(f"Trying to find bear trap or touching of sma for {curr_data.name}")
            if any(
                trap[1] > curr_data["Low"] and trap[1] < curr_data["High"]
                for trap in active_bear_traps
            ):
                pass
                # print(f"Condition 5a met: bear trap met!, {active_bear_traps}")

            # else if touches sma20, sma50 or sma200
            elif (
                i > 0  # only valid if K onwards touches sma (Try between low and close)
                and (
                    curr_data["Low"]
                    <= aggregated_data["SMA_20"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= aggregated_data["SMA_50"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= aggregated_data["SMA_200"].iloc[curr_pos]
                    <= curr_data["High"]
                )
            ):
                pass
                # print(
                #     f"Condition 5b met: touches SMA 20, 50 or 200: {curr_data['Low']}, {curr_data['High']}"
                # )
                # print(f"SMAs are {aggregated_data["SMA_20"].iloc[curr_pos]}, {aggregated_data["SMA_50"].iloc[curr_pos]}, {aggregated_data["SMA_200"].iloc[curr_pos]}")
            else:
                continue

            bull_appear_dates.append(curr_date)

            # print(
            #     "✅ Wallaby date: "
            #     + str(date)
            #     + "; Bull appear date: "
            #     + str(curr_date)
            # )
            break

    return pd.DatetimeIndex(bull_appear_dates)


def get_apex_bear_appear_dates(data):
    aggregated_data = get_2day_aggregated_data(data)

    if "Close" not in aggregated_data.columns:
        # print("The 'Close' column is missing from the data. Skipping...")
        return None
    aggregated_data["SMA_20"] = aggregated_data["Close"].rolling(window=20).mean()
    aggregated_data["SMA_50"] = aggregated_data["Close"].rolling(window=50).mean()
    aggregated_data["SMA_200"] = aggregated_data["Close"].rolling(window=200).mean()

    # Find dates where the high of the current day is lower than the high of the previous day = Kangaroo wallaby formation
    condition = (aggregated_data["High"] < aggregated_data["High"].shift(1)) & (
        aggregated_data["Low"] > aggregated_data["Low"].shift(1)
    )
    wallaby_dates = aggregated_data.index[condition]

    bear_appear_dates = []
    potential_bull_traps = get_high_inflexion_points(aggregated_data)

    for date in wallaby_dates:
        # print(f"======{date}======")
        wallaby_pos = aggregated_data.index.get_loc(date)
        kangaroo_pos = wallaby_pos - 1

        # Get date index 1 year before date, approximately 126 indexes before
        start_index = max(0, wallaby_pos - 126)
        end_index = kangaroo_pos - 3

        active_bull_traps = find_bull_traps(
            potential_bull_traps,
            aggregated_data.index[start_index],
            aggregated_data.index[end_index],
        )

        any_bar_went_above_kangaroo = False
        bearish_bar_went_back_down_to_range = False

        # Condition 1: 20 SMA should slope downwards??
        if (
            kangaroo_pos + 5 < len(aggregated_data)
            and aggregated_data["SMA_20"].iloc[kangaroo_pos]
            < aggregated_data["SMA_20"].iloc[kangaroo_pos + 5]
        ):
            # print("Condition 1 not met: 20 SMA should slope downwards")
            continue
        # else:
        # print("Condition 1 met: 20 SMA slopes upwards")

        # Condition 2: Should be below 20 sma (roughly)
        if (
            aggregated_data["High"].iloc[kangaroo_pos]
            < aggregated_data["SMA_20"].iloc[kangaroo_pos]
        ):
            pass
            # print(
            # f"Condition 2 met: K High is below 50 sma: {aggregated_data['Low'].iloc[kangaroo_pos]} {aggregated_data['SMA_50'].iloc[kangaroo_pos]}"
            # )
        else:
            # print(
            # f"Condition 2 not met: K High should be below 50 sma {aggregated_data['Low'].iloc[kangaroo_pos]} {aggregated_data['SMA_50'].iloc[kangaroo_pos]}"
            # )
            continue

        # Check the next 4 trading dates from wallaby date
        for i in range(1, 5):
            # print(f"Checking {i} days after wallaby date")
            target_pos = wallaby_pos + i
            if target_pos >= len(aggregated_data):
                break

            curr_data = aggregated_data.iloc[target_pos]
            curr_date = aggregated_data.index[target_pos]

            # if low is lower than kangaroo, exit
            if (
                not any_bar_went_above_kangaroo
                and curr_data["Low"] > aggregated_data.iloc[kangaroo_pos]["Low"]
            ):
                # print("Exiting because low is lower than kangaroo")
                break

            # Condition 2: High above the high of the kangaroo wallaby,
            if (
                not any_bar_went_above_kangaroo
                and curr_data["High"] > aggregated_data.iloc[kangaroo_pos]["High"]
            ):
                any_bar_went_above_kangaroo = True
                # print("Condition 3 met: broke above kangaroo highs")

            # Condition 3: must have one of 3 bearish bars (after going out of K range), close between low and high of kangaroo wallaby
            if (
                any_bar_went_above_kangaroo
                and not bearish_bar_went_back_down_to_range
                and aggregated_data.iloc[kangaroo_pos]["Low"]
                <= curr_data["Close"]
                <= aggregated_data.iloc[kangaroo_pos]["High"]
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
                    # print("Condition 4 met: bullish bar close between low and high ")
                    break

        if not any_bar_went_above_kangaroo or not bearish_bar_went_back_down_to_range:
            continue

        # Condition 4: active bear trap must be taken between K-3 and K+5
        # OR if K-K+5 touches 20sma, 50 sma or 200 sma from below
        for i in range(0, 6):
            curr_pos = end_index + i
            if curr_pos >= len(aggregated_data):
                break
            curr_data = aggregated_data.iloc[curr_pos]
            # print(f"Trying to find bear trap or touching of sma for {curr_data.name}")
            if any(
                trap[1] > curr_data["Low"] and trap[1] < curr_data["High"]
                for trap in active_bull_traps
            ):
                pass
                # print(f"Condition 5a met: bear trap met!, {active_bull_traps}")

            # else if touches sma20, sma50 or sma200
            elif (
                i > 0  # only valid if K onwards touches sma (Try between low and close)
                and (
                    curr_data["Low"]
                    <= aggregated_data["SMA_20"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= aggregated_data["SMA_50"].iloc[curr_pos]
                    <= curr_data["High"]
                    or curr_data["Low"]
                    <= aggregated_data["SMA_200"].iloc[curr_pos]
                    <= curr_data["High"]
                )
            ):
                pass
                # print(
                #     f"Condition 5b met: touches SMA 20, 50 or 200: {curr_data['Low']}, {curr_data['High']}"
                # )
                # print(f"SMAs are {aggregated_data["SMA_20"].iloc[curr_pos]}, {aggregated_data["SMA_50"].iloc[curr_pos]}, {aggregated_data["SMA_200"].iloc[curr_pos]}")
            else:
                continue

            bear_appear_dates.append(curr_date)

            # print(
            #     "✅ Wallaby date: "
            #     + str(date)
            #     + "; Bear appear date: "
            #     + str(curr_date)
            # )
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


def get_rsi_overbought_dates(data, threshold=70):
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))
    if data["RSI"].empty:
        return False
    overbought = data["RSI"] > threshold
    overbought_dates = overbought[overbought].index

    return overbought_dates


def get_rsi_oversold_dates(data, threshold=30):
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    oversold = data["RSI"] < threshold
    oversold_dates = oversold[oversold].index
    return oversold_dates


def get_macd_bullish_dates(data, short_window=12, long_window=26, signal_window=9):
    data["Short_EMA"] = data["Close"].ewm(span=short_window, adjust=False).mean()
    data["Long_EMA"] = data["Close"].ewm(span=long_window, adjust=False).mean()
    data["MACD"] = data["Short_EMA"] - data["Long_EMA"]
    data["Signal_Line"] = data["MACD"].ewm(span=signal_window, adjust=False).mean()

    bullish = (data["MACD"] > data["Signal_Line"]) & (
        data["MACD"].shift(1) <= data["Signal_Line"].shift(1)
    )
    bullish_dates = bullish[bullish].index
    return bullish_dates


def get_macd_bearish_dates(data, short_window=12, long_window=26, signal_window=9):
    data["Short_EMA"] = data["Close"].ewm(span=short_window, adjust=False).mean()
    data["Long_EMA"] = data["Close"].ewm(span=long_window, adjust=False).mean()
    data["MACD"] = data["Short_EMA"] - data["Long_EMA"]
    data["Signal_Line"] = data["MACD"].ewm(span=signal_window, adjust=False).mean()

    bearish = (data["MACD"] < data["Signal_Line"]) & (
        data["MACD"].shift(1) >= data["Signal_Line"].shift(1)
    )
    bearish_dates = bearish[bearish].index
    return bearish_dates


def get_bollinger_band_squeeze_dates(data, window=20, num_std_dev=2):
    data["Middle_Band"] = data["Close"].rolling(window=window).mean()
    data["Upper_Band"] = (
        data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
    )
    data["Lower_Band"] = (
        data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
    )

    squeeze = (data["Upper_Band"] - data["Lower_Band"]) / data["Middle_Band"] <= 0.05
    squeeze_dates = squeeze[squeeze].index
    return squeeze_dates


def get_bollinger_band_expansion_dates(data, window=20, num_std_dev=2):
    data["Middle_Band"] = data["Close"].rolling(window=window).mean()
    data["Upper_Band"] = (
        data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
    )
    data["Lower_Band"] = (
        data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
    )

    expansion = (data["Upper_Band"] - data["Lower_Band"]) / data["Middle_Band"] >= 0.1
    expansion_dates = expansion[expansion].index
    return expansion_dates


def get_bollinger_band_breakout_dates(data, window=20, num_std_dev=2):
    data["Middle_Band"] = data["Close"].rolling(window=window).mean()
    data["Upper_Band"] = (
        data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
    )
    data["Lower_Band"] = (
        data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
    )

    breakout = data["Close"] > data["Upper_Band"]
    breakout_dates = breakout[breakout].index
    return breakout_dates


def get_bollinger_band_pullback_dates(data, window=20, num_std_dev=2):
    data["Middle_Band"] = data["Close"].rolling(window=window).mean()
    data["Upper_Band"] = (
        data["Middle_Band"] + num_std_dev * data["Close"].rolling(window=window).std()
    )
    data["Lower_Band"] = (
        data["Middle_Band"] - num_std_dev * data["Close"].rolling(window=window).std()
    )

    pullback = data["Close"] < data["Lower_Band"]
    pullback_dates = pullback[pullback].index
    return pullback_dates


def get_volume_spike_dates(data, window=20, num_std_dev=2):
    data["Volume_MA"] = data["Volume"].rolling(window=window).mean()
    data["Volume_MA_std"] = data["Volume"].rolling(window=window).std()

    spike = data["Volume"] > data["Volume_MA"] + num_std_dev * data["Volume_MA_std"]
    spike_dates = spike[spike].index
    return spike_dates
