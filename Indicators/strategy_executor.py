import json
import queue
import time

def execute_strategy(api_instance, supply_zones, demand_zones, nifty_symbol, nifty_token, price_queue, option_symbol="NIFTY26DEC2425000CE", option_token="71362"):
    if not (supply_zones and demand_zones):
        print("No zones available for execution.")
        return

    avg_demand = demand_zones[0][3]  # Average demand price
    avg_supply = supply_zones[0][3]  # Average supply price
    

    buy_order_id = None

    while True:
        
        try:
            # Get live Nifty price from the queue
            nifty_price = price_queue.get()  # Adjust timeout as needed
            print(f"Monitoring Nifty: avg_demand={avg_demand}, avg_supply={avg_supply}")
            print(f"Live Nifty Price: {nifty_price}")

            # Check if Nifty is below the average demand zone to place a buy order
            if nifty_price < avg_demand and buy_order_id is None:
                print("Nifty price is below the demand zone. Placing a buy order for Nifty options.")
                buy_params = {
                    "variety": "NORMAL",
                    "tradingsymbol": option_symbol,
                    "symboltoken": option_token,
                    "transactiontype": "BUY",
                    "exchange": "NFO",
                    "ordertype": "LIMIT",
                    "producttype": "INTRADAY",
                    "duration": "DAY",
                    "price": avg_demand,
                    "quantity": 1
                }
                buy_order_id = api_instance.placeOrder(buy_params)
                print(f"Buy order placed successfully. Order ID: {buy_order_id}")

            # Monitor buy order execution
            if buy_order_id:
                order_status_response = api_instance.getTranStatus({"orderid": buy_order_id})
                if isinstance(order_status_response, str):
                    order_status_response = json.loads(order_status_response)

                if order_status_response.get("status") == "COMPLETE":
                    print(f"Buy order executed. Order ID: {buy_order_id}")

                    # Place sell order once buy is executed
                    sell_params = {
                        "variety": "NORMAL",
                        "tradingsymbol": option_symbol,
                        "symboltoken": option_token,
                        "transactiontype": "SELL",
                        "exchange": "NFO",
                        "ordertype": "LIMIT",
                        "producttype": "INTRADAY",
                        "duration": "DAY",
                        "price": avg_supply,
                        "quantity": 1
                    }
                    sell_order_id = api_instance.placeOrder(sell_params)
                    print(f"Sell order placed successfully. Order ID: {sell_order_id}")

                    # Reset buy_order_id to stop further buy orders
                    buy_order_id = None


            # Exit condition when Nifty crosses the supply zone
            if nifty_price > avg_supply:
                print("Nifty price crossed the supply zone. Exiting monitoring.")
                break

        except queue.Empty:
            print("No price data received in the last interval. Retrying...")
        except Exception as e:
            print(f"Error in strategy execution: {e}")

        time.sleep(0)  # Reduce sleep time for more frequent checks
