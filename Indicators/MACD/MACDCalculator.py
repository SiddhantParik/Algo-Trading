import queue
import time
import pandas as pd
from api_handler import fetch_candle_data



def calculate_macd(data, short_window=6, long_window=12, signal_window=9):
    
    """
    Calculate MACD, Signal line, and Histogram.
    """
    data['ShortEMA'] = data['close'].ewm(span=short_window, adjust=False).mean()
    data['LongEMA'] = data['close'].ewm(span=long_window, adjust=False).mean()
    data['MACD'] = data['ShortEMA'] - data['LongEMA']
    data['Signal'] = data['MACD'].ewm(span=signal_window, adjust=False).mean()
    data['Histogram'] = data['MACD'] - data['Signal']
     
  
    return data


# Global DataFrame to hold the live candle data
live_candle_data = pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
# Queue to pass data between threads
price_queue = queue.Queue()

def process_live_data(api_instance, token):
    """
    Fetch live candlestick data and queue it for processing.
    """
    data_generator = fetch_candle_data(api_instance, token)

    for candle_data in data_generator:
        if not candle_data.empty:
            # Put new data into the price queue for processing
            price_queue.put(candle_data)

def MACD():
    """
    Continuously update the DataFrame with new data and calculate MACD.
    """
    global live_candle_data
    global data 
    while True:
        if not price_queue.empty():
            # Get the latest data from the queue
            candle_data = price_queue.get()

            # Update the global DataFrame
            live_candle_data = pd.concat([live_candle_data, candle_data]).drop_duplicates(subset=['datetime'], keep='last')
            # print(f"Updated Data:\n{live_candle_data.tail(5)}")

            # Calculate MACD for the updated DataFrame
            data = calculate_macd(live_candle_data)
            # print("Updated Data", data)
            #   # Print the MACD and Signal values
            # print("MACD values:")
            # print(data['MACD'].tail(1))  # Print the last few MACD values for quick reference
            # print("\nSignal values:")
            # print(data['Signal'].tail(1))  # Print the last few Signal values for quick reference

            # Yield the latest MACD and Signal values
            yield {
                'MACD': data['MACD'].iloc[-1],  # Latest MACD value
                'Signal': data['Signal'].iloc[-1]  # Latest Signal value
            }

        # Allow for processing at 1-second intervals
        time.sleep(1)




