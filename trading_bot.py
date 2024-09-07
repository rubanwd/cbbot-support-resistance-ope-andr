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
from strategy import Strategies

class TradingBot:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("BYBIT_API_KEY")
        self.api_secret = os.getenv("BYBIT_API_SECRET") 

        if not self.api_key or not self.api_secret:
            raise ValueError("API keys not found. Please set BYBIT_API_KEY and BYBIT_API_SECRET in your .env file.")

        self.data_fetcher = BybitDemoSession(self.api_key, self.api_secret)

        self.strategy = Strategies()
        self.indicators = Indicators()
        self.risk_management = RiskManagement(
            atr_multiplier=float(os.getenv("ATR_MULTIPLIER", 1.0)),
            risk_ratio=float(os.getenv("RISK_RATIO", 1.0))
        )
        self.symbol = os.getenv("TRADING_SYMBOL", 'BTCUSDT')
        self.quantity = float(os.getenv("TRADE_QUANTITY", 0.03))

        # Load trading parameters
        self.interval = os.getenv("TRADING_INTERVAL", '1')
        self.limit = int(os.getenv("TRADING_LIMIT", 100))
        self.leverage = int(os.getenv("LEVERAGE", 10))

        # Set up logging
        logging.basicConfig(filename='trading_bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def job(self):
        last_closed_position = self.data_fetcher.get_last_closed_position(self.symbol)
        if last_closed_position:
            last_closed_time = int(last_closed_position['updatedTime']) / 1000
            current_time = time.time()
            time_since_last_close = current_time - last_closed_time
            print(f"Time since last closed position: {int(time_since_last_close)} seconds")
            if time_since_last_close < 60:
                print("The last closed position was less than 1 minute ago. A new order will not be placed.")
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

        # Determine market trend based on last 5-10 hours
        trend = self.strategy.determine_market_trend(df, hours=5)

        # Get the latest price
        current_price = self.data_fetcher.get_real_time_price(self.symbol)
        if current_price is None:
            print("Failed to retrieve real-time price.")
            return

        print(f"Support Level: {support:.2f}, Resistance Level: {resistance:.2f}")
        print(f"Current Price: {current_price:.2f}")
        print(f"Market Trend: {trend}")

        # Place limit order at support or resistance based on the trend
        position_type, order_price = self.strategy.support_resistance_strategy(current_price, support, resistance, trend)

        if position_type and order_price:
            stop_loss, take_profit = self.risk_management.calculate_dynamic_risk_management(df, order_price, position_type)
            print(f"Placing {position_type.upper()} order at price: {order_price:.2f}")
            print(f"Stop Loss: {stop_loss:.2f}")
            print(f"Take Profit: {take_profit:.2f}")

            side = 'Buy' if position_type == 'long' else 'Sell'

            order_result = self.data_fetcher.place_order(
                symbol=self.symbol,
                side=side,
                qty=self.quantity,
                current_price=order_price,  # Use support or resistance as the limit price
                leverage=self.leverage,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            if order_result:
                print(f"Order successfully placed: {order_result}")
            else:
                print("Failed to place order.")
        else:
            print("No suitable signals for position opening.")

    def run(self):
        self.job()
        schedule.every(10).seconds.do(self.job)
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
