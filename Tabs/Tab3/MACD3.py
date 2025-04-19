import queue
import time
import pandas as pd
from Tabs.Tab3.api_handler3 import fetch_candle_data3



def calculate_macd3(data, short_window, long_window, gui_app, signal_window=9):
    """
    Calculate MACD, Signal line, and Histogram with proper data validation.
    """
    # Check if we have enough data
    # if len(data) < long_window:
    #     raise ValueError("Insufficient data for MACD calculation.")
    
    # Ensure 'close' column is numeric
    data['close'] = pd.to_numeric(data['close'], errors='coerce')

    # Calculate ShortEMA and LongEMA
    data['ShortEMA'] = data['close'].ewm(span=short_window, adjust=False).mean()
    data['LongEMA'] = data['close'].ewm(span=long_window, adjust=False).mean()
    
    # Calculate MACD and Signal
    data['MACD'] = data['ShortEMA'] - data['LongEMA']
    data['Signal'] = data['MACD'].ewm(span=signal_window, adjust=False).mean()

    # Calculate Histogram
    data['Histogram'] = data['MACD'] - data['Signal']
    
    # Optional: Round the values for better alignment with the expected output
    data['ShortEMA'] = data['ShortEMA'].round(2)
    data['LongEMA'] = data['LongEMA'].round(2)
    data['MACD'] = data['MACD'].round(2)
    data['Signal'] = data['Signal'].round(2)
    data['Histogram'] = data['Histogram'].round(2)
    
    # # Debugging output: Check the last few rows of the data
    # gui_app.log_signal.emit("MACD Calculation:")
    # gui_app.log_signal.emit(data[['Histogram']].tail())
    
    return {
        "MACD": data['MACD'].iloc[-1],
        "Signal": data['Signal'].iloc[-1],
        "Histogram": data['Histogram'].iloc[-1],
        "ShortEMA": data['ShortEMA'].iloc[-1],
        "LongEMA": data['LongEMA'].iloc[-1]
    }

# Global DataFrame to hold the live candle data
live_candle_data = pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
# Queue to pass data between threads

price_queue = queue.Queue()

def process_live_data3(api_instance, token, interval, stop_event, Exchange, gui_app):
    """
    Fetch live candlestick data and queue it for processing.
    The function will stop gracefully if the stop_event is set.
    If an error occurs, updates the GUI status label to 'Stopped'.
    """
    try:
        data_generator = fetch_candle_data3(api_instance, token, interval, Exchange, gui_app, stop_event)
        

        for candle_data in data_generator:
            if stop_event.is_set():
                gui_app.log_signal.emit("Stopping live data processing...")
                gui_app.status_label.setText("Status: Stopped")
                break  # Exit the loop if the stop_event is set

            if not candle_data.empty:
                # Put new data into the price queue for processing
                price_queue.put(candle_data)

            # Optionally, add a small sleep to prevent CPU overuse
            time.sleep(0.1)

    except Exception as e:
        gui_app.log_signal.emit(f"Error occurred: {e}")
        gui_app.status_label.setText("Status: Stopped")  # Update GUI label
        raise  # Optionally re-raise the exception


def MACD3(short_window, long_window, gui_app):
    """
    Continuously update the DataFrame with new data and calculate MACD.
    If an error occurs, updates the GUI status label to 'Stopped'.
    """
    global live_candle_data
    global data
    try:
        while True:
            if not price_queue.empty():
                # Get the latest data from the queue
                candle_data = price_queue.get()

                # Check if `candle_data` is not empty or all-NA
                if not candle_data.empty and not candle_data.isna().all().all():
                    # Update the global DataFrame
                    live_candle_data = (
                        pd.concat([live_candle_data, candle_data])
                        .drop_duplicates(subset=['datetime'], keep='last')
                    )

                    # Calculate MACD for the updated DataFrame
                    data = calculate_macd3(live_candle_data, short_window, long_window, gui_app)

                    # Yield the latest MACD and Signal values
                    yield {
                        'MACD': data['MACD'],  # Latest MACD value
                        'Signal': data['Signal'],  # Latest Signal value
                        'Histogram': data['Histogram']
                    }

            # Allow for processing at 1-second intervals
            time.sleep(1)
    except Exception as e:
        gui_app.log_signal.emit(f"Error in MACD calculation: {e}")
        gui_app.status_label.setText("Status: Stopped")  # Update GUI label
        raise  # Optionally re-raise the exception
