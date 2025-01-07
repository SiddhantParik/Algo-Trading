import queue
import threading
import pandas as pd
import time
from datetime import datetime
from api_handler import connect_to_smart_api, fetch_candle_data
from Indicators.MACD.MACDCalculator import process_live_data, MACD
from Indicators.MACD.MACDExecution import execute_strategy



API_KEY = "A1octAeU"
USERNAME = "D117603"
PASSWORD = "2375"
TOTP_TOKEN = "R33AUPIMLMJNCCPW2B3AD7WTRU"
SYMBOL_TOKEN = "99926000"
SYMBOL = "NIFTY"

def main():
    """
    Main entry point for the script.
    """
    # Connect to API
    smart_api, auth_token, feed_token = connect_to_smart_api(API_KEY, USERNAME, PASSWORD, TOTP_TOKEN)

    # Start fetching live data in a separate thread
    live_data_thread = threading.Thread(target=process_live_data, args=(smart_api, SYMBOL_TOKEN), daemon=True)
    live_data_thread.start()

    # Continuously calculate MACD in the main thread
    # MACD()
    execute_strategy(smart_api)

if __name__ == "__main__":
    main()

