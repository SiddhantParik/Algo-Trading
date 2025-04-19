import json
import random
from threading import Thread
import threading
import time
from Indicators.ADX.ADXCalculator import ADX
from Indicators.MACD.MACDCalculator import MACD
from collections import deque
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectTimeout, RequestException
from Tabs.Tab1.MACD1 import MACD1
from Tabs.Tab1.api_handler1 import fetch_price1
from api_handler import fetch_price

class MacdStrategy3:
    def __init__(self):
        self.macd_queue = deque()
        self.price_queue = deque()
        self.histogram_list = []
        self.rate_limit_lock = threading.Lock()
        self.last_request_time = [0]  # Mutable container to share timestamp

    def macd_calculator_thread(self, macd_gen, stop_event):
        for macd_signal in macd_gen:
            if stop_event.is_set():
                break
            self.macd_queue.append(macd_signal)
            time.sleep(0.1)

    def price_calculator_thread(self, price_gen, stop_event):
        for price in price_gen:
            if stop_event.is_set():
                break
            self.price_queue.append(price)
            time.sleep(0.1)

    def create_session_with_retries(self, timeout=60):
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=3)
        session.mount('https://', adapter)
        return session

    def fetch_data_with_retry(self, api_instance, gui_app, stop_event, max_retries=60):
        retries = 0
        while retries < max_retries and not stop_event.is_set():
            with self.rate_limit_lock:
                elapsed = time.time() - self.last_request_time[0]
                if elapsed < 1:
                    time.sleep(1)
                try:
                    response = api_instance.position()
                    self.last_request_time[0] = time.time()
                    return response
                except ConnectTimeout:
                    gui_app.log_signal.emit(f"Timeout error, retrying... {retries}/{max_retries}")
                except RequestException as e:
                    gui_app.log_signal.emit(f"Request error: {e}. Retrying...")
                except Exception as e:
                    gui_app.log_signal.emit(f"Unexpected error: {e}")
                retries += 1
                time.sleep(1)
        gui_app.log_signal.emit(f"Failed to fetch data after {max_retries} retries.")
        return None

    def place_order(self, api_instance, symbol, token, transaction, quantity, Exchange, gui_app):
        params = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": token,
            "transactiontype": transaction,
            "exchange": Exchange,
            "ordertype": "MARKET",
            "producttype": "CARRYFORWARD",
            "duration": "DAY",
            "quantity": quantity,
        }
        try:
            order_id = api_instance.placeOrder(params)
            gui_app.log_signal.emit(f"{transaction} Order executed for {symbol}. Order ID: {order_id}")
        except Exception as e:
            gui_app.log_signal.emit(f"Error placing order for {symbol}: {e}")

    def execute_strategy3(self, api_instance, token, interval, stop_event, call_position, call_token,
                         put_position, put_token, transaction, quantity, Exchange, short_window, long_window, gui_app):

        flag = None
        previous_candle_data = None
        current_position = None
        last_action = None
        Squareoff_transaction = None

        macd_gen = MACD1(short_window, long_window, gui_app)
        macd_thread = Thread(target=self.macd_calculator_thread, args=(macd_gen, stop_event))
        macd_thread.start()

        price_gen = fetch_price1(api_instance, token, interval, Exchange, gui_app)
        price_thread = Thread(target=self.price_calculator_thread, args=(price_gen, stop_event))
        price_thread.start()

        try:
            while not stop_event.is_set():
                order_status_response = self.fetch_data_with_retry(api_instance, gui_app, stop_event)
                if not order_status_response:
                    break
                data = order_status_response.get("data", []) or []
                filtered_data = [item for item in data if int(item.get("netqty", 0)) != 0]
                current_positions = [item["tradingsymbol"] for item in filtered_data] if filtered_data else []
                call_exists = call_position in current_positions
                put_exists = put_position in current_positions

                gui_app.log_signal.emit(f"Current Position: {current_positions}")

                if self.macd_queue:
                    macd_signal = self.macd_queue.popleft()
                    macd_value = macd_signal['MACD']
                    signal_value = macd_signal['Signal']
                    histogram = macd_signal['Histogram']
                else:
                    gui_app.log_signal.emit("MACD values not available. Waiting...")
                    time.sleep(1)
                    continue

                if self.price_queue:
                    live_price = self.price_queue.popleft()
                else:
                    gui_app.log_signal.emit("Latest Price not available. Waiting...")
                    time.sleep(1)
                    continue

                Squareoff_transaction = "SELL" if transaction == "BUY" else "BUY"

                gui_app.log_signal.emit(f"MACD: {macd_value}, Signal: {signal_value}, Histogram: {histogram}")

                if histogram is not None and previous_candle_data != histogram:
                    previous_candle_data = histogram
                    if len(self.histogram_list) < 2:
                        self.histogram_list.append(histogram)
                    else:
                        self.histogram_list.pop(0)
                        self.histogram_list.append(histogram)
                    gui_app.log_signal.emit(f"Updated Histogram List: {self.histogram_list}")

                if len(self.histogram_list) == 2:
                    first, second = self.histogram_list
                    flag = "SELL" if first > second else "BUY" if first < second else None
                    gui_app.log_signal.emit(f"List Data: {self.histogram_list} Flag : {flag}")

                if not call_exists and not put_exists:
                    gui_app.log_signal.emit("No open positions. Checking if conditions met for new entry...")
                    if ((macd_value > signal_value and flag == "SELL") or (macd_value < signal_value and flag == "SELL")) and (last_action != "Buy PUT"):
                        self.place_order(api_instance, put_position, put_token, transaction, quantity, Exchange, gui_app)
                        last_action = "Buy PUT"
                    elif ((macd_value < signal_value and flag == "BUY") or (macd_value > signal_value and flag == "BUY")) and (last_action != "Buy Call"):
                        self.place_order(api_instance, call_position, call_token, transaction, quantity, Exchange, gui_app)
                        last_action = "Buy Call"

                elif call_exists:
                    if ((macd_value > signal_value and flag == "SELL") or
                        (macd_value < signal_value and flag == "SELL")):
                        self.place_order(api_instance, call_position, call_token, Squareoff_transaction, quantity, Exchange, gui_app)
                        last_action = "Exit Call"

                elif put_exists:
                    if ((macd_value < signal_value and flag == "BUY") or
                        (macd_value > signal_value and flag == "BUY")):
                        self.place_order(api_instance, put_position, put_token, Squareoff_transaction, quantity, Exchange, gui_app)
                        last_action = "Exit Put"

                gui_app.log_signal.emit("Sleeping for 1 second before next iteration...")
                time.sleep(1)

        except KeyboardInterrupt:
            gui_app.log_signal.emit("Keyboard Interrupt received. Stopping strategy...")
            stop_event.set()
        except Exception as e:
            gui_app.log_signal.emit(f"Error: {e}")
            stop_event.set()
        finally:
            macd_thread.join()
            price_thread.join()
            gui_app.log_signal.emit("Strategy execution stopped.")
