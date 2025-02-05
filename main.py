import sys
import threading
from threading import Event
from trading_gui import AlgorithmApp, TabbedApplication  # Import the GUI app
from api_handler import connect_to_smart_api
from Indicators.MACD.MACDExecution import execute_strategy
from Indicators.MACD.MACDCalculator import process_live_data
from PyQt6.QtWidgets import QApplication  # Import QApplication

# API credentials
API_KEY = "kE1sA1Mu"
USERNAME = "S1226097"
PASSWORD = "2375"
TOTP_TOKEN = "2R7GIVBUWXDFZOJCAFERNRTP6Q"

# Global variables
stop_event_dict = {}
is_running_dict = {}
algorithm_thread_dict = {}
live_data_thread_dict = {}

def start_algorithm(app, tab_id):
    """Start the algorithm and update the UI through the app instance."""
    global is_running_dict, algorithm_thread_dict, live_data_thread_dict, stop_event_dict
    
    if is_running_dict.get(tab_id, False):
        return  # Prevent multiple instances

    is_running_dict[tab_id] = True
    stop_event_dict[tab_id] = Event()
    stop_event_dict[tab_id].clear()

    try:
        # Parse data from GUI
        SYMBOL_TOKEN = app.name_dropdown.currentData()["token"]
        call_position = app.call_option_dropdown.currentText()
        call_token = app.call_option_dropdown.currentData()
        put_position = app.put_option_dropdown.currentText()
        put_token = app.put_option_dropdown.currentData()
        quantity = int(app.quantity_input.text())
        Exchange = app.exchange_dropdown.currentText()
        short_window = int(app.short_window.text())
        long_window = int(app.long_window.text())
        interval = app.time_interval.currentText()
        Transaction_type = app.transaction_type.currentText()
        Target_call = int(app.target_input_call.text())
        Target_put = int(app.target_input_put.text())
        Entry_diff = int(app.entry_diff.text())

        # app.log_signal.emit("Starting Algorithm with:", SYMBOL_TOKEN, call_position, call_token, put_position, put_token, quantity, Exchange)

        # Update UI
        app.status_label.setText("Status: Running...")

        # Connect to API
        smart_api, auth_token, feed_token = connect_to_smart_api(API_KEY, USERNAME, PASSWORD, TOTP_TOKEN)
        
        # Start live data thread for the specific tab
        live_data_thread_dict[tab_id] = threading.Thread(
            target=process_live_data,
            args=(smart_api, SYMBOL_TOKEN, interval, stop_event_dict[tab_id], Exchange, app),
            daemon=True
        )
        live_data_thread_dict[tab_id].start()

        # Start strategy execution thread for the specific tab
        algorithm_thread_dict[tab_id] = threading.Thread(
            target=execute_strategy,
            args=(smart_api, SYMBOL_TOKEN, interval,stop_event_dict[tab_id], call_position, call_token, put_position, put_token, Transaction_type, quantity, Exchange, short_window, long_window, Target_call, Target_put, Entry_diff, app),
            daemon=True
        )
        algorithm_thread_dict[tab_id].start()
    
    except Exception as e:
        app.status_label.setText(f"Error: {str(e)}")
        is_running_dict[tab_id] = False

def stop_algorithm(app, tab_id):
    """Stop the algorithm and update the UI through the app instance."""
    global is_running_dict, algorithm_thread_dict, live_data_thread_dict
    
    if not is_running_dict.get(tab_id, False):
        return

    is_running_dict[tab_id] = False
    app.status_label.setText("Status: Stopping...")
    stop_event_dict[tab_id].set()

    if live_data_thread_dict.get(tab_id) and live_data_thread_dict[tab_id].is_alive():
        live_data_thread_dict[tab_id].join()
    if algorithm_thread_dict.get(tab_id) and algorithm_thread_dict[tab_id].is_alive():
        algorithm_thread_dict[tab_id].join()
    
    app.status_label.setText("Status: Stopped")

# Entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TabbedApplication()
    
    # Connect buttons to functions dynamically based on tab
    def connect_tab_buttons(tab, tab_id):
        tab.start_button.clicked.connect(lambda _, t=tab: start_algorithm(t, tab_id))
        tab.stop_button.clicked.connect(lambda _, t=tab: stop_algorithm(t, tab_id))

    
    for i in range(window.tabs.count()):
        tab = window.tabs.widget(i)
        connect_tab_buttons(tab, i)
    
    window.show()
    sys.exit(app.exec())
