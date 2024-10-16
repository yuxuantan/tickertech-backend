from datetime import datetime, timedelta
import utils.telegram_controller as tc
import utils.supabase as db
import utils.ticker_getter as tg

chat_ids = [
    27392018,  # me
    432502167 # rainbow
]

def alert(indicator_name):
    # Fetch cached data for the given indicator
    bull_raging_cache = db.fetch_cached_data_from_supabase(indicator_name)

    # Filter out data with 'analysis' column's last JSON key older than 5 days

    # Get the date 3 weekdays ago
    # Calculate the date 3 weekdays ago
    three_weekdays_ago = datetime.now()
    weekdays_count = 0
    while weekdays_count < 3:
        three_weekdays_ago -= timedelta(days=1)
        if three_weekdays_ago.weekday() < 5:  # Monday to Friday are 0-4
            weekdays_count += 1

    results_output = "__ *ticker | entry date | next earning report * __\n" 

    # Filter and format the data
    filtered_tickers = []
    for row in bull_raging_cache:
        # get last date in ticker["dates"]
        if not row['dates']:
            continue
        entry_date = datetime.strptime(row['dates'][-1], '%Y-%m-%d')
        # Calculate the entry date as 2 weekdays away from signal confirmed bar date because we are using 2D chart. 

        days_added = 0
        while days_added < 2:
            entry_date += timedelta(days=1)
            if entry_date.weekday() < 5:  # Monday to Friday are 0-4
                days_added += 1
            
        if entry_date > three_weekdays_ago:
            filtered_tickers.append(row)
            ticker_symbol = row["ticker"]
            data = tg.fetch_stock_data(ticker_symbol)
            entry_close_price = data.loc[entry_date].get('Close', '?')
            volume = data.loc[entry_date].get('Volume', '?')

            # Format entry close price and volume
            if entry_close_price != '?':
                entry_close_price = round(float(entry_close_price), 2)

            if volume != '?':
                volume = round(float(volume))

            if entry_close_price == '?' or volume == '?' or entry_close_price < 20 or volume < 1000000:
                continue

            # Add row to the table
            results_output += f"✅ *{ticker_symbol}* | {str(entry_date).split(' ')[0]} | {str(tg.fetch_next_earnings_date(ticker_symbol)).split(' ')[0]}\n"

    # Check if there are results
    if not filtered_tickers:
        return f"*{indicator_name} screening completed*\n\n⚙️ Close price > 20, Volume > 100k\n\nNo stocks found matching the criteria"

    # Use PrettyTable's string representation to create the message

    output_msg = f"""*{indicator_name} screening completed*\n\n⚙️ Close price > 20, Volume > 100k \n\n *Screen results:*\n{results_output}"""
    
    return output_msg


if __name__ == "__main__":
    # Send messages for each indicator
    tc.send_message(chat_ids, message=alert('apex_bull_raging'))
    tc.send_message(chat_ids, message=alert('apex_bull_appear'))
    tc.send_message(chat_ids, message=alert('apex_bear_raging'))
    tc.send_message(chat_ids, message=alert('apex_bear_appear'))
