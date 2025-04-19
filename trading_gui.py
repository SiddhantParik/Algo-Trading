import json
import subprocess
import sys
from threading import Event
import threading
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, 
    QHBoxLayout, QTextEdit, QTabWidget, QGridLayout, QTabBar, QStyle, QMainWindow, QTabWidget, QVBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QObject
from PyQt6.QtGui import QTextCursor, QIcon


DARK_THEME = """
    QWidget { background-color: #2E2E2E; color: #E0E0E0; font-size: 14px; }
    QComboBox, QLineEdit, QTextEdit { 
        background-color: #3E3E3E; 
        border: 1px solid #555; 
        color: #E0E0E0; 
        padding: 8px;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    QPushButton { 
        background-color: #007BFF; 
        border-radius: 4px; 
        color: white; 
        padding: 8px; 
        font-weight: bold;
    }
    QPushButton:hover { background-color: #0056b3; }
    QLabel { 
        font-weight: bold; 
        margin-bottom: 4px;
        color: #B0B0B0;
    }
    QTabWidget::pane { border: 1px solid #555; }
    QTabWidget::tab-bar { left: 5px; }
    QTabBar::tab { 
        background-color: #3E3E3E; 
        color: #E0E0E0; 
        border: 1px solid #555; 
        padding: 5px 10px; 
        margin-right: 2px; 
        border-top-left-radius: 4px; 
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected { background-color: #007BFF; }
    QLineEdit:focus, QComboBox:focus { 
        border: 1px solid #007BFF;
        background-color: #404040;
    }
    QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    QTabBar::close-button {
        background: transparent;
        border: none;
    }
    QTabBar::close-button:hover {
        background: transparent;
    }
    """


class ConsoleRedirector(QObject):
    text_written = pyqtSignal(str)  # Signal to send text to the main thread

    def __init__(self, console_output):
        super().__init__()  # Call the QObject constructor
        self.console_output = console_output
        
        # Connect the signal to the slot (GUI update)
        self.text_written.connect(self.update_console)

    def write(self, message):
        if message.strip():  # Avoid empty lines
            self.text_written.emit(message)  # Emit signal instead of direct call

    def flush(self):
        pass
    
    def update_console(self, message):
        max_lines = 100
        current_text = self.console_output.toPlainText().splitlines()
        
        if len(current_text) >= max_lines:
            current_text = current_text[1:]  # Remove the oldest line

        current_text.append(message)
        self.console_output.setPlainText("\n".join(current_text))

        # Move cursor to the end to auto-scroll
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.console_output.setTextCursor(cursor)

# Worker thread to run algorithm in the background
class AlgorithmWorker(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, tab_name):
        super().__init__()
        self.tab_name = tab_name
        self.running = True

    def run(self):
        count = 0
        while self.running:
            time.sleep(1)
            count += 1
            # self.update_signal.emit(f"{self.tab_name} - Count: {count}")

    def stop(self):
        self.running = False


class AlgorithmApp(QWidget):
    log_signal = pyqtSignal(str)

    def __init__(self, tab_name):
        super().__init__()
        self.setWindowTitle(f"{tab_name} - Algorithm Control Panel")
        self.setStyleSheet(DARK_THEME)

        self.tab_name = tab_name
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.form_widget = QWidget()
        self.form_layout = QGridLayout(self.form_widget)
        self.main_layout.addWidget(self.form_widget)

        self.setup_ui_elements()
        self.setup_console()
        self.load_json_data()
        self.setup_connections()

        # Individual Console Redirection for this tab
        self.console_redirector = ConsoleRedirector(self.console_output)
        self.log_signal.connect(self.console_redirector.update_console)  # Connect signal to GUI method
        sys.stdout = self.console_redirector  # Redirect print to the QTextEdit widget

       # Worker thread to simulate live data
        self.algorithm_thread = AlgorithmWorker(self.tab_name)
        self.algorithm_thread.update_signal.connect(self.console_redirector.update_console)
        self.algorithm_thread.start()


        

    def setup_ui_elements(self):
        # Exchange Dropdown
        self.exchange_dropdown = QComboBox()
        self.exchange_dropdown.setEditable(True)
        self.exchange_dropdown.lineEdit().setPlaceholderText("Select Exchange...")
        self.exchange_label = QLabel("Select Exchange")

        # Type Dropdown
        self.type_dropdown = QComboBox()
        self.type_dropdown.setEditable(True)
        self.type_dropdown.lineEdit().setPlaceholderText("Select Type...")
        self.type_label = QLabel("Select Type")

        # Name Dropdown
        self.name_dropdown = QComboBox()
        self.name_dropdown.setEditable(True)
        self.name_dropdown.lineEdit().setPlaceholderText("Select Name...")
        self.name_label = QLabel("Select Name")

        # Time Interval Dropdown
        self.time_interval = QComboBox()
        self.time_interval.setEditable(True)
        self.time_interval.lineEdit().setPlaceholderText("Select Time Interval...")
        self.time_interval_label = QLabel("Time Interval")

        # MACD Windows
        self.short_window = QLineEdit()
        self.short_window.setPlaceholderText("Enter Short Window Value...")
        self.short_window_label = QLabel("MACD Short Window")

        self.long_window = QLineEdit()
        self.long_window.setPlaceholderText("Enter Long Window Value...")
        self.long_window_label = QLabel("MACD Long Window")

        # #Entry Difference 
        # self.entry_diff = QLineEdit()
        # self.entry_diff.setPlaceholderText("Enter entry difference Value...")
        # self.entry_diff_label = QLabel("Entry Difference")

        # Call Option Dropdown
        self.call_option_dropdown = QComboBox()
        self.call_option_dropdown.setEditable(True)
        self.call_option_dropdown.lineEdit().setPlaceholderText("Select Call Option...")
        self.call_option_label = QLabel("Call Option")

        # Put Option Dropdown
        self.put_option_dropdown = QComboBox()
        self.put_option_dropdown.setEditable(True)
        self.put_option_dropdown.lineEdit().setPlaceholderText("Select Put Option...")
        self.put_option_label = QLabel("Put Option")

        # # Target Input
        # self.target_input_call = QLineEdit()
        # self.target_input_call.setPlaceholderText("Enter Target...")
        # self.target_label_call = QLabel("Target Call Option")

        # self.target_input_put = QLineEdit()
        # self.target_input_put.setPlaceholderText("Enter Target...")
        # self.target_label_put = QLabel("Target Put Option")

        # Quantity Input
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Enter Quantity...")
        self.quantity_label = QLabel("Quantity")

        # Transaction Type Dropdown
        self.transaction_type = QComboBox()
        self.transaction_type.setEditable(True)
        self.transaction_type.lineEdit().setPlaceholderText("Select Transaction Type...")
        self.transaction_type_label = QLabel("Transaction Type")

        # Lot Size Label
        self.lot_size_label = QLabel("Lot Size: N/A")
        self.lot_size_label.setStyleSheet("color: yellow;")

        # Status Label
        self.status_label = QLabel("Status: Stopped")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; color: red;")

        # Buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.refresh_button = QPushButton("Refresh Data")
        # self.refresh_button.clicked.connect(self.run_data_downloader)

        # Add widgets to form layout
        self.form_layout.addWidget(self.exchange_label, 0, 0)
        self.form_layout.addWidget(self.exchange_dropdown, 1, 0)
        self.form_layout.addWidget(self.type_label, 0, 1)
        self.form_layout.addWidget(self.type_dropdown, 1, 1)
        
        self.form_layout.addWidget(self.name_label, 2, 0)
        self.form_layout.addWidget(self.name_dropdown, 3, 0)
        self.form_layout.addWidget(self.time_interval_label, 2, 1)
        self.form_layout.addWidget(self.time_interval, 3, 1)
        
        self.form_layout.addWidget(self.short_window_label, 4, 0)
        self.form_layout.addWidget(self.short_window, 5, 0)
        self.form_layout.addWidget(self.long_window_label, 4, 1)
        self.form_layout.addWidget(self.long_window, 5, 1)
        
        self.form_layout.addWidget(self.call_option_label, 6, 0)
        self.form_layout.addWidget(self.call_option_dropdown, 7, 0)
        self.form_layout.addWidget(self.put_option_label, 6, 1)
        self.form_layout.addWidget(self.put_option_dropdown, 7, 1)

        
        # self.form_layout.addWidget(self.target_label_call, 8, 0)
        # self.form_layout.addWidget(self.target_input_call, 9, 0)
        # self.form_layout.addWidget(self.target_label_put, 8, 1)
        # self.form_layout.addWidget(self.target_input_put, 9, 1)
        
        self.form_layout.addWidget(self.quantity_label, 10, 0)
        self.form_layout.addWidget(self.quantity_input, 11, 0)
        self.form_layout.addWidget(self.transaction_type_label, 10, 1)
        self.form_layout.addWidget(self.transaction_type, 11, 1)
        
        self.form_layout.addWidget(self.lot_size_label, 12, 0)
        # self.form_layout.addWidget(self.entry_diff_label, 12, 1)
        # self.form_layout.addWidget(self.entry_diff, 13, 1)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        self.form_layout.addLayout(button_layout, 14, 0, 1, 2)
        self.form_layout.addWidget(self.status_label, 15, 0, 1, 2)
        self.form_layout.addWidget(self.refresh_button, 16, 0, 1, 2)

    

    def setup_console(self):
        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText("Live Data...")
        self.main_layout.addWidget(self.console_output)

    def load_json_data(self):
        self.json_data = []
        try:
            with open("scrip_master.json", "r") as f:
                self.json_data = json.load(f)
            print("Data loaded successfully")
        except Exception as e:
            print(f"Error loading JSON data: {e}")
            self.status_label.setText(f"Error: {e}")
        finally:
            self.status_label.setText("Status: Stopped")

        self.type_dropdown.addItems(["Index", "Shares", "Commodities"])
        self.exchange_dropdown.addItems(["BSE", "NSE", "NFO", "MCX", "BFO", "CDS"])
        self.time_interval.addItems(["ONE_MINUTE", "THREE_MINUTE", "FIVE_MINUTE", "TEN_MINUTE", "FIFTEEN_MINUTE", "THIRTY_MINUTE", "ONE_HOUR", "ONE_DAY"])
        self.transaction_type.addItems(["BUY", "SELL"])
        self.type_dropdown.setCurrentText("Index")

    def setup_console(self):
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText("Live Data...")
        self.main_layout.addWidget(self.console_output)


    def setup_connections(self):
        self.type_dropdown.currentTextChanged.connect(self.update_second_field)
        self.name_dropdown.currentIndexChanged.connect(self.update_options)
        self.call_option_dropdown.currentIndexChanged.connect(self.update_lot_size)
        self.update_second_field()

    def log_data(self, message):
        self.log_signal.emit(message)

    

    def update_second_field(self):
        selected_type = self.type_dropdown.currentText().lower()
        self.name_dropdown.clear()
        type_mapping = {"index": "amxidx", "shares": "", "commodities": "comdty"}
        filtered_data = [item for item in self.json_data if item.get("instrumenttype", "").lower() == type_mapping.get(selected_type, "")]
        for item in filtered_data:
            self.name_dropdown.addItem(item["name"], item)
        self.status_label.setText("Status: Stopped")

    def update_options(self):
        selected_item = self.name_dropdown.currentData()
        if not selected_item:
            self.lot_size_label.setText("Lot Size: N/A")
            return
        
        self.call_option_dropdown.clear()
        self.put_option_dropdown.clear()
        selected_symbol = selected_item.get("name", "")
        
        for item in self.json_data:
            if selected_symbol.startswith(item.get("name", "")) and item["symbol"].endswith(("CE", "PE", "FUT")):
                self.call_option_dropdown.addItem(item["symbol"], item["token"])
                self.put_option_dropdown.addItem(item["symbol"], item["token"])
        
        self.update_lot_size()

    def update_lot_size(self):
        selected_symbol = self.call_option_dropdown.currentText()
        if not selected_symbol:
            self.lot_size_label.setText("Lot Size: N/A")
            return
        
        for item in self.json_data:
            if item.get("symbol") == selected_symbol:
                self.lot_size_label.setText(f"Lot Size: {item.get('lotsize', 'N/A')}")
                return
        
        self.lot_size_label.setText("Lot Size: N/A")
    

    @staticmethod
    def global_exception_handler(type, value, traceback):
        error_message = f"Uncaught Exception: {str(value)}"
        print(error_message)
        sys.__excepthook__(type, value, traceback)

class CloseableTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        
        # Load the custom close icon
        
        
        # Style the close buttons
        for i in range(self.tabBar().count()):
            self.style_close_button(i)

    def style_close_button(self, index):
        tab_bar = self.tabBar()
        close_button = QPushButton()
        close_button.setIcon(QIcon("x-symbol-svgrepo-com.svg"))
        close_button.setIconSize(QSize(10, 10))  # Slightly bigger
        close_button.setFixedSize(18, 18)  # More padding
        close_button.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                border-radius: 9px;
            }
            QPushButton:hover {
                background-color: rgba(255, 85, 85, 0.5); /* Semi-transparent red */
            }
        """)

        close_button.clicked.connect(lambda: self.close_tab(index))
        
        # Manually assign the button
        tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, close_button)

    def close_tab(self, index):
        if self.count() > 1:  # Keep at least one tab
            self.removeTab(index)
            
    def addTab(self, widget, label):
        index = super().addTab(widget, label)
        self.style_close_button(index)
        return index

class TabbedApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Tab Algorithm Control")
        self.setGeometry(100, 100, 800, 800)
        self.setStyleSheet(DARK_THEME)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.setWindowTitle("Algo Trading App")

        # Set the icon
        self.setWindowIcon(QIcon('Algo_Trading.png'))  # Replace with your icon path

        self.setGeometry(100, 100, 800, 600)  # Window size and position

        self.tab_consoles = {}  # Dictionary to store console redirection for each tab

        for i in range(3):  # Create 3 tabs with AlgorithmApp instances
            tab = AlgorithmApp(f"Algorithm {i+1}")
            self.tabs.addTab(tab, f"Algorithm {i+1}")

            # Set the console redirection for this tab
            self.tab_consoles[i] = tab.console_redirector

        add_tab_icon = QIcon("add-svgrepo-com.svg")
        self.add_tab_button = QPushButton()
        self.add_tab_button.setIcon(add_tab_icon)
        self.add_tab_button.setToolTip("Add New Algorithm Tab")
        self.add_tab_button.clicked.connect(self.add_new_tab)
        self.tabs.setCornerWidget(self.add_tab_button, Qt.Corner.TopRightCorner)

        # # Switch console whenever the tab changes (but don't redirect stdout every time)
        # self.tabs.currentChanged.connect(self.switch_console)

        # # Call switch_console for the first tab to ensure it gets redirected immediately
        # self.switch_console(self.tabs.currentIndex())

    def add_tab(self, name):
        new_tab = AlgorithmApp(name)
        self.tabs.addTab(new_tab, name)
        tab_id = self.tabs.indexOf(new_tab)  # Get the tab index
        self.tab_consoles[tab_id] = new_tab.console_redirector  # Add the redirection for new tab

    def add_new_tab(self):
        tab_count = self.tabs.count() + 1
        self.add_tab(f"Algorithm {tab_count}")

    # def switch_console(self, tab_id):
    #     """Switch console redirection to a fixed tab."""
    #     if tab_id is None:
    #         tab_id = 0  # Default to the first tab if no index is provided

    #     # Get the console redirection for the selected tab
    #     fixed_widget = self.tabs.widget(tab_id)

    #     if isinstance(fixed_widget, AlgorithmApp):
    #         # Only set stdout to the selected tab's console
    #         sys.stdout = self.tab_consoles.get(tab_id, sys.__stdout__)  # Default to sys.__stdout__ if not found
    #         sys.stderr = sys.stdout  # Redirect stderr to the same place as stdout
