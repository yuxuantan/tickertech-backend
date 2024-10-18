from datetime import datetime, timedelta, timezone
import utils.telegram_controller as tc
import utils.supabase as db
import utils.ticker_getter as tg
import sys

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

    results_output = "__ *ticker | entry date | next earning report* __\n" 

    # Filter and format the data
    filtered_tickers = []
    for row in bull_raging_cache:
        # get last date in ticker["dates"]
        if not row['dates']:
            continue
        signal_date = datetime.strptime(row['dates'][-1], '%Y-%m-%d')
        # Calculate the entry date as 2 weekdays away from signal confirmed bar date because we are using 2D chart. 
        entry_date = signal_date
        days_added = 0
        while days_added < 2:
            entry_date += timedelta(days=1)
            if entry_date.weekday() < 5:  # Monday to Friday are 0-4
                days_added += 1
            

        if entry_date > three_weekdays_ago:
            filtered_tickers.append(row)
            ticker_symbol = row["ticker"]
            data = tg.fetch_stock_data(ticker_symbol)

            latest_close = data.iloc[-1].get('Close', '?')
            latest_volume = data.iloc[-1].get('Volume', '?')

            # Format entry close price and volume
            if latest_close != '?':
                latest_close = round(float(latest_close), 2)

            if latest_volume != '?':
                latest_volume = round(float(latest_volume))

            if latest_close == '?' or latest_volume == '?' or latest_close < 20 or latest_volume < 1000000:
                continue

            next_earnings_date = tg.fetch_next_earnings_date(ticker_symbol)
            if next_earnings_date is None or next_earnings_date > (datetime.now(timezone.utc) + timedelta(days=14)):
                continue


            # Add row to the table
            results_output += f"✅ *{ticker_symbol}* | {str(entry_date).split(' ')[0]} | {str(tg.fetch_next_earnings_date(ticker_symbol)).split(' ')[0]}\n"

    msg = f"""*{indicator_name} screening completed on {datetime.now().date()}*\n
*Filter ⚙️:*\n ‣ Entry date up to 2 weekdays ago \n ‣ Latest close price > 20 \n ‣ Latest volume > 100k \n ‣ Earnings Report in next 14 days\n\n"""
    # Check if there are results
    if not filtered_tickers:
        msg += "No stocks found matching the criteria."
    else:
        msg += f"*Screen results:*\n{results_output}"


    
    return msg


if __name__ == "__main__":
    # Send messages for each indicator
    for input_arg in sys.argv[1:]:
        tc.send_message(chat_ids, message=alert(input_arg))
