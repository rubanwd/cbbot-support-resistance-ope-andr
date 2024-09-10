# trading_bot.py

import schedule
import time
import logging
from data_fetcher import DataFetcher
from indicators import Indicators
from risk_management import RiskManagement
from dotenv import load_dotenv
import os
import pandas as pd
from bybit_demo_session import BybitDemoSession
from strategy import Strategy

class TradingBot:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET") 

        if not self.api_key or not self.api_secret:
            raise ValueError("API keys not found. Please set BYBIT_API_KEY and BYBIT_API_SECRET in your .env file.")

        self.data_fetcher = BybitDemoSession(self.api_key, self.api_secret)

        self.strategy = Strategy()
        self.indicators = Indicators()
        self.risk_management = RiskManagement(
            atr_multiplier=float(os.getenv("ATR_MULTIPLIER", 1.0)),
            risk_ratio=float(os.getenv("RISK_RATIO", 1.0))
        )
        self.symbol = os.getenv("TRADING_SYMBOL", 'BTCUSDT')
        self.quantity = float(os.getenv("TRADE_QUANTITY", 0.03))

        self.take_profit_percentage = float(os.getenv("TAKE_PROFIT_PERCENTAGE", 0.15))
        self.stop_loss_percentage = float(os.getenv("STOP_LOSE_PERCENTAGE", 0.15))

        # Load trading parameters
        self.interval = os.getenv("TRADING_INTERVAL", '1')
        self.limit = int(os.getenv("TRADING_LIMIT", 100))
        self.leverage = int(os.getenv("LEVERAGE", 10))

        # Set up logging
        logging.basicConfig(filename='trading_bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def job(self):
        print("-----------------------------")

        last_closed_position = self.data_fetcher.get_last_closed_position(self.symbol)
        if last_closed_position:
            last_closed_time = int(last_closed_position['updatedTime']) / 1000
            current_time = time.time()
            time_since_last_close = current_time - last_closed_time
            print(f"Time since last closed position: {int(time_since_last_close)} seconds")
            if time_since_last_close < 900:  # 15 minutes
                print("The last closed position was less than 15 minutes ago. A new order will not be placed.")
                return
            
        is_open_positions = self.data_fetcher.get_open_positions(self.symbol)
        if is_open_positions:
            print("There is already an open position. A new order will not be placed.")
            return

        is_open_orders = self.data_fetcher.get_open_orders(self.symbol)
        if is_open_orders:
            print("There is an open limit order. A new order will not be placed.")
            return

        get_historical_data = self.data_fetcher.get_historical_data(self.symbol, self.interval, self.limit)
        if get_historical_data is None:
            print("Failed to retrieve historical data.")
            return

        df = self.strategy.prepare_dataframe(get_historical_data)

        # Identify support and resistance levels
        support, resistance = self.strategy.identify_support_resistance(df)

        # Get the latest price
        current_price = self.data_fetcher.get_real_time_price(self.symbol)
        if current_price is None:
            print("Failed to retrieve real-time price.")
            return

        print(f"Support Level: {support:.2f}, Resistance Level: {resistance:.2f}")
        print(f"Current Price: {current_price:.2f}")

        # Place limit orders for support (long) and resistance (short)
        long_order_price = support
        short_order_price = resistance

        # Define percentages
        # take_profit_percentage = 0.05 / 100  # 0.05%
        # stop_loss_percentage = 0.15 / 100    # 0.15%

        # Calculate multipliers for long and short positions
        long_tp_multiplier = 1 + self.take_profit_percentage / 100  # 1.005 for 0.5%
        long_sl_multiplier = 1 - self.stop_loss_percentage / 100    # 0.985 for 1.5%
        short_tp_multiplier = 1 - self.take_profit_percentage / 100 # 0.995 for 0.5%
        short_sl_multiplier = 1 + self.stop_loss_percentage / 100   # 1.015 for 1.5%

        # Risk management (Take Profit and Stop Loss)
        long_tp = long_order_price * long_tp_multiplier
        long_sl = long_order_price * long_sl_multiplier
        short_tp = short_order_price * short_tp_multiplier
        short_sl = short_order_price * short_sl_multiplier


        # Place two limit orders (long at support, short at resistance)
        long_order_result = self.data_fetcher.place_order(
            symbol=self.symbol,
            side='Buy',
            qty=self.quantity,
            current_price=long_order_price,
            leverage=self.leverage,
            stop_loss=long_sl,
            take_profit=long_tp
        )
        
        short_order_result = self.data_fetcher.place_order(
            symbol=self.symbol,
            side='Sell',
            qty=self.quantity,
            current_price=short_order_price,
            leverage=self.leverage,
            stop_loss=short_sl,
            take_profit=short_tp
        )

        if long_order_result or short_order_result:
            print("Waiting for one of the orders to be filled...")
            # Wait for one of the limit orders to be filled
            filled_order = self.strategy.wait_for_order_fill(self.symbol, long_order_result, short_order_result, self.data_fetcher)


            if filled_order:
                print(f"Order filled: {filled_order}")
                # Cancel the other order
                unfilled_order = long_order_result if filled_order == short_order_result else short_order_result
                self.data_fetcher.cancel_order(unfilled_order['orderId'], self.symbol)
        else:
            print("Failed to place orders.")

    def run(self):
        self.job()
        schedule.every(10).seconds.do(self.job)
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()

