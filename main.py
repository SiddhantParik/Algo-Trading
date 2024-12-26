import queue
from api_handler import connect_to_smart_api, fetch_candle_data
from Indicators.zone_calculator import calculate_supply_demand_zones
from Indicators.strategy_executor import execute_strategy
from websocket_listener import websocket

API_KEY = "Your Api Key"
USERNAME = "Your username"
PASSWORD = "Your Password"
TOTP_TOKEN = "Your Api TOTP Token"
SYMBOL_TOKEN = "99926000"
SYMBOL = "NIFTY"

def main():
    # Connect to API
    smart_api, auth_token, feed_token = connect_to_smart_api(API_KEY, USERNAME, PASSWORD, TOTP_TOKEN)

    price_queue = queue.Queue()

    # Start WebSocket in the background to fetch tick data
    websocket(auth_token, API_KEY, USERNAME, feed_token, SYMBOL_TOKEN, price_queue)

    # Fetch candle data
    candle_data = fetch_candle_data(smart_api, SYMBOL_TOKEN)

    # Calculate zones
    zones = calculate_supply_demand_zones(candle_data)

    # Start executing strategy using live price from WebSocket
    execute_strategy(smart_api, zones['supply'], zones['demand'], SYMBOL, SYMBOL_TOKEN, price_queue)

if __name__ == "__main__":
    main()
