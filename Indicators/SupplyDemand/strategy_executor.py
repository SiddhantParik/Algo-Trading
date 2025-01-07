import json
import queue
import time

def execute_strategy(api_instance, supply_zones, demand_zones, nifty_symbol, nifty_token, price_queue, option_symbol="NIFTY02JAN2525000CE", option_token="52603"):
    if not (supply_zones and demand_zones):
        print("No zones available for execution.")
        return

    avg_demand = demand_zones[0][3]  # Average demand price
    avg_supply = supply_zones[0][3]  # Average supply price
    
    buy_order_id = None
    sell_order_id = None
    nifty_price = None  # Initialize the Nifty price variable
    def fetch_nifty_price():
        nonlocal nifty_price  # Ensure we modify the outer scope variable
        while True:
            try:
                # Get live Nifty price from the queue
                nifty_price = price_queue.get()  # Adjust timeout as needed
                print(f"Monitoring Nifty: avg_demand={avg_demand}, avg_supply={avg_supply}")
                print(f"Live Nifty Price: {nifty_price}")

        
            except queue.Empty:
                print("No price data received in the last interval. Retrying...")
    # Start fetching Nifty price in a separate thread
    import threading
    price_fetch_thread = threading.Thread(target=fetch_nifty_price, daemon=True)
    price_fetch_thread.start()

    while True:
        try:
         # Place Buy Order if Nifty price is above the supply zone and no buy order is active
            if nifty_price < avg_demand and buy_order_id is None:
                print("Nifty price is above the supply zone. Placing a buy order for Nifty options.")
                buy_params = {
                    "variety": "ROBO",
                    "tradingsymbol": option_symbol,
                    "symboltoken": option_token,
                    "transactiontype": "BUY",
                    "exchange": "NFO",
                    "ordertype": "MARKET",
                    "producttype": "INTRADAY",
                    "duration": "DAY",
                    "quantity": 75,
                    "squareoff":40,
                    "stoploss":20
                }
                
                buy_order_id = api_instance.placeOrder(buy_params)
                print(f"Buy order placed successfully. Order ID: {buy_order_id}")

            # Monitor the Buy Order Execution
            if buy_order_id:
                order_status_response = api_instance.orderBook()
                orders = order_status_response.get("data", [])
                order_status = next((order for order in orders if order.get("orderid") == buy_order_id), None)

                if isinstance(order_status, str):
                    order_status = json.loads(order_status)

                if order_status and order_status.get('orderstatus') == "complete":
                    print(f"Buy order executed. Order ID: {buy_order_id}")

                    # Place Sell Order when Nifty price drops below the demand zone
                    if nifty_price > avg_supply and sell_order_id is None:
                        print("Nifty price is below the demand zone. Placing a sell order to exit the position.")
                        sell_params = {
                            "variety": "NORMAL",
                            "tradingsymbol": option_symbol,
                            "symboltoken": option_token,
                            "transactiontype": "SELL",
                            "exchange": "NFO",
                            "ordertype": "MARKET",
                            "producttype": "INTRADAY",
                            "duration": "DAY",
                            "quantity": 75
                        }
                        sell_order_id = api_instance.placeOrder(sell_params)
                        print(f"Sell order placed successfully. Order ID: {sell_order_id}")

                        # Reset buy_order_id and sell_order_id after position exit
                        buy_order_id = None
                        sell_order_id = None

                elif order_status and order_status.get('orderstatus') == "rejected":
                    print(f"Buy order rejected. Order ID: {buy_order_id}")
                    buy_order_id = None
                    break
        except Exception as e:
            print(f"Error in strategy execution: {e}")

        time.sleep(1)  # Adjust sleep time for desired frequency
