import pandas as pd
import requests
import asyncio
import nest_asyncio
from bigquery_utils.bq_utils import read_data
from gcp_utils.secret_manager import GCPManager
from deribit_utils.deribit_utils import (authenticate,get_available_balance_btc
    ,get_btc_usd_price,calculate_usd_quantity_from_btc
    ,get_current_position,cancel_order,place_limit_order
    ,get_instrument_details,handle_long_signal,handle_short_signal
    ,adjust_quantity_to_contract_size,monitor_and_update_order,place_market_order
    ,place_trigger_order,place_take_profit_and_stop_loss_orders,get_order_book
    ,get_order_details,get_current_position_quantity,cancel_all_orders
    ,execute_trade_logic,call_api
)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Create an instance of the GCPManager with the project ID where secrets are located
project_id_secret = "abracadata-316418"  # Replace with the actual project ID for secrets
gcp_manager = GCPManager(project_id=project_id_secret)

# Access the secrets
api_key = gcp_manager.access_secret_version(secret_id="BtcRider-api-key")
api_secret = gcp_manager.access_secret_version(secret_id="BtcRider-api-secret")

# Others trading parameters
cl_ord_id = "b14"
instrument_name = "BTC-PERPETUAL"

def deribit_trading_btc_perpetual_ao_signal(event, context):
    """
    Main GCP Functions entrypoint.
    """
    print("Starting Deribit Strategy Execution...")

    # Construct the BigQuery query
    query_string = """
        SELECT DISTINCT
            *
        FROM `signals-etl.btc_perpetual_binance.master_signals_ao_1h` kline
        ORDER BY open_time ASC
        LIMIT 1
    """

    # Retrieve and process data
    df = read_data(query_string)

    # Run the WebSocket event loop and execute the trading logic
    asyncio.run(call_api(df, api_key, api_secret))

    return "Function executed successfully", 200
