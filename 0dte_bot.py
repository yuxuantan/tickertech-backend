"""
- if 85% win rate (conservatively), expectancy is 0.85*0.75 - 0.15*3 = 0.15. this means that for every $1 risked, you get $0.15 back.
 -- target profit is 375 USD (500 SGD) per day (1%)
 -- max loss is 750 USD (1000 SGD) per day (2%)

 Strategy:
- (ONLY If no current positions), Look for opportunities to sell 0DTE options beginning at 230am SGT at 0.5% (~30) price away. latest enter at 4am SGT
    -- Check 30 min, 5 min and 1 min chart for apex patterns (in this order). Go in the direction of first signal found. If none, go with the trend (if up since open, sell put and vice versa)
    -- calculate strike price, which is 0.5 % from current price
    -- calculate spread (only use <20). start trying using 5 -> 10 -> 15 -> 20
        -- min premium obtained per contract (short - long) is 0.15
        -- max_contracts_given_buying_power = buying power / (spread * 100) * 0.9
        -- max_contracts_given_target_profit = target profit / (contract price * number of contracts * 100)
        -- number of contracts = min(max_contracts_given_buying_power, max_contracts_given_target_profit)
    -- initial SL at 200% (or triple the price).

- before 4am
    - if hit 50% of premium obtained, change SL to 50% of premium obtained
- after 4am
    - if hit 75% of premium obtained, change SL to 75% of premium obtained


"""
from tigeropen.common.util.contract_utils import option_contract
from tigeropen.common.util.order_utils import (market_order,  # market order
                                               limit_order,  # limit order
                                               stop_order,  # stop order
                                               stop_limit_order,  # stop limit order
                                               trail_order,  # trailing stop order
                                               order_leg)  # additional order


import pytz
from datetime import datetime
import yfinance as yf
from utils.tiger_controller import TigerController
from dotenv import load_dotenv
import utils.indicators as indicators

load_dotenv()
# get current time and check if it is before or after 4am SGT, which is 3pm EST
current_time = datetime.now().astimezone(pytz.timezone("US/Eastern"))
current_hour = current_time.hour
current_minute = current_time.minute

print(current_hour)

if (
    current_hour == 13 or current_hour == 14 or current_hour == 5
):  # correct one # if time between 2 and 3 PM EST, potentially enter
    # if current_hour == 9: # temp one
    print("between 3 and 4am SGT")
    # get current options that are open using tigeropen
    tc = TigerController()
    pos = tc.get_open_positions_options()

    contracts = []
    for p in pos:
        if "SPXW" in str(p.contract):
            print(p)
            contracts.append(p)

    # if open - adjust SL if hit 50% of premium
    if len(contracts) > 0:
        print("open positions")
    elif len(contracts) == 0:
        print("no open positions")

        timeframes = ["30m", "15m", "5m", "1m"]
        bull_or_bear_rating = 0  # the more bullish, the higher the number. the more bearish, the lower the number
        for tf in timeframes:
            print("checking " + tf + " chart for signal")
            data = yf.download("^GSPC", period="1d", interval=tf)

            # multiplier for 30m is 2, 15m is 1.5, 5m is 1, 1m is 1
            if tf == "30m":
                multiplier = 4
                look_back_num_bars = 1
            elif tf == "15m":
                multiplier = 3
                look_back_num_bars = 2
            elif tf == "5m":
                multiplier = 2
                look_back_num_bars = 6
            elif tf == "1m":
                multiplier = 1
                look_back_num_bars = 10

            # get bull appear
            bull_appear_bars = indicators.get_apex_bull_appear_dates(
                data, custom_aggregate_2days=False, only_fetch_last=True
            )
            # if the last signal is one of the last 3 bars, then it is a confirmed signal
            if (
                len(bull_appear_bars) > 0
                and bull_appear_bars[-1] >= data.index[-look_back_num_bars]
            ):
                print(
                    "bull appear detected for "
                    + tf
                    + " at "
                    + str(bull_appear_bars[-1])
                )
                bull_or_bear_rating += 1 * multiplier

            # get bull raging

            bull_raging_bars = indicators.get_apex_bull_raging_dates(
                data,
                custom_aggregate_2days=False,
                flush_treshold=0.5,
                ratio_of_flush_bars_to_consider_raging=0.4,
            )
            if (
                len(bull_raging_bars) > 0
                and bull_raging_bars[-1] >= data.index[-look_back_num_bars]
            ):
                print(
                    "bull raging detected for "
                    + tf
                    + " at "
                    + str(bull_raging_bars[-1])
                )
                bull_or_bear_rating += 1 * multiplier

            # get bear appear
            bear_appear_bars = indicators.get_apex_bear_appear_dates(
                data, custom_aggregate_2days=False, only_fetch_last=True
            )
            if (
                len(bear_appear_bars) > 0
                and bear_appear_bars[-1] >= data.index[-look_back_num_bars]
            ):
                print(
                    "bear appear detected for "
                    + tf
                    + " at "
                    + str(bear_appear_bars[-1])
                )
                bull_or_bear_rating -= 1 * multiplier

            # get bear raging
            bear_raging_bars = indicators.get_apex_bear_raging_dates(
                data,
                custom_aggregate_2days=False,
                flush_treshold=0.5,
                ratio_of_flush_bars_to_consider_raging=0.4,
            )
            if (
                len(bear_raging_bars) > 0
                and bear_raging_bars[-1] >= data.index[-look_back_num_bars]
            ):
                print(
                    "bear raging detected for "
                    + tf
                    + " at "
                    + str(bear_raging_bars[-1])
                )
                bull_or_bear_rating -= 1 * multiplier

            # get uptrend
            uptrend_bars = indicators.get_apex_uptrend_dates(
                data, custom_aggregate_2days=False
            )
            if (
                len(uptrend_bars) > 0
                and uptrend_bars[-1] >= data.index[-look_back_num_bars]
            ):
                print("uptrend detected for " + tf + " at " + str(uptrend_bars[-1]))
                bull_or_bear_rating += 1 * multiplier

            # get downtrend
            downtrend_bars = indicators.get_apex_downtrend_dates(
                data, custom_aggregate_2days=False
            )
            if (
                len(downtrend_bars) > 0
                and downtrend_bars[-1] >= data.index[-look_back_num_bars]
            ):
                print("downtrend detected for " + tf + " at " + str(downtrend_bars[-1]))
                bull_or_bear_rating -= 1 * multiplier

        print("bull or bear rating: " + str(bull_or_bear_rating))
        # get current price
        current_price = data["Close"].iloc[-1]
        # get open price
        open_price = data["Open"].iloc[-1]

        if bull_or_bear_rating > 0:
            print("bullish")
            option_type = "put"
        elif bull_or_bear_rating < 0:
            print("bearish")
            option_type = "call"

        # if bull_bear rating is 0, go with the trend.
        elif bull_or_bear_rating == 0:
            print("going with the trend")
            data = yf.download("^GSPC", period="1d", interval="1d")
            

            if current_price > open_price:
                option_type = "put"
            else:
                option_type = "call"
            print("current price: " + str(current_price))
            print("open price: " + str(open_price))
        

        # calculate strike price
        percent_from_strike = 0.005
        strike_price = (
            current_price * (1 + percent_from_strike)
            if option_type == "call"
            else current_price * (1 - percent_from_strike)
        )
        short_strike_price = round(strike_price / 5) * 5

        print("option type: " + option_type)
        print("short strike price: " + str(short_strike_price))

        spreads_to_try = [5, 10, 15, 20]
        long_strike_prices_to_try = [short_strike_price + spread if option_type == "call" else short_strike_price - spread for spread in spreads_to_try]

        print("long strike prices to try: " + str(long_strike_prices_to_try))
        
        expiry = current_time.strftime('%y%m%d')
        option_type = 'P' if option_type == 'put' else 'C'
        identifier = f'SPXW {expiry}{option_type}{short_strike_price}'
        # get the current bid and ask price for short leg. use this to find the middle price
        quote = tc.quote_client.get_option_briefs([identifier])
        print(quote)

        # for each long leg
            # get the current bid and ask price for long leg
            # short leg price - long leg price >= 0.15 # if satisfy this condition, execute both legs for vertical spread then exit this loop

        
            
      

# if time between 3 PM - 4pm EST, adjust SL if hit 75% of premium
elif current_hour == 15:
    print("between 4 and 5am SGT. Last hour!")
else:
    # stop the script because it should not be running
    print("not between 3 and 5am SGT. script shouldnt be running")


def make_order(option_type, strike_price, limit_price, action='SELL'):
      # enter the trade using tiger

        # Example for a call vertical spread on SPXW
        
        quantity = 1


        contract = option_contract(identifier=f'SPXW {expiry}{option_type}{strike_price}')


        # Create order objects
        order = limit_order(
            account=tc.config.account,
            contract=contract,
            action=action,
            quantity=quantity,
            limit_price=limit_price,
            # time_in_force='DAY'  # or 'GTC' for Good-Till-Canceled
        )

        # Place the buy order
        order_id = tc.trade_client.place_order(order)
        print(f'Order placed with ID: {order_id}')