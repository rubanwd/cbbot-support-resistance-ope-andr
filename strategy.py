# strategy.py

import pandas as pd

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
        support = df['low'].rolling(window=20).min().iloc[-1]  # recent lowest low
        resistance = df['high'].rolling(window=20).max().iloc[-1]  # recent highest high
        return support, resistance

    def support_resistance_strategy(self, current_price, support, resistance):
        # Open long if the price is near support, open short if it's near resistance
        threshold = 0.01  # Example: 1% threshold for proximity to support/resistance
        if current_price <= support * (1 + threshold):
            return 'long'
        elif current_price >= resistance * (1 - threshold):
            return 'short'
        return None
