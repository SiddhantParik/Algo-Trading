import json
import threading
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from logzero import logger
import queue

def websocket(authToken, api_key, username, feedToken, SYMBOL_TOKEN, price_queue):
    # Set up WebSocket connection and handlers
    AUTH_TOKEN = authToken
    API_KEY = api_key
    CLIENT_CODE = username
    FEED_TOKEN = feedToken
    correlation_id = "abc123"
    mode = 1
   

    token_list = [
        {
            "exchangeType": 1,
            "tokens": [SYMBOL_TOKEN]
        }
    ]

    # Initialize WebSocket
    sws = SmartWebSocketV2(AUTH_TOKEN, API_KEY, CLIENT_CODE, FEED_TOKEN)

    def on_data(wsapp, message):
        """Handle incoming WebSocket data"""
        try:
            logger.info(f"Raw WebSocket message: {message}")
            # Parse message and extract the price
            # tick_data = json.loads(message).get("data", {})
            if message:
                current_price = message.get("last_traded_price") / 100  # Adjust based on actual WebSocket data structure
                price_queue.put(current_price)  # Add the processed price to the queue
                # logger.info(f"Processed Tick Data: {current_price}")
            
            else:
                logger.warning("Empty tick data received.")
        except Exception as e:
            logger.error(f"Error processing tick data: {e}")

        
        

    def on_open(wsapp):
        """Handle WebSocket open event"""
        logger.info("WebSocket connection opened")
        sws.subscribe(correlation_id, mode, token_list)

    def on_error(wsapp, error):
        """Handle WebSocket error event"""
        logger.error(f"WebSocket Error: {error}")

    def on_close(wsapp):
        """Handle WebSocket close event"""
        logger.info("WebSocket connection closed")

    def close_connection():
        """Close the WebSocket connection"""
        sws.close_connection()

    # Assign callbacks to WebSocket
    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close

    def run_websocket():
        """Run the WebSocket connection in a separate thread"""
        try:
            sws.connect()
        except Exception as e:
            logger.error(f"Error while connecting to WebSocket: {e}")

    # Start WebSocket in a separate thread
    websocket_thread = threading.Thread(target=run_websocket)
    websocket_thread.daemon = True  # Daemon thread to exit when main program exits
    websocket_thread.start()

    # Optional: Monitor WebSocket connection in the main thread
    # while True:
    #     # You can implement any other logic here or just keep the program running
    #     # Example: If you need to check for price updates or events
    #     pass

