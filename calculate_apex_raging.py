from datetime import datetime
import pytz
import utils.ticker_getter as tg
import utils.supabase as db
import utils.indicators as ie


def calculate_and_save_indicator_results():
    stock_list = tg.get_all_tickers()

    # Fetch cached data from Supabase
    cached_data = {
        "apex_bull_raging": db.fetch_cached_data_from_supabase("apex_bull_raging"),
        "apex_bear_raging": db.fetch_cached_data_from_supabase("apex_bear_raging")
    }

    # Filter tickers based on cache and current day
    def filter_tickers(cache):
        sgt = pytz.timezone("Asia/Singapore")
        today_sgt = datetime.now(sgt).replace(hour=5, minute=0, second=0, microsecond=0)
        return [
            ticker["ticker"]
            for ticker in cache
            if datetime.fromisoformat(ticker["created_at"].split(".")[0] + "+00:00").astimezone(sgt) > today_sgt
        ]

    # Tickers to screen by strategy
    tickers_to_screen = {
        strategy: list(set(stock_list) - set(filter_tickers(cache)))
        for strategy, cache in cached_data.items()
    }

    # Track the number of tickers to screen and already screened
    already_screened = {strategy: len(filter_tickers(cache)) for strategy, cache in cached_data.items()}
    to_screen_count = {strategy: len(tickers) for strategy, tickers in tickers_to_screen.items()}
    total_to_screen = sum(to_screen_count.values())

    print(f"Total number of tickers to screen: {total_to_screen}")
    for strategy, count in to_screen_count.items():
        print(f"Number of tickers to screen for {strategy}: {count}")
    for strategy, count in already_screened.items():
        print(f"Number of tickers already screened for {strategy}: {count}")

    # Track inserted records and batches
    batched_data = {strategy: [] for strategy in tickers_to_screen}
    total_inserted = {strategy: 0 for strategy in tickers_to_screen}
    
    # Initialize progress counters
    progress_counter = {strategy: 0 for strategy in tickers_to_screen}
    total_processed = 0

    def batch_upsert(strategy, batch):
        if batch:
            db.upsert_data_to_supabase(strategy, batch)
            total_inserted[strategy] += len(batch)
            print(f"Upserted {len(batch)} records to {strategy}")
            batch.clear()

    # Fetch data and analyze tickers
    total_tickers = set(sum(tickers_to_screen.values(), []))
    total_tickers_count = len(total_tickers)

    for idx, ticker in enumerate(total_tickers, start=1):
        try:
            ticker_data = tg.fetch_stock_data(ticker)
            total_processed += 1
            for strategy, (get_dates_func, table_name) in {
                "apex_bull_raging": (ie.get_apex_bull_raging_dates, "apex_bull_raging"),
                "apex_bear_raging": (ie.get_apex_bear_raging_dates, "apex_bear_raging")
            }.items():
                if ticker in tickers_to_screen[strategy]:
                    dates = [date.strftime('%Y-%m-%d') for date in get_dates_func(ticker_data)]
                    batched_data[table_name].append({
                        "ticker": ticker,
                        "dates": dates,
                        "created_at": "now()"
                    })

                    progress_counter[strategy] += 1
                    

                    # Print progress for the strategy
                    print(f"[{total_processed}/{total_tickers_count}] Processed ticker: {ticker} for {strategy} ({progress_counter[strategy]}/{to_screen_count[strategy]} tickers)")

                    if len(batched_data[table_name]) >= 100:
                        batch_upsert(table_name, batched_data[table_name])

        except Exception as e:
            print(f"❌ Failed to fetch or process data for {ticker}: {e}")

    # Final upsert for remaining batches
    for strategy, batch in batched_data.items():
        batch_upsert(strategy, batch)

    # Print total records inserted for each strategy
    for strategy, count in total_inserted.items():
        print(f"Total inserted for {strategy}: {count}")


calculate_and_save_indicator_results()
