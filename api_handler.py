import threading
import time
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta
import pyotp
import requests
from requests.exceptions import ConnectTimeout

# Subclassing SmartConnect to modify the timeout
class CustomSmartConnect(SmartConnect):
    def __init__(self, api_key, timeout=600):
        super().__init__(api_key)
        self.timeout = timeout  # Set custom timeout
    
    # Override the method that makes requests to set a timeout
    def _make_request(self, *args, **kwargs):
        # Add timeout to kwargs for requests
        kwargs['timeout'] = self.timeout
        return super()._make_request(*args, **kwargs)
    def get_position_with_retry(api_instance, retries=50, delay=60):
        for attempt in range(retries):
            try:
                position_data = api_instance.getPosition()
                return position_data
            except requests.exceptions.Timeout:
                print(f"Timeout occurred. Retrying in {delay} seconds... (Attempt {attempt + 1}/{retries})")
                time.sleep(delay)
            except Exception as e:
                print(f"Error fetching position data: {e}")
                time.sleep(delay)
        raise Exception("Max retries exceeded for fetching position data.")

def connect_to_smart_api(api_key, username, password, totp_token):
    retries = 0
    max_retries=60
    retry_delay=5

    while retries < max_retries:
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

        except ConnectTimeout as e:
            retries += 1
            print(f"Connection timeout error. Retrying {retries}/{max_retries}...")
            time.sleep(retry_delay)  # Wait before retrying
        except Exception as e:
            print(f"Error fetching position: {e}")
            break
    return None






def fetch_candle_data(api_instance, token, interval, Exchange, gui_app,days=9):
    """
    Fetch live candle data continuously at a specified interval.
    ="FIVE_MINUTE"
    """
    while True:
        try:
            current_date = datetime.now()
            to_date = current_date.replace(hour=23, minute=30, second=0, microsecond=0)
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

            # gui_app.log_signal.emit(f"Fetched Data:\n{candle_data["close"].iloc[-1]}")

            # Yield the data for further processing
            yield candle_data

            # Wait for 1 second before the next request
            time.sleep(1)
        except requests.exceptions.Timeout:
            gui_app.log_signal.emit("Request timed out. Retrying...")
            time.sleep(6)
        except Exception as e:
            gui_app.log_signal.emit(f"Error fetching data: {e}")
            time.sleep(6)

def fetch_price(api_instance, token, interval, Exchange, gui_app,days=9):
    """
    Fetch live candle data continuously at a specified interval.
    ="FIVE_MINUTE"
    """
    while True:
        try:
            current_date = datetime.now()
            to_date = current_date.replace(hour=23, minute=30, second=0, microsecond=0)
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

            # gui_app.log_signal.emit(f"Fetched Data:\n{candle_data["close"].iloc[-1]}")

            # Yield the data for further processing
            yield {
                'Live_price' : candle_data["close"].iloc[-1]
                }

            # Wait for 1 second before the next request
            time.sleep(1)
        except requests.exceptions.Timeout:
            gui_app.log_signal.emit("Request timed out. Retrying...")
            time.sleep(6)
        except Exception as e:
            gui_app.log_signal.emit(f"Error fetching data: {e}")
            time.sleep(6)