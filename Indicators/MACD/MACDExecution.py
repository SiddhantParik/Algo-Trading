import json
import random
from threading import Thread
import threading
import time
from Indicators.ADX.ADXCalculator import ADX
from Indicators.MACD.MACDCalculator import MACD
import queue
from collections import defaultdict, deque
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectTimeout, RequestException

from api_handler import fetch_price

# Dictionary to store queues for each tab




# Shared lock and timestamp across all instances
rate_limit_lock = threading.Lock()
last_request_time = [0]  # Using a list to make it mutable

def macd_calculator_thread(macd_gen, stop_event, macd_queue):
    """Thread function to calculate MACD and put values into the queue."""
    for macd_signal in macd_gen:
        if stop_event.is_set():
            break
        macd_queue.put(macd_signal)
        time.sleep(0.1)  # Simulate MACD calculation delay

def price_calculator_thread(price_gen, stop_event, price_queue):
    """Thread function to calculate MACD and put values into the queue."""
    for price in price_gen:
        if stop_event.is_set():
            break
        price_queue.put(price)
        time.sleep(0.1)  # Simulate MACD calculation delay

# Increase timeout and retries
def create_session_with_retries(timeout=60):
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=3)  # Retry 3 times
    session.mount('https://', adapter)
    return session

def fetch_data_with_retry(api_instance, gui_app, max_retries=60):
    
    retries = 0
    global last_request_time

    while retries < max_retries:
        with rate_limit_lock:
            elapsed = time.time() - last_request_time[0]
            if elapsed < 1:
                time.sleep(1)
            
            try:
                response = api_instance.position()
                last_request_time[0] = time.time()
                return response
            except ConnectTimeout as e:    
                gui_app.log_signal.emit(f"Timeout error, retrying... {retries}/{max_retries}")
                retries += 1
                time.sleep(1)
                
            except RequestException as e:
                gui_app.log_signal.emit(f"Request error: {e}. Retrying...")
                retries += 1
                time.sleep(1)
                
            except Exception as e:
                gui_app.log_signal.emit(f"Unexpected error: {e}")
                retries += 1
                time.sleep(1)
            
            # # Exponential backoff with some randomness to avoid thundering herd
            # sleep_time = backoff_factor * (2 ** retries) + random.uniform(0, 1)
            # sleep_time = min(sleep_time, 60)  # Cap the maximum delay at 60 seconds
            # gui_app.log_signal.emit(f"Sleeping for {sleep_time:.2f} seconds before next retry...")
            # time.sleep(sleep_time)
    gui_app.log_signal.emit(f"Failed to fetch data after {max_retries} retries.")
    return None



def execute_strategy(api_instance, token, interval, stop_event, call_position, call_token, put_position, put_token, transaction, quantity, Exchange, short_window, long_window, tab_id, macd_queue, price_queue, gui_app):
    """Main strategy execution function."""
    # Initialize the MACD generator and thread
    flag = None
    # Each tab gets its own queues
    histogram_queue = deque(maxlen=3)  # This is now private to this thread/tab


    macd_gen = MACD(short_window, long_window, gui_app)
    macd_thread = Thread(target=macd_calculator_thread, args=(macd_gen, stop_event, macd_queue))
    macd_thread.start()

    price = fetch_price(api_instance, token, interval, Exchange, gui_app)
    price_thread = Thread(target=price_calculator_thread, args=(price, stop_event, price_queue))
    price_thread.start()
    

    # adx_data = ADX(gui_app)
    # print(adx_data[['ADX', '+DI', '-DI']])
    
    
    
    # For Debugging
    # macd_signal = macd_queue.get()
    # for Data in macd_signal:
    #     if stop_event.is_set():
    #         break
    #     gui_app.log_signal.emit(f"Histogram:\n{Data}")
    #     time.sleep(0.1)
    # Tracking variables
    
    current_position = None
    last_action = None
    Squareoff_transaction = None
    buy_price = None
    previous_candle_data = None
    associated_key = None

    try:
        while not stop_event.is_set():  # Continue running until stop_event is set
            # Fetch current position with retry
            order_status_response = fetch_data_with_retry(api_instance, gui_app)
            if not order_status_response:
                gui_app.log_signal.emit("Failed to fetch position after multiple retries. Exiting...")
                break  # Exit strategy if position fetching fails after retries

            # Extract only `call_position` and `put_position` from API response
            data = order_status_response.get("data", []) or []
            filtered_data = [item for item in data if int(item.get("netqty", 0)) != 0]
            current_positions = [item["tradingsymbol"] for item in filtered_data] if filtered_data else None
      

            # Check if selected positions exist
            call_exists = call_position in current_positions if current_positions else False
            put_exists = put_position in current_positions if current_positions else False

            gui_app.log_signal.emit(f"Current Position: {current_positions}")
            

            # Get the latest MACD and Signal values
            if not macd_queue.empty():
                macd_signal = macd_queue.get()
                macd_value = macd_signal['MACD']
                signal_value = macd_signal['Signal']
                histogram = macd_signal['Histogram']
            else:
                gui_app.log_signal.emit("MACD values not available. Waiting...")
                time.sleep(1)
                continue

            # Get the latest price values
            if not price_queue.empty():
                live_price = price_queue.get()
            else:
                gui_app.log_signal.emit("latest Price not available. Waiting...")
                time.sleep(1)
                continue

            if transaction == "BUY":
                Squareoff_transaction = "SELL"
            elif transaction == "SELL":
                Squareoff_transaction = "BUY"
                               

            gui_app.log_signal.emit(f"[Tab {tab_id}] MACD: {macd_value}, Signal: {signal_value}, Histogram: {histogram}")
            
            if histogram is not None:  # Ensure we only store valid values
                if previous_candle_data != histogram:
                    previous_candle_data = histogram  # Update with the latest closed candle
                    
                    if len(histogram_queue) < 2: # Check if we have exactly 2 values
                        histogram_queue.append(histogram)  # Fill queue initially
                    else:
                        histogram_queue.popleft()  # Remove oldest candle data
                        histogram_queue.append(histogram)  # Store latest closed candle
                    
                    gui_app.log_signal.emit(f"Updated Histogram Queue: {list(histogram_queue)}")
    
            # Check if we have exactly 3 values
            if len(histogram_queue) == 2:
                first, second = histogram_queue
                
                if first > second:
                    flag = "SELL"
                elif first < second:
                    flag = "BUY"
                
                gui_app.log_signal.emit(f"Queue Data: {list(histogram_queue)} Flag : {flag}")

            # import time

            # # Debug function for logging
            # def debug_log(gui_app, message):
            #     timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            #     gui_app.log_signal.emit(f"[DEBUG] {timestamp} - {message}")

            # gui_app.log_signal.emit( f"Checking Positions - Call: {call_position} Exists: {call_exists}, Put: {put_position} Exists: {put_exists}")
            # gui_app.log_signal.emit(f"MACD: {macd_value}, Signal: {signal_value}, Histogram: {histogram}")

            if not call_exists and not put_exists:
                gui_app.log_signal.emit("No open positions. Checking if conditions met for new entry...")

                if ((macd_value > signal_value and flag == "SELL") or (macd_value < signal_value and flag == "SELL")) and last_action != "Buy PUT":
                    gui_app.log_signal.emit(f"Placing BUY PUT Order - {put_position} Token: {put_token} Transaction: {transaction} Qty: {quantity}")
                    place_order(api_instance, put_position, put_token, transaction, quantity, Exchange, gui_app)
                    gui_app.log_signal.emit(f"BUY PUT: {put_position} Token: {put_token}")
                    last_action = "Buy PUT"

                elif ((macd_value < signal_value and flag == "BUY") or (macd_value > signal_value and flag == "BUY")) and last_action != "Buy Call":
                    gui_app.log_signal.emit(f"Placing BUY CALL Order - {call_position}, Token: {call_token}, Transaction: {transaction}, Qty: {quantity}")
                    place_order(api_instance, call_position, call_token, transaction, quantity, Exchange, gui_app)
                    gui_app.log_signal.emit(f"BUY Call: {call_position} Token: {call_token}")
                    last_action = "Buy Call"

            elif call_exists:
                gui_app.log_signal.emit(f"Call position exists. Checking conditions for exit...")

                if ((macd_value > signal_value and flag == "SELL") or (macd_value < signal_value and flag == "SELL")):
                    gui_app.log_signal.emit(f"Placing EXIT CALL Order - {call_position}, Token: {call_token}, Squareoff: {Squareoff_transaction}, Qty: {quantity}")
                    place_order(api_instance, call_position, call_token, Squareoff_transaction, quantity, Exchange, gui_app)
                    gui_app.log_signal.emit(f"EXIT CALL: {call_position} Token: {call_token}")
                    last_action = "Exit Call"

            elif put_exists:
                gui_app.log_signal.emit(f"Put position exists. Checking conditions for exit...")

                if ((macd_value < signal_value and flag == "BUY") or (macd_value > signal_value and flag == "BUY")):
                    gui_app.log_signal.emit(f"Placing EXIT PUT Order - {put_position}, Token: {put_token}, Squareoff: {Squareoff_transaction}, Qty: {quantity}")
                    place_order(api_instance, put_position, put_token, Squareoff_transaction, quantity, Exchange, gui_app)
                    gui_app.log_signal.emit(f"EXIT PUT: {put_position} Token: {put_token}")
                    last_action = "Exit Put"

            # Debugging Sleep Time
            gui_app.log_signal.emit("Sleeping for 1 second before next iteration...")
            time.sleep(1)


    except KeyboardInterrupt:
        gui_app.log_signal.emit("Stopping strategy...")
        stop_event.set()  # Signal to stop the threads
        macd_thread.join()  # Ensure the MACD thread stops gracefully
    except Exception as e:
        gui_app.log_signal.emit(f"Error: {e}")
        stop_event.set()  # Ensure the stop_event is set in case of an error
        macd_thread.join()  # Ensure the MACD thread stops gracefully
def place_order(api_instance, symbol, token, transaction, quantity, Exchange, gui_app):
    """Helper function to place orders."""
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
