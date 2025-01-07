import json
from threading import Thread
import threading
import time
from Indicators.MACD.MACDCalculator import MACD
import queue

macd_queue = queue.Queue()

def macd_calculator_thread(macd_gen, stop_event):
    """Thread function to calculate MACD and put values into the queue."""
    for macd_signal in macd_gen:
        if stop_event.is_set():
            break
        macd_queue.put(macd_signal)
        time.sleep(0.1)  # Simulate MACD calculation delay

def execute_strategy(api_instance):
    """Main strategy execution function."""
    # Initialize the MACD generator and thread
    macd_gen = MACD()
    stop_event = threading.Event()
    macd_thread = Thread(target=macd_calculator_thread, args=(macd_gen, stop_event))
    macd_thread.start()

    call_position = "NIFTY09JAN2523900CE"
    call_token = 48110
    put_position = "NIFTY09JAN2523500PE"
    put_token = 48095
    quantity = 75

    # Tracking variables
    current_position = None
    last_action = None

    try:
        while True:
            # Fetch current position from API
            order_status_response = api_instance.position()
            data = order_status_response.get("data", []) or []
            filtered_data = [
                item for item in data if int(item.get("netqty", 0)) != 0
            ]
            synced_position = [item["tradingsymbol"] for item in filtered_data] if filtered_data else None

            if current_position != synced_position:
                print(f"Manual update detected. Syncing position to: {synced_position}")
                current_position = synced_position

            # Get the latest MACD and Signal values
            if not macd_queue.empty():
                macd_signal = macd_queue.get()
                macd_value = macd_signal['MACD']
                signal_value = macd_signal['Signal']
            else:
                print("MACD values not available. Waiting...")
                time.sleep(1)
                continue

            print(f"MACD: {macd_value}, Signal: {signal_value}")

            # Trading logic
            if current_position is None:
                if macd_value > signal_value and last_action != "Buy Call":
                    place_order(api_instance, call_position, call_token, "BUY", quantity)
                    current_position = [call_position]
                    last_action = "Buy Call"
                elif macd_value < signal_value and last_action != "Buy Put":
                    place_order(api_instance, put_position, put_token, "BUY", quantity)
                    current_position = [put_position]
                    last_action = "Buy Put"
            elif call_position in current_position:
                if macd_value < signal_value:
                    place_order(api_instance, call_position, call_token, "SELL", quantity)
                    current_position = None
                    last_action = "Exit Call"
            elif put_position in current_position:
                if macd_value > signal_value:
                    place_order(api_instance, put_position, put_token, "SELL", quantity)
                    current_position = None
                    last_action = "Exit Put"

            print(f"Current Position: {current_position}")
            time.sleep(1)  # Small delay to avoid excessive CPU usage

    except KeyboardInterrupt:
        print("Stopping strategy...")
        stop_event.set()
        macd_thread.join()
    except Exception as e:
        print(f"Error: {e}")
        stop_event.set()
        macd_thread.join()

def place_order(api_instance, symbol, token, transaction, quantity):
    """Helper function to place orders."""
    params = {
        "variety": "NORMAL",
        "tradingsymbol": symbol,
        "symboltoken": token,
        "transactiontype": transaction,
        "exchange": "NFO",
        "ordertype": "MARKET",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "quantity": quantity,
    }
    order_id = api_instance.placeOrder(params)
    print(f"{transaction} Order executed for {symbol}. Order ID: {order_id}")
