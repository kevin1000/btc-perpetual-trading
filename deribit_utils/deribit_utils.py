import pandas_ta as ta
import requests
import json
import websockets
import asyncio
import pandas as pd
import numpy as np
import time
import logging
from gcp_utils.secret_manager import GCPManager

# Subacount btcridermulti

# Deribit  API URL for authentication
auth_url = "https://deribit.com/api/v2/public/auth"
# Deribit  API URL for placing an order
order_url = "https://deribit.com/api/v2/private/buy"  # Change "buy" to "sell" for a sell order

# Create an instance of the GCPManager with your project Id
project_id = "trading-etl"
gcp_manager = GCPManager(project_id=project_id)

# Access the secrets
api_key = gcp_manager.access_secret_version(secret_id="btcridermulti-api-key")
api_secret = gcp_manager.access_secret_version(secret_id="btcridermulti-api-secret")


# Prepare the authentication data
auth_data = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "public/auth",
    "params": {
        "grant_type": "client_credentials",  # Authentication method
        "client_id": api_key,
        "client_secret": api_secret
    }
}

# Others trading parameters
cl_ord_id = "b14"

# Global configuration variables
INSTRUMENT_NAME = "BTC-PERPETUAL"
TICK_SIZE = 0.5  # Tick size for rounding
STOP_LOSS_PERCENTAGE = 0.09  # 9% for stop loss
TAKE_PROFIT_PERCENTAGE = 0.09  # 9% for take profit
TIME_LIMIT_SECONDS = 200  # Time limit for order execution in seconds

async def authenticate(api_key, api_secret, connection_type="websocket", websocket=None, auth_url=None):
    """
    Authenticate with the Deribit API.

    Parameters:
    - api_key: Your API key
    - api_secret: Your API secret
    - connection_type: "websocket" or "http"
    - websocket: WebSocket connection object (required if connection_type is "websocket")
    - auth_url: Authentication URL (required if connection_type is "http")

    Returns:
    - access_token if connection_type is "http"
    - True if WebSocket authentication is successful
    """

    auth_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "public/auth",
        "params": {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret
        }
    }

    if connection_type == "http":
        # HTTP authentication
        response = requests.post(auth_url, json=auth_msg)
        if response.status_code == 200:
            auth_response = response.json()
            access_token = auth_response["result"]["access_token"]
            expires_in = auth_response["result"]["expires_in"]
            print(f"Access Token: {access_token}")
            print(f"Expires in: {expires_in} seconds")
            return access_token
        else:
            print(f"Failed to authenticate. Status code: {response.status_code}")
            print(response.text)
            return None

    elif connection_type == "websocket":
        # WebSocket authentication
        await websocket.send(json.dumps(auth_msg))
        response = await websocket.recv()
        response_json = json.loads(response)
        if "result" in response_json and "access_token" in response_json["result"]:
            print("WebSocket Auth Response:", response)
            return True
        else:
            print("WebSocket Authentication failed:", response)
            return False

    else:
        print("Invalid connection type. Choose either 'http' or 'websocket'.")
        return None

async def get_available_balance_btc(websocket):
    balance_request = {
        "jsonrpc": "2.0",
        "id": 4219,
        "method": "private/get_account_summary",
        "params": {
            "currency": "BTC"
        }
    }

    await websocket.send(json.dumps(balance_request))
    response = await websocket.recv()
    balance_data = json.loads(response)

    if "result" in balance_data:
        return balance_data["result"]["available_funds"]
    else:
        print("Error retrieving BTC balance:", balance_data)
        return 0

async def get_btc_usd_price(websocket):
    price_request = {
        "jsonrpc": "2.0",
        "id": 4220,
        "method": "public/ticker",
        "params": {
            "instrument_name": INSTRUMENT_NAME
        }
    }

    await websocket.send(json.dumps(price_request))
    response = await websocket.recv()
    price_data = json.loads(response)

    if "result" in price_data:
        return price_data["result"]["last_price"]
    else:
        print("Error retrieving BTC/USD price:", price_data)
        return 0

async def calculate_usd_quantity_from_btc(websocket):
    available_balance_btc = await get_available_balance_btc(websocket)
    btc_usd_price = await get_btc_usd_price(websocket)

    if available_balance_btc > 0 and btc_usd_price > 0:
        quantity_usd = available_balance_btc * btc_usd_price - 10  # Subtract $10 buffer
        return int(quantity_usd)  # Round down to nearest USD amount
    else:
        return 0

async def get_current_position(websocket):
    position_msg = {
        "jsonrpc": "2.0",
        "id": 4217,
        "method": "private/get_positions",
        "params": {
            "currency": "BTC",
            "kind": "future"
        }
    }
    await websocket.send(json.dumps(position_msg))
    response = await websocket.recv()
    response_json = json.loads(response)
    if response_json.get("result"):
        # Return the full position details
        return response_json["result"][0]
    return None

async def cancel_order(websocket, order_id):
    cancel_order_msg = {
        "jsonrpc": "2.0",
        "id": 4222,
        "method": "private/cancel",
        "params": {
            "order_id": order_id
        }
    }

    await websocket.send(json.dumps(cancel_order_msg))
    response = await websocket.recv()
    return json.loads(response)

async def place_limit_order(websocket, side, quantity, price, instrument_name=INSTRUMENT_NAME):
    instrument_details = await get_instrument_details(websocket, instrument_name)
    tick_size = instrument_details.get('tick_size', 0.5)
    price = round(price / tick_size) * tick_size

    order_data = {
        "jsonrpc": "2.0",
        "id": 4215,
        "method": f"private/{side}",
        "params": {
            "instrument_name": instrument_name,
            "amount": quantity,
            "type": "limit",
            "price": price,
            "post_only": True,
            "time_in_force": "good_til_cancelled",
            "reduce_only": False
        }
    }

    await websocket.send(json.dumps(order_data))
    response = await websocket.recv()
    response_json = json.loads(response)

    if "result" not in response_json:
        print(f"Error placing limit order: {response_json}")
        return None

    return response_json

async def get_instrument_details(websocket, instrument_name):
    details_request = {
        "jsonrpc": "2.0",
        "id": 4221,
        "method": "public/get_instrument",
        "params": {
            "instrument_name": instrument_name
        }
    }
    await websocket.send(json.dumps(details_request))
    response = await websocket.recv()
    details_data = json.loads(response)
    if "result" in details_data:
        return details_data["result"]
    else:
        print("Error retrieving instrument details:", details_data)
        return {}

async def handle_long_signal(websocket, quantity):
    logging.info("Handling long signal")
    current_position = await get_current_position(websocket)
    logging.debug(f"Current position: {current_position}")

    if current_position and current_position["direction"] == "buy":
        logging.info("Already in a long position. No action taken.")
        return  # Do nothing if already in a long position

    # Cancel all existing orders only if reversing from short to long
    if current_position and current_position["direction"] == "sell":
        logging.info("Closing existing short position")
        await cancel_all_orders(websocket)  # Cancel existing orders
        await monitor_and_update_order(websocket, "buy", abs(current_position["size"]))
        while await get_current_position_quantity(websocket) < 0:
            logging.debug("Waiting for short position to close...")
            await asyncio.sleep(1)

    logging.info("Opening new long position")
    execution_price = await monitor_and_update_order(websocket, "buy", quantity)

    if execution_price:
        logging.debug(f"Execution price for long position: {execution_price}")
        logging.info("Placing stop-loss and take-profit orders for long position")
        await place_take_profit_and_stop_loss_orders(websocket, execution_price, quantity,
                                                     "buy")  # Use "buy" for long position

async def handle_short_signal(websocket, quantity):
    logging.info("Handling short signal")
    current_position = await get_current_position(websocket)
    logging.debug(f"Current position: {current_position}")

    if current_position and current_position["direction"] == "sell":
        logging.info("Already in a short position. No action taken.")
        return  # Do nothing if already in a short position

    # Cancel all existing orders only if reversing from long to short
    if current_position and current_position["direction"] == "buy":
        logging.info("Closing existing long position")
        await cancel_all_orders(websocket)  # Cancel existing orders
        await monitor_and_update_order(websocket, "sell", abs(current_position["size"]))
        while await get_current_position_quantity(websocket) > 0:
            logging.debug("Waiting for long position to close...")
            await asyncio.sleep(1)

    logging.info("Opening new short position")
    execution_price = await monitor_and_update_order(websocket, "sell", quantity)

    if execution_price:
        logging.debug(f"Execution price for short position: {execution_price}")
        logging.info("Placing stop-loss and take-profit orders for short position")
        await place_take_profit_and_stop_loss_orders(websocket, execution_price, quantity,
                                                     "sell")  # Use "sell" for short position


def adjust_quantity_to_contract_size(quantity, contract_size):
    """
    Adjusts the quantity to the nearest lower multiple of the contract size.
    """
    return (quantity // contract_size) * contract_size

async def monitor_and_update_order(websocket, side, quantity):
    adjusted_quantity = adjust_quantity_to_contract_size(quantity, 10)  # Assuming contract size is 10
    remaining_quantity = adjusted_quantity
    last_order_id = None
    tolerance = 0.5
    start_time = time.time()
    execution_price = None

    while remaining_quantity > 0:
        order_book = await get_order_book(websocket)
        best_bid = order_book.get("best_bid_price", 0)
        best_ask = order_book.get("best_ask_price", 0)
        target_price = best_bid - (TICK_SIZE*2) if side == "buy" else best_ask + (TICK_SIZE*2)

        if last_order_id:
            order_details = await get_order_details(websocket, last_order_id)
            if order_details:
                current_order_price = order_details.get("price", 0)
                filled_amount = order_details.get("filled_amount", 0)
                if filled_amount >= remaining_quantity:
                    execution_price = current_order_price
                    remaining_quantity = 0
                    break

                if abs(current_order_price - target_price) > tolerance:
                    await cancel_order(websocket, last_order_id)
                    last_order_id = None

        if last_order_id is None:
            order_response = await place_limit_order(websocket, side, remaining_quantity, target_price)
            if order_response:
                last_order_id = order_response["result"]["order"]["order_id"]

        # Execute market order if timeout is reached
        if time.time() - start_time > TIME_LIMIT_SECONDS:
            await cancel_order(websocket, last_order_id)
            print(f"Time limit reached. Placing market order for remaining quantity: {remaining_quantity}")
            market_order_response = await place_market_order(websocket, side, remaining_quantity)

            # Check if market order was filled and get execution price
            if market_order_response:
                last_order_id = market_order_response["result"]["order"]["order_id"]
                while True:
                    order_details = await get_order_details(websocket, last_order_id)
                    if order_details and order_details["order_state"] == "filled":
                        execution_price = order_details.get("average_price", None)
                        remaining_quantity = 0
                        break
            break

        await asyncio.sleep(1)

    return execution_price  # Return execution price only if position is fully opened

async def place_market_order(websocket, side, quantity):
    order_data = {
        "jsonrpc": "2.0",
        "id": 4219,
        "method": f"private/{side}",
        "params": {
            "instrument_name": INSTRUMENT_NAME,
            "amount": quantity,
            "type": "market",
            "reduce_only": False
        }
    }

    await websocket.send(json.dumps(order_data))
    response = await websocket.recv()
    response_json = json.loads(response)

    if "result" not in response_json:
        print(f"Error placing market order: {response_json}")
        return None

    return response_json

async def place_trigger_order(websocket, side, quantity, trigger_price, limit_price, order_type="stop_limit", instrument_name=INSTRUMENT_NAME):
    """
    Places a stop-limit or take-profit order with a trigger price.

    Args:
    - websocket: The WebSocket connection.
    - side: "buy" or "sell".
    - quantity: The amount of the asset to be traded.
    - trigger_price: The price at which the limit order is triggered.
    - limit_price: The price at which the order will be placed once triggered.
    - order_type: "stop_limit" for stop loss, "take_limit" for take profit.
    - instrument_name: The instrument name (e.g., "BTC-PERPETUAL").

    Returns:
    - The order response from the exchange.
    """
    # Adjust the limit price to conform to the tick size
    instrument_details = await get_instrument_details(websocket, instrument_name)
    tick_size = instrument_details.get('tick_size', 0.5)  # Use 0.5 as a default tick size if not available
    limit_price = round(limit_price / tick_size) * tick_size

    order_data = {
        "jsonrpc": "2.0",
        "id": 4215,
        "method": f"private/{side}",
        "params": {
            "instrument_name": instrument_name,
            "amount": quantity,
            "type": order_type,
            "trigger_price": trigger_price,
            "price": limit_price,
            "trigger": "last_price",
            "reduce_only": True,
            "time_in_force": "good_til_cancelled"
        }
    }

    await websocket.send(json.dumps(order_data))
    response = await websocket.recv()
    response_json = json.loads(response)

    if "result" not in response_json:
        print(f"Error placing trigger order: {response_json}")
        return None

    return response_json

async def place_take_profit_and_stop_loss_orders(websocket, execution_price, quantity, side):
    """
    Place take profit and stop loss orders after position is fully opened.

    Args:
        websocket: WebSocket connection.
        execution_price: The price at which the position was opened.
        quantity: The total quantity of the position.
        side: "buy" for long position, "sell" for short position.
    """
    if side == "buy":  # Long position
        stop_loss_price = execution_price * (1 - STOP_LOSS_PERCENTAGE)  # 5% below execution price
        take_profit_price = execution_price * (1 + TAKE_PROFIT_PERCENTAGE)  # 5% above execution price
        stop_loss_order_side = "sell"  # Sell for stop-loss
        take_profit_order_side = "sell"  # Sell for take-profit
    else:  # Short position
        stop_loss_price = execution_price * (1 + STOP_LOSS_PERCENTAGE)  # 5% above execution price
        take_profit_price = execution_price * (1 - TAKE_PROFIT_PERCENTAGE)  # 5% below execution price
        stop_loss_order_side = "buy"  # Buy for stop-loss
        take_profit_order_side = "buy"  # Buy for take-profit

    # Place the stop loss order as a trigger order
    stop_loss_order = await place_trigger_order(
        websocket=websocket,
        side=stop_loss_order_side,
        quantity=quantity,
        trigger_price=stop_loss_price,
        limit_price=stop_loss_price,
        order_type="stop_limit"
    )

    if not stop_loss_order:
        print("Failed to place stop loss order.")

    # Place the take profit order as a trigger order
    take_profit_order = await place_trigger_order(
        websocket=websocket,
        side=take_profit_order_side,
        quantity=quantity,
        trigger_price=take_profit_price,
        limit_price=take_profit_price,
        order_type="take_limit"
    )

    if not take_profit_order:
        print("Failed to place take profit order.")

async def get_order_book(websocket, instrument_name=INSTRUMENT_NAME):
    order_book_msg = {
        "jsonrpc": "2.0",
        "id": 4217,
        "method": "public/get_order_book",
        "params": {
            "instrument_name": instrument_name
        }
    }

    await websocket.send(json.dumps(order_book_msg))
    response = await websocket.recv()
    order_book_data = json.loads(response)

    if "result" in order_book_data:
        return {
            "best_bid_price": order_book_data["result"].get("best_bid_price", None),
            "best_ask_price": order_book_data["result"].get("best_ask_price", None),
            "bids": order_book_data["result"].get("bids", []),
            "asks": order_book_data["result"].get("asks", [])
        }
    else:
        print("Error: Order book data not found in the response")
        return None

async def get_order_details(websocket, order_id):
    order_details_msg = {
        "jsonrpc": "2.0",
        "id": 4223,
        "method": "private/get_order_state",
        "params": {
            "order_id": order_id
        }
    }

    await websocket.send(json.dumps(order_details_msg))
    response = await websocket.recv()
    order_details_data = json.loads(response)

    if "result" in order_details_data:
        return order_details_data["result"]
    else:
        print("Error retrieving order details:", order_details_data)
        return None

async def get_current_position_quantity(websocket):
    position = await get_current_position(websocket)
    if position:
        return position.get("size", 0)
    return 0

async def cancel_all_orders(websocket):
    cancel_all_msg = {
        "jsonrpc": "2.0",
        "id": 4214,
        "method": "private/cancel_all",
        "params": {}
    }
    await websocket.send(json.dumps(cancel_all_msg))
    response = await websocket.recv()
    print("Cancel All Orders Response:", response)

async def execute_trade_logic(websocket, df):
    if df.empty:
        print("DataFrame is empty. No trading actions will be performed.")
        return

    try:
        quantity = await calculate_usd_quantity_from_btc(websocket)
        if quantity <= 0:
            print("Insufficient BTC balance to place an order.")
            return

        contract_size = 10
        quantity = adjust_quantity_to_contract_size(quantity, contract_size)
        if quantity <= 0:
            print("Calculated quantity is too small to place an order.")
            return

        current_position = await get_current_position(websocket)

        if df["Long_Entry"].iloc[0]:
            await handle_long_signal(websocket, quantity*2)
        elif df["Short_Entry"].iloc[0]:
            await handle_short_signal(websocket, quantity*4)
        else:
            print("No trading signal detected.")

        print(f"Current position: {current_position}, Latest signal: {'Long' if df['Long_Entry'].iloc[0] else 'Short' if df['Short_Entry'].iloc[0] else 'No Signal'}")

    except Exception as e:
        print(f"An error occurred: {e}")

async def call_api(df, api_key, api_secret):
    websocket_url = "wss://www.deribit.com/ws/api/v2"

    async with websockets.connect(websocket_url) as websocket:
        authenticated = await authenticate(api_key, api_secret, connection_type="websocket", websocket=websocket)

        if authenticated:
            await execute_trade_logic(websocket, df)
        else:
            print("WebSocket authentication failed.")