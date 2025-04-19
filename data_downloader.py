import requests
import json
import sys
import time
from datetime import datetime
import os

DATA_FILE = "scrip_master.json"
DATA_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

def download_data(gui_app):
    """Fetch data from the URL, delete old data and store new data in a local JSON file."""
    try:
        # Delete the existing data file if it exists
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            gui_app.log_signal.emit(f"[{datetime.now()}] Existing data file '{DATA_FILE}' deleted.")

        gui_app.log_signal.emit(f"[{datetime.now()}] Downloading data from {DATA_URL}...")
        response = requests.get(DATA_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Save the new data to the file
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        gui_app.log_signal.emit(f"[{datetime.now()}] Data downloaded successfully and stored in {DATA_FILE}")
    except Exception as e:
        gui_app.log_signal.emit(f"[{datetime.now()}] Error downloading data: {e}")


