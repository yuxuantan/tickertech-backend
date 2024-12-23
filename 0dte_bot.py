# TODO: use bid and ask and limit order when closing positions to prevent slippage

from tigeropen.common.consts import ComboType
from tigeropen.common.util.order_utils import (
    combo_order,
    contract_leg,
    stop_order,
    limit_order,
    market_order,
)


import pytz
from datetime import datetime
import yfinance as yf
from utils.tiger_controller import TigerController
from dotenv import load_dotenv
import utils.indicators as indicators
import time
import utils.telegram_controller as TelegramController

load_dotenv()


def get_current_time():
    return datetime.now().astimezone(pytz.timezone("US/Eastern"))


def get_open_positions(tc):
    pos = tc.get_open_positions_options()
    return [p for p in pos if "SPXW" in str(p.contract)]


def get_bull_or_bear_rating(timeframes):
    bull_or_bear_rating = 0
    for tf in timeframes:
        data = yf.download("^GSPC", period="5d", interval=tf)
        # remove the last bar as it is not complete
        data = data.loc[data.index[:-1]]

        multiplier, look_back_num_bars = get_multiplier_and_lookback(tf)
        bull_or_bear_rating += calculate_rating(
            data, tf, multiplier, look_back_num_bars
        )

    return bull_or_bear_rating


def get_multiplier_and_lookback(tf):
    if tf == "30m":
        return 4, 1
    elif tf == "15m":
        return 3, 2
    elif tf == "5m":
        return 2, 6


def calculate_rating(data, tf, multiplier, look_back_num_bars):
    rating = 0
    print(f"checking formation for tf {tf}")
    rating += check_for_formation(
        indicators.get_apex_bull_appear_dates, data, look_back_num_bars, multiplier
    )
    rating += check_for_formation(
        indicators.get_apex_bull_raging_dates, data, look_back_num_bars, multiplier
    )
    rating -= check_for_formation(
        indicators.get_apex_bear_appear_dates, data, look_back_num_bars, multiplier
    )
    rating -= check_for_formation(
        indicators.get_apex_bear_raging_dates, data, look_back_num_bars, multiplier
    )
    rating += check_for_formation(
        indicators.get_apex_uptrend_dates, data, look_back_num_bars, multiplier
    )
    rating -= check_for_formation(
        indicators.get_apex_downtrend_dates, data, look_back_num_bars, multiplier
    )
    return rating


def check_for_formation(func, data, look_back_num_bars, multiplier):
    bars = func(data, custom_aggregate_2days=False, only_fetch_last=True)
    # if formation detected in the last lookbacknumbars, print it out
    if len(bars) > 0 and bars[-1] >= data.index[-look_back_num_bars]:
        print(f"formation detected for: {func.__name__} at {bars[-1]}")
    return (
        multiplier
        if len(bars) > 0 and bars[-1] >= data.index[-look_back_num_bars]
        else 0
    )


def get_option_type(bull_or_bear_rating, current_price, open_price, current_time):
    if bull_or_bear_rating > 0:
        return "PUT"
    elif bull_or_bear_rating < 0:
        return "CALL"
    else:
        if current_time.hour >= 13:
            # reversal more likely
            return "PUT" if current_price < open_price else "CALL"
        else:
            # bull bias
            return "PUT"


def calculate_strike_price(current_price, current_hour, option_type):
    if current_hour == 10:
        percent_from_strike = 0.005
    elif current_hour == 15:
        percent_from_strike = 0.002
    else:
        return None

    strike_price = (
        current_price * (1 + percent_from_strike)
        if option_type == "CALL"
        else current_price * (1 - percent_from_strike)
    )
    return round(strike_price / 5) * 5


def get_leg_quote(tc, expiry, strike_price, option_type):
    fmt_expiry = expiry[2:].replace("-", "")
    fmt_option_type = "C" if option_type == "CALL" else "P"
    fmt_strike = (str(strike_price) + "000").zfill(8)
    identifier = "SPXW " + fmt_expiry + fmt_option_type + fmt_strike
    print(identifier)
    leg_quote = tc.quote_client.get_option_briefs([identifier])
    if leg_quote.empty:
        print(f"no data for strike price: {strike_price}, option type: {option_type}")
        exit()
    return leg_quote


def calculate_target_premium(short_leg_mid_price, long_leg_mid_price):
    target_premium = round(short_leg_mid_price - long_leg_mid_price, 2)
    return round(target_premium * 20) / 20


def place_order(
    tc,
    expiry,
    short_strike_price,
    long_strike_price,
    option_type,
    target_qty,
    target_premium,
):
    order_leg_short = contract_leg(
        symbol="SPXW",
        sec_type="OPT",
        expiry=expiry,
        strike=short_strike_price,
        put_call=option_type,
        action="SELL",
        ratio=1,
    )
    order_leg_long = contract_leg(
        symbol="SPXW",
        sec_type="OPT",
        expiry=expiry,
        strike=long_strike_price,
        put_call=option_type,
        action="BUY",
        ratio=1,
    )
    order = combo_order(
        account=tc.config.account,
        contract_legs=[order_leg_short, order_leg_long],
        combo_type=ComboType.VERTICAL,
        action="SELL",
        quantity=target_qty,
        order_type="LMT",
        limit_price=-float(target_premium),
    )
    return tc.trade_client.place_order(order)


def main(is_real=False):
    current_time = get_current_time()
    TelegramController.send_message(
        message=f"0dte bot started running at {current_time}"
    )

    expiry = current_time.strftime("%Y-%m-%d")
    tc = TigerController()

    while True:
        spx_positions = get_open_positions(tc)
        spx_short_positions = [p for p in spx_positions if p.quantity < 0]

        if (
            not spx_short_positions
            and current_time.hour == 10
            or current_time.hour == 15
        ) or not is_real:
            print(
                "NO open positions. Look to enter new trades at 10-11am and 3-4pm EST"
            )
            timeframes = ["30m", "15m", "5m"]
            bull_or_bear_rating = get_bull_or_bear_rating(timeframes)
            daily_data = yf.download("^GSPC", period="1d", interval="1d")
            current_price = daily_data["Close"].iloc[-1]
            open_price = daily_data["Open"].iloc[-1]

            option_type = get_option_type(
                bull_or_bear_rating, current_price, open_price, current_time
            )

            print(f"bull_or_bear_rating: {bull_or_bear_rating}")

            short_strike_price = calculate_strike_price(
                current_price, current_time.hour, option_type
            )
            if short_strike_price is None:
                print("not time to trade yet. Strike price is None. Sleeping for 1 min")
                time.sleep(60)
                continue
            print(
                f"current price: {current_price}, open price: {open_price}, option type: {option_type}"
            )

            short_leg_quote = get_leg_quote(
                tc, expiry, short_strike_price, option_type
            ).copy()

            # if bid_price or ask_price is None, then abort
            if (
                short_leg_quote["bid_price"].values[0] is not None
                and short_leg_quote["ask_price"].values[0] is not None
            ):
                short_leg_mid_price = (
                    short_leg_quote["bid_price"].values[0]
                    + short_leg_quote["ask_price"].values[0]
                ) / 2

                spreads_to_try = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
                long_strike_prices_to_try = [
                    short_strike_price + spread
                    if option_type == "CALL"
                    else short_strike_price - spread
                    for spread in spreads_to_try
                ]

                for long_strike_price in long_strike_prices_to_try:
                    long_leg_quote = get_leg_quote(
                        tc, expiry, long_strike_price, option_type
                    ).copy()

                    # if bid_price or ask_price is None, then abort
                    if (
                        long_leg_quote["bid_price"].values[0] is not None
                        and long_leg_quote["ask_price"].values[0] is not None
                    ):
                        long_leg_mid_price = (
                            long_leg_quote["bid_price"].values[0]
                            + long_leg_quote["ask_price"].values[0]
                        ) / 2

                        target_premium = calculate_target_premium(
                            short_leg_mid_price, long_leg_mid_price
                        )

                        if (long_leg_mid_price > 0.2 and current_time.hour == 10) or (
                            long_leg_mid_price > 0.05 and current_time.hour == 15
                        ):
                            print(f"long leg mid price too high: {long_leg_mid_price}")

                        elif target_premium >= 0.15:
                            print(
                                f"short_strike_price: {short_strike_price}, long_strike_price: {long_strike_price}"
                            )
                            print(f"target premium: {target_premium}")
                            excess_liquidity = (
                                tc.trade_client.get_assets()[0]
                                .segments["S"]
                                .excess_liquidity
                            )
                            max_contracts_given_buying_power = round(
                                excess_liquidity
                                / (abs(short_strike_price - long_strike_price) * 100)
                                * 0.8,
                                0,
                            )
                            max_contracts_given_target_profit = (
                                round(
                                    excess_liquidity * 0.01 / (target_premium * 100), 0
                                )
                                if target_premium > 0
                                else 999999999999
                            )
                            target_qty = min(
                                max_contracts_given_buying_power,
                                max_contracts_given_target_profit,
                            )
                            print(f"target qty: {target_qty}")

                            if is_real:
                                order_id = place_order(
                                    tc,
                                    expiry,
                                    short_strike_price,
                                    long_strike_price,
                                    option_type,
                                    target_qty,
                                    target_premium,
                                )
                                order_res = tc.trade_client.get_order(id=order_id)
                                TelegramController.send_message(
                                    message=f"order placed: {order_res}"
                                )
                            break
                        else:
                            print(f"target premium too low: {target_premium}")

        else:
            print(
                "have open positions already. check if there are existing orders for stop loss and take profit. If not, place them"
            )
            open_orders = tc.get_open_orders_options()
            spxw_open_orders = [
                order for order in open_orders if "SPXW" in str(order.contract)
            ]

            for spx_position in spx_positions:
                matching_open_order = [
                    order
                    for order in spxw_open_orders
                    if (str(order.contract) == str(spx_position.contract))
                ]
                if len(matching_open_order) > 0:
                    matching_open_order = matching_open_order[0]
                else:
                    matching_open_order = None

                if spx_position.quantity < 0:  # short leg
                    premium_collected = spx_position.average_cost
                    pnl = round(
                        (spx_position.average_cost - spx_position.market_price)
                        / spx_position.average_cost
                        * 100,
                        2,
                    )
                    print(f"pnl of {spx_position.contract}: {pnl}%")
                    # stop loss (market order) default protection. send in stop loss order to cut loss, triggered at 4x premium (300% loss) if there is no open orders for this short leg
                    # this will only be triggered at the start (max 1 min) after order is first placed, and be set as the default to prevent catestrophic loss. subsequently when other orders are placed, it wont be triggered again
                    if matching_open_order is None:
                        print(
                            f"no existing order for {spx_position.contract} short leg. need to enter stop loss and take profit orders"
                        )
                        print(f"premium collected = {premium_collected}")

                        stop_price = (
                            round(premium_collected * 5 * 20) / 20
                        )  # stop price is 5x premium collected from the short leg. this is just in case

                        print(f"stop triggered price: {stop_price}")
                        # place stop loss order
                        order = stop_order(
                            account=tc.config.account,
                            contract=spx_position.contract,
                            action="BUY",
                            quantity=abs(spx_position.quantity),
                            aux_price=stop_price,
                        )
                        oid = tc.trade_client.place_order(order)
                        print(f"stop loss (market) order placed with id: {oid}")

                        order_res = tc.trade_client.get_order(id=oid)
                        TelegramController.send_message(
                            message=f"order placed for sl default market order: {order_res}"
                        )
                    else:
                        print(
                            f"existing order exists for {spx_position.contract} short leg. no need to enter stop loss and take profit orders"
                        )

                    # stop loss (market order) manual protection. send in market order to cut loss, triggered if price is 2x premium + if the current price is less than 10 away from the strike in hour 14 or less than 5 away in hour 15
                    if (
                        current_time.hour <= 14  # before 2pm EST
                        and abs(current_price - float(spx_position.contract.strike))
                        / current_price
                        < 0.003 # roughly 18 apart
                    ) or (
                        current_time.hour >= 15  # after 2pm EST
                        and abs(current_price - float(spx_position.contract.strike))
                        / current_price
                        < 0.001 # roughly 6 apart
                    ):
                        # delete any existing orders that are on HOLD (eg stop loss orders)
                        if matching_open_order is not None:
                            matching_open_order_id = matching_open_order.id
                            print(f"deleting existing order: {matching_open_order_id}")
                            cancel_order_success = tc.trade_client.cancel_order(
                                id=matching_open_order_id
                            )
                            print(f"cancel order success: {cancel_order_success}")

                        if pnl < -200:
                            # submit market order
                            order = market_order(
                                account=tc.config.account,
                                contract=spx_position.contract,
                                action="BUY",
                                quantity=abs(spx_position.quantity),
                            )
                            print("submitting market order for stop loss..")
                            oid = tc.trade_client.place_order(order)
                            print(f"stop loss (market) order placed with id: {oid}")

                            order_res = tc.trade_client.get_order(id=oid)
                            TelegramController.send_message(
                                message=f"order placed for sl manual market order: {order_res}"
                            )
                        else:
                            print(f"pnl of {spx_position.contract} not below -200% yet")
                            stop_price = (
                                round(premium_collected * 3 * 20) / 20
                            )  # stop price is 3x premium collected from the short leg.
                            order = stop_order(
                                account=tc.config.account,
                                contract=spx_position.contract,
                                action="BUY",
                                quantity=abs(spx_position.quantity),
                                aux_price=stop_price,
                            )

                    # take profit order - only when pnl is above target tp

                    tp_target_percent = 75
                    if current_time.hour == 15 and current_time.minute >= 30:
                        tp_target_percent = 90

                    if pnl >= tp_target_percent:
                        print("take profit because pnl > 75%")
                        # delete any existing orders that are on HOLD (eg stop loss orders)
                        if matching_open_order is not None:
                            matching_open_order_id = matching_open_order.id
                            print(f"deleting existing order: {matching_open_order_id}")
                            cancel_order_success = tc.trade_client.cancel_order(
                                id=matching_open_order_id
                            )
                            print(f"cancel order success: {cancel_order_success}")
                        # submit limit order
                        limit_price = (
                            round((spx_position.average_cost * 0.25) * 20) / 20
                        )
                        order = limit_order(
                            account=tc.config.account,
                            contract=spx_position.contract,
                            action="BUY",
                            quantity=abs(spx_position.quantity),
                            limit_price=limit_price,
                        )
                        print(f"submitting take profit order for {limit_price}..")
                        oid = tc.trade_client.place_order(order)
                        print(f"take profit order placed with id: {oid}")

                        order_res = tc.trade_client.get_order(id=oid)
                        TelegramController.send_message(
                            message=f"order placed for tp limit order: {order_res}"
                        )

                elif spx_position.quantity > 0:  # long leg
                    # check if corresponding short leg (with same option type and expiry, but negative quantity) is present. if not present, close the long leg for TP/ SL
                    matching_short_leg = [
                        position
                        for position in spx_positions
                        if (
                            (str(spx_position.contract)[:13] in str(position.contract))
                            and position.quantity < 0
                        )
                    ]
                    if len(matching_short_leg) == 0:
                        print(
                            f"no corresponding short leg found for {spx_position.contract}. closing long leg"
                        )
                        # delete any existing orders that are on HOLD (eg stop loss orders)
                        if matching_open_order is not None:
                            matching_open_order_id = matching_open_order.id
                            print(f"deleting existing order: {matching_open_order_id}")
                            cancel_order_success = tc.trade_client.cancel_order(
                                id=matching_open_order_id
                            )
                            print(f"cancel order success: {cancel_order_success}")
                        # submit market order
                        limit_price = (
                            round((spx_position.average_cost * 0.25) * 20) / 20
                        )
                        order = market_order(
                            account=tc.config.account,
                            contract=spx_position.contract,
                            action="SELL",
                            quantity=abs(spx_position.quantity),
                        )
                        print("submitting take market order to close long leg..")
                        oid = tc.trade_client.place_order(order)
                        print(
                            f"take market order placed with id to close long leg: {oid}"
                        )

                        order_res = tc.trade_client.get_order(id=oid)
                        TelegramController.send_message(
                            message=f"market order placed to close long leg: {order_res}"
                        )
                    else:
                        print(
                            f"corresponding short leg found for {spx_position.contract}. no need to close long leg"
                        )
        print("sleeping for 1 mins at end of loop")
        time.sleep(60)

    TelegramController.send_message(
        message=f"0dte bot stopped running at {get_current_time()}"
    )


if __name__ == "__main__":
    main(is_real=False)
