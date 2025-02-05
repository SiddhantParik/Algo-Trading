import requests
import json
import schedule
import time
from datetime import datetime
import os

DATA_FILE = "scrip_master.json"
DATA_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

def download_data():
    """Fetch data from the URL, delete old data and store new data in a local JSON file."""
    try:
        # Delete the existing data file if it exists
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            print(f"[{datetime.now()}] Existing data file '{DATA_FILE}' deleted.")

        print(f"[{datetime.now()}] Downloading data from {DATA_URL}...")
        response = requests.get(DATA_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Save the new data to the file
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        print(f"[{datetime.now()}] Data downloaded successfully and stored in {DATA_FILE}")
    except Exception as e:
        print(f"[{datetime.now()}] Error downloading data: {e}")

# Schedule the data download daily at 9:45 AM
schedule.every().day.at("09:45").do(download_data)

if __name__ == "__main__":
    # Perform initial download on script start
    download_data()

    # Keep the script running to schedule daily downloads
    print("Scheduler started. Waiting for the next run...")
    while True:
        schedule.run_pending()
        time.sleep(1)
