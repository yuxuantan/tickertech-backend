import pandas as pd

def get_analysis_results(dates, data):
    analysis_results = {}
    if dates is None:
        return analysis_results
    
    for date in dates:
        date_index = data.index.get_loc(date)
        if date_index != -1:
            date_str = date.strftime('%Y-%m-%d')
            analysis_results[date_str] = {}
            analysis_results[date_str]['change1TD'] = ((data.iloc[date_index + 1]['Close'] - data.iloc[date_index]['Close']) / data.iloc[date_index]['Close']) * 100 if date_index + 1 < len(data) else None
            analysis_results[date_str]['change5TD'] = ((data.iloc[date_index + 5]['Close'] - data.iloc[date_index]['Close']) / data.iloc[date_index]['Close']) * 100 if date_index + 5 < len(data) else None
            analysis_results[date_str]['change20TD'] = ((data.iloc[date_index + 20]['Close'] - data.iloc[date_index]['Close']) / data.iloc[date_index]['Close']) * 100 if date_index + 20 < len(data) else None
            analysis_results[date_str]['volume'] = data.iloc[date_index]['Volume']
            analysis_results[date_str]['close'] = data.iloc[date_index]['Close']
    
    return analysis_results

def get_2day_aggregated_data(data):
    # Ensure the Date column is the index and is of datetime type
    data.index = pd.to_datetime(data.index)
    
    # Split the data into separate dataframes by year
    yearly_data = {year: df for year, df in data.groupby(data.index.year)}
    
    aggregated_data_list = []
    
    # Process each year's dataframe independently
    for year, df in yearly_data.items():
        # Group data into 2-day periods within each year
        grouped = (
            df[["High", "Low", "Open", "Close"]]
            .rolling(window=2, min_periods=1)
            .agg(
                {
                    "High": "max",
                    "Low": "min",
                    "Open": lambda x: x.iloc[0],
                    "Close": lambda x: x.iloc[-1],
                }
            )
        )
        # Shift to make the aggregation align to the end of each 2-day period
        aggregated = grouped.shift(-1).iloc[::2]
        
        # Append the result for the current year
        aggregated_data_list.append(aggregated)

    # Combine all the yearly dataframes into one dataframe
    if aggregated_data_list:
        aggregated_data = pd.concat(aggregated_data_list)
    else:
        aggregated_data = pd.DataFrame()
    
    return aggregated_data


# pass data before kangaroo -1 inside. it cannot take the money of past bear traps
def get_low_inflexion_points(data):
    # get all bear trap dates and values = u or v shape, where T-1 low > T low < T+1 low. Identify T
    all_low_inflexion_points = []
    for i in range(2, len(data) - 2):
        if (
            data.iloc[i - 1]["Low"] > data.iloc[i]["Low"] < data.iloc[i + 1]["Low"]
        ) and (
            data.iloc[i - 2]["Low"] > data.iloc[i]["Low"] < data.iloc[i + 2]["Low"]
        ):
            all_low_inflexion_points.append((data.index[i], data.iloc[i]["Low"]))
    return all_low_inflexion_points


def get_high_inflexion_points(data):
    all_high_inflexion_points = []
    for i in range(2, len(data) - 2):
        if (
            (data.iloc[i - 1]["High"] < data.iloc[i]["High"] > data.iloc[i + 1]["High"])
            and 
            (data.iloc[i - 2]["High"] < data.iloc[i]["High"] > data.iloc[i + 2]["High"])
        ):
            all_high_inflexion_points.append((data.index[i], data.iloc[i]["High"]))
    return all_high_inflexion_points


def find_bear_traps(potential_traps, from_date, to_date):
    bear_traps = []
    # Filter bear traps up to the given date
    potential_bear_traps_in_date_range = [(date, low) for date, low in potential_traps if from_date <= date <= to_date]

    # For each bear trap, check if it has been invalidated by a lower low
    for potential_bear_trap_date, potential_bear_trap_low in potential_bear_traps_in_date_range:
        # Find if a lower low trap occurred after the bear trap but before the given date
        post_bear_trap_lows = pd.Series([low for trap_date, low in potential_bear_traps_in_date_range if potential_bear_trap_date <= trap_date <= to_date])
        if (post_bear_trap_lows < potential_bear_trap_low).any():
            # Bear trap is invalidated
            continue
        bear_traps.append((potential_bear_trap_date, potential_bear_trap_low))

        # Bear trap is valid
    return bear_traps

def find_bull_traps(potential_traps, from_date, to_date):
    bull_traps = []
    # Filter bull traps up to the given date
    potential_bull_traps_in_date_range = [(date, high) for date, high in potential_traps if from_date <= date <= to_date]

    # For each bull trap, check if it has been invalidated by a lower low
    for potential_bull_trap_date, potential_bull_trap_high in potential_bull_traps_in_date_range:
        # Find if a higher high trap occurred after the bull trap but before the given date
        post_bull_trap_highs = pd.Series([high for trap_date, high in potential_bull_traps_in_date_range if potential_bull_trap_date <= trap_date <= to_date])
        if (post_bull_trap_highs > potential_bull_trap_high).any():
            # Bull trap is invalidated
            continue
        bull_traps.append((potential_bull_trap_date, potential_bull_trap_high))

        # Bull trap is valid
    return bull_traps


# def find_lowest_bear_trap_within_price_range(potential_bear_traps, high_point_date, low_price, high_price):
#     active_traps = []
#     for trap in potential_bear_traps:
#         trap_date, trap_low = trap
#         if trap_date >= high_point_date or not (low_price < trap_low < high_price):
#             continue
        
#         # Invalidate older traps with higher lows
#         active_traps = [t for t in active_traps if t[1] < trap_low]
#         active_traps.append(trap)
    
#     return min(active_traps, key=lambda x: x[1]) if active_traps else None
    



def find_lowest_bear_trap_within_price_range(potential_traps, up_to_date, low_price, high_price):
    # from date is 1 year before up_to_date
    from_date = up_to_date - pd.Timedelta(days=365)
    # Filter bear traps up to the given date
    bear_traps_up_to_date = find_bear_traps(potential_traps, from_date=from_date, to_date=up_to_date)
    
    for date, trap_price in bear_traps_up_to_date:
        # Bear trap is valid
        if low_price <= trap_price <= high_price:
            return(date, trap_price)
    

def find_highest_bull_trap_within_price_range(potential_traps, up_to_date, low_price, high_price):
    from_date = up_to_date - pd.Timedelta(days=365)
    # Filter bull traps up to the given date
    bull_traps_up_to_date = find_bull_traps(potential_traps, from_date=from_date, to_date=up_to_date)
    
    # ordered from highest to lowest, so the first one will be the highest one and we can return it
    for date, trap_price in bull_traps_up_to_date:
        # Bull trap is valid
        if low_price <= trap_price <= high_price:
            return(date, trap_price)
