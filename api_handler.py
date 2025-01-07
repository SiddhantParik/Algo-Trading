import threading
import time
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta

import pyotp

def connect_to_smart_api(api_key, username, password, totp_token):
    try:
        smart_api = SmartConnect(api_key)
        totp = pyotp.TOTP(totp_token).now()
        session = smart_api.generateSession(username, password, totp)

        if session['status'] ==False:
            raise Exception("Login failed")

        auth_token = session['data']['jwtToken']
        feed_token = smart_api.getfeedToken()
        # print(feed_token)
        
        return smart_api, auth_token, feed_token

    except Exception as e:
        raise Exception(f"API connection failed: {e}")





def fetch_candle_data(api_instance, token, interval="FIVE_MINUTE", days=1):
    """
    Fetch live candle data continuously at a specified interval.
    """
    while True:
        current_date = datetime.now()
        to_date = current_date.replace(hour=15, minute=30, second=0, microsecond=0)
        from_date = (current_date - timedelta(days=days)).replace(hour=9, minute=0, second=0, microsecond=0)

        historic_params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M"),
        }

        # Fetch the candle data
        candle_data = api_instance.getCandleData(historic_params)
        columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        candle_data = pd.DataFrame(candle_data["data"], columns=columns)

        # print(f"Fetched Data:\n{candle_data.tail(5)}")

        # Yield the data for further processing
        yield candle_data

        # Wait for 1 second before the next request
        time.sleep(1)
