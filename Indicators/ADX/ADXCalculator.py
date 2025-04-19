import queue
import time
import pandas as pd
from api_handler import fetch_candle_data
import numpy as np

def calculate_adx(data, period=14):
    """
    Calculate the Average Directional Index (ADX).
    
    :param data: DataFrame with 'High', 'Low', and 'Close' columns.
    :param period: Lookback period for ADX calculation.
    :return: DataFrame with ADX values.
    """
    high = data['High']
    low = data['Low']
    close = data['Close']

    # Calculate True Range (TR)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Calculate Directional Movement
    plus_dm = high.diff()
    minus_dm = low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)

    # Smoothed TR, +DM, -DM
    tr_smooth = tr.rolling(window=period).sum()
    plus_dm_smooth = plus_dm.rolling(window=period).sum()
    minus_dm_smooth = minus_dm.rolling(window=period).sum()

    # Calculate +DI and -DI
    plus_di = (plus_dm_smooth / tr_smooth) * 100
    minus_di = (minus_dm_smooth / tr_smooth) * 100

    # Calculate DX
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100

    # Calculate ADX
    adx = dx.rolling(window=period).mean()

    data['ADX'] = adx
    data['+DI'] = plus_di
    data['-DI'] = minus_di
    

    return data


   
# Global DataFrame to hold the live candle data
live_candle_data = pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
# Queue to pass data between threads

price_queue = queue.Queue()

def process_live_data(api_instance, token, interval, stop_event, Exchange, gui_app):
    """
    Fetch live candlestick data and queue it for processing.
    The function will stop gracefully if the stop_event is set.
    If an error occurs, updates the GUI status label to 'Stopped'.
    """
    try:
        data_generator = fetch_candle_data(api_instance, token, interval, Exchange, gui_app, stop_event)
        

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


def ADX(gui_app):
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
                    data = calculate_adx(live_candle_data)
                    gui_app.log_signal.emit(f"ADX: {data['ADX']}")
                    # Yield the latest MACD and Signal values
                    yield {
                        'ADX': data['ADX'], 
                        '+DI': data['+DI'], 
                        '-DI': data['-DI']
                    }

            # Allow for processing at 1-second intervals
            time.sleep(1)
    except Exception as e:
        gui_app.log_signal.emit(f"Error in ADX calculation: {e}")
        gui_app.status_label.setText("Status: Stopped")  # Update GUI label
        raise  # Optionally re-raise the exception
