import subprocess
import sys
import threading
from threading import Event
from Tabs.Tab1.MACD1 import process_live_data1
from Tabs.Tab1.api_handler1 import connect_to_smart_api1
from Tabs.Tab2.MACD2 import process_live_data2
from Tabs.Tab2.api_handler2 import connect_to_smart_api2
from Tabs.Tab3.MACD3 import process_live_data3
from Tabs.Tab3.api_handler3 import connect_to_smart_api3
from Tabs.Tab3.tab3 import MacdStrategy3
from Tabs.Tab4.MACD4 import process_live_data4
from Tabs.Tab4.api_handler4 import connect_to_smart_api4
from Tabs.Tab4.tab4 import MacdStrategy4
from data_downloader import download_data
from Tabs.Tab2.tab2 import MacdStrategy2
from Tabs.Tab1.tab1 import MacdStrategy1
from trading_gui import AlgorithmApp, TabbedApplication  # Import the GUI app
from api_handler import connect_to_smart_api
from Indicators.MACD.MACDExecution import execute_strategy
from Indicators.MACD.MACDCalculator import process_live_data
from PyQt6.QtWidgets import QApplication  # Import QApplication
from PyQt6.QtGui import QIcon

# API credentials
API_KEY1 = "rYAoSM8D"
API_KEY2 = "VsXImU9u"
API_KEY3 = "t9mlQQbC"
API_KEY4 = "4t986hse"
USERNAME = "D117603"
PASSWORD = "2375"
TOTP_TOKEN = "R33AUPIMLMJNCCPW2B3AD7WTRU"

# Global variables
stop_event_dict = {}
is_running_dict = {}
algorithm_thread_dict = {}
live_data_thread_dict = {}
 # Initialize strategy
strategy1 = MacdStrategy1()
strategy2 = MacdStrategy2()
strategy3 = MacdStrategy3()
strategy4 = MacdStrategy4()

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
        # Target_call = int(app.target_input_call.text())
        # Target_put = int(app.target_input_put.text())
        # Entry_diff = int(app.entry_diff.text())

        # app.log_signal.emit("Starting Algorithm with:", SYMBOL_TOKEN, call_position, call_token, put_position, put_token, quantity, Exchange)

        # Update UI
        

        # Start strategy execution thread for the specific tab
        if tab_id == 0: 

            app.status_label.setText("Status: Running...")

            # Connect to API
            smart_api1, auth_token, feed_token = connect_to_smart_api1(API_KEY1, USERNAME, PASSWORD, TOTP_TOKEN)
            
            # Start live data thread for the specific tab
            live_data_thread_dict[1] = threading.Thread(
                target=process_live_data1,
                args=(smart_api1, SYMBOL_TOKEN, interval, stop_event_dict[tab_id], Exchange, app),
                daemon=True
            )
            live_data_thread_dict[1].start()

            # Start strategy thread
            algorithm_thread_dict[1] = threading.Thread(
                target=strategy1.execute_strategy1,
                args=(smart_api1, SYMBOL_TOKEN, interval, stop_event_dict[tab_id],
                    call_position, call_token, put_position, put_token,
                    Transaction_type, quantity, Exchange,
                    short_window, long_window, app),
                daemon=True
            )
            algorithm_thread_dict[1].start()
        
        elif tab_id == 1:

            app.status_label.setText("Status: Running...")

            # Connect to API
            smart_api2, auth_token, feed_token = connect_to_smart_api2(API_KEY2, USERNAME, PASSWORD, TOTP_TOKEN)
            
            # Start live data thread for the specific tab
            live_data_thread_dict[2] = threading.Thread(
                target=process_live_data2,
                args=(smart_api2, SYMBOL_TOKEN, interval, stop_event_dict[tab_id], Exchange, app),
                daemon=True
            )
            live_data_thread_dict[2].start()

            # Start strategy thread
            algorithm_thread_dict[2] = threading.Thread(
                target=strategy2.execute_strategy2,
                args=(
                    smart_api2, SYMBOL_TOKEN, interval, stop_event_dict[tab_id],
                    call_position, call_token, put_position, put_token,
                    Transaction_type, quantity, Exchange,
                    short_window, long_window, app
                )
            )
            algorithm_thread_dict[2].start()

        elif tab_id == 2:

            app.status_label.setText("Status: Running...")

            # Connect to API
            smart_api3, auth_token, feed_token = connect_to_smart_api3(API_KEY3, USERNAME, PASSWORD, TOTP_TOKEN)
            
            # Start live data thread for the specific tab
            live_data_thread_dict[3] = threading.Thread(
                target=process_live_data3,
                args=(smart_api3, SYMBOL_TOKEN, interval, stop_event_dict[tab_id], Exchange, app),
                daemon=True
            )
            live_data_thread_dict[3].start()

            # Start strategy thread
            algorithm_thread_dict[3] = threading.Thread(
                target=strategy3.execute_strategy3,
                args=(
                    smart_api3, SYMBOL_TOKEN, interval, stop_event_dict[tab_id],
                    call_position, call_token, put_position, put_token,
                    Transaction_type, quantity, Exchange,
                    short_window, long_window, app
                )
            )
            algorithm_thread_dict[3].start()

               
    
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

    if stop_event_dict[tab_id].set():
        live_data_thread_dict[1].join()
        live_data_thread_dict[2].join()
        live_data_thread_dict[3].join()
    if stop_event_dict[tab_id].set():
        algorithm_thread_dict[1].join()
        algorithm_thread_dict[2].join()
        algorithm_thread_dict[3].join()
    
    app.status_label.setText("Status: Stopped")


# def run_data_downloader(app):
#         try:
#             subprocess.run(["python", "data_downloader.py", app], check=True)
#             # self.close()
#             # subprocess.run(["python", "main.py"])
#         except subprocess.CalledProcessError as e:
#             app.log_signal.emit(f"Error executing script: {e}")

# Entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TabbedApplication()
     # Set application-level icon (for taskbar)
    app.setWindowIcon(QIcon('Algo_Trading.png'))
    
    # Connect buttons to functions dynamically based on tab
    def connect_tab_buttons(tab, tab_id):
        tab.start_button.clicked.connect(lambda _, t=tab: start_algorithm(t, tab_id))
        tab.stop_button.clicked.connect(lambda _, t=tab: stop_algorithm(t, tab_id))
        tab.refresh_button.clicked.connect(lambda _, t=tab: download_data(t))

    
    for i in range(window.tabs.count()):
        tab = window.tabs.widget(i)
        connect_tab_buttons(tab, i)
    
    window.show()
    sys.exit(app.exec())
