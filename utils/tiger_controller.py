from tigeropen.trade.trade_client import TradeClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import SecurityType, Market
import datetime
import os
from tigeropen.quote.quote_client import QuoteClient

class TigerController:
    def __init__(_self, credentials_dict={}):
        config = TigerOpenClientConfig(sandbox_debug=None, enable_dynamic_domain=True,props_path=None)
        if credentials_dict.get('tiger_private_key') is None or credentials_dict.get('tiger_account') is None or credentials_dict.get('tiger_id') is None:
            config.private_key = os.getenv('TIGER_PRIVATE_KEY')
            config.account = os.getenv('TIGER_ACCOUNT')
            config.tiger_id = os.getenv('TIGER_ID')
            
        else:
            config.private_key = credentials_dict['tiger_private_key']
            config.account = credentials_dict['tiger_account']
            config.tiger_id = credentials_dict['tiger_id']
        _self.config = config

        _self.trade_client = TradeClient(_self.config)
        _self.quote_client = QuoteClient(_self.config)

        # print(_self.quote_client.grab_quote_permission())




    def get_orders(_self, sec_type = SecurityType.ALL, start_date = datetime.datetime.now()-datetime.timedelta(days=30), end_date = datetime.datetime.now().date()):

        date_diff_days = (end_date - start_date).days
        print("date_diff_days: " + str(date_diff_days))
        # check if start_time and end_time is more than 3 months
        if date_diff_days > 90:
            # split the date range into multiple api calls with 3 months each, and return accumulated results
            filled_orders = []
            for i in range(0, date_diff_days, 90):
                segment_start_date = start_date + datetime.timedelta(days=i)
                segment_end_date = start_date + datetime.timedelta(days=i+90)
                print("segment_start_date: " + str(segment_start_date))
                print("segment_end_date: " + str(segment_end_date))
                orders = _self.trade_client.get_filled_orders(sec_type=sec_type, start_time=str(segment_start_date), end_time=str(segment_end_date))
                filled_orders.extend(orders)
                print("filled_order_count: " + str(len(filled_orders)))
        else:
            filled_orders = _self.trade_client.get_filled_orders(sec_type=sec_type, start_time=str(start_date), end_time=str(end_date))
            
        # sort filled orders by trade_time
        filled_orders.sort(key=lambda x: x.trade_time, reverse=True)
        return filled_orders

    def get_open_orders_options(_self):
        pending_orders = _self.trade_client.get_open_orders(sec_type=SecurityType.OPT)
        return pending_orders
    
    def get_open_positions_stocks(_self):
        
        open_positions = _self.trade_client.get_positions(sec_type=SecurityType.STK)
        return open_positions
    
    def get_open_positions_options(_self):
        open_positions = _self.trade_client.get_positions(sec_type=SecurityType.OPT)
        return open_positions

    def get_cash(_self):
        assets = _self.trade_client.get_assets()
        return assets[0].summary.cash


if __name__ == "__main__":
    controller = TigerController()
    assets = controller.trade_client.get_analytics_asset()
    import json
    # for asset in assets:
    print(json.dumps(assets, indent=4))