# strategy.py

import pandas as pd  # Add this import statement
import time

class Strategy:
    def __init__(self):
        pass

    def prepare_dataframe(self, historical_data):
        df = pd.DataFrame(historical_data)
        df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        df['close'] = df['close'].astype(float)
        df.sort_values('timestamp', inplace=True)
        return df

    def identify_support_resistance(self, df):
        # Identify the most recent support and resistance levels
        support = df['low'].rolling(window=60).min().iloc[-1]  # recent lowest low
        resistance = df['high'].rolling(window=60).max().iloc[-1]  # recent highest high
        return support, resistance

    def wait_for_order_fill(self, symbol, long_order_result, short_order_result, data_fetcher):
        """Waits for one of the limit orders to be filled, and returns the filled order."""
        long_order_id = long_order_result['orderId']
        short_order_id = short_order_result['orderId']

        while True:
            # Check the status of both orders every 2 seconds
            time.sleep(2)

            open_orders = data_fetcher.get_open_orders(symbol)
            open_order_ids = [order['orderId'] for order in open_orders]

            if long_order_id not in open_order_ids:
                print(f"Long order {long_order_id} filled.")
                return long_order_result

            if short_order_id not in open_order_ids:
                print(f"Short order {short_order_id} filled.")
                return short_order_result

            print("Waiting for one of the orders to be filled...")

        return None
