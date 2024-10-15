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
    for ticker in bull_raging_cache:
        last_key = next(reversed(ticker["analysis"]), None)
        if last_key:
            last_key_date = datetime.strptime(last_key, '%Y-%m-%d')
            # Calculate the entry date as 2 weekdays away from signal confirmed bar date because we are using 2D chart. 
            entry_date = last_key_date
            days_added = 0
            while days_added < 2:
                entry_date += timedelta(days=1)
                if entry_date.weekday() < 5:  # Monday to Friday are 0-4
                    days_added += 1
            
            if entry_date > three_weekdays_ago:
                filtered_tickers.append(ticker)
                ticker_symbol = ticker.get('ticker', '?')
                # entry_date = last_key if last_key else '?'
                entry_close_price = ticker['analysis'][last_key].get('close', '?')
                volume = ticker['analysis'][last_key].get('volume', '?')

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
