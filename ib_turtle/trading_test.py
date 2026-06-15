import urllib.request
import json
import logging
import math
import datetime
import pytz
from ib_insync import *

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

EST = pytz.timezone('US/Eastern')

def get_index_price_yahoo(symbol):
    yahoo_symbol = "^VIX" if symbol == "VIX" else "^GSPC"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1m&range=1d"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            meta = data['chart']['result'][0]['meta']
            price = meta.get('regularMarketPrice')
            if price is not None:
                return float(price)
    except Exception as e:
        logger.error(f"Error fetching index price from Yahoo Finance for {symbol}: {e}")
    return None

def resolve_option_contract(ib, strike, right, expiry):
    contract = Option(
        symbol='SPX',
        lastTradeDateOrContractMonth=expiry,
        strike=strike,
        right=right,
        exchange='CBOE',
        multiplier='100',
        currency='USD'
    )
    qualified = ib.qualifyContracts(contract)
    return qualified[0] if qualified else None

def execute_iron_butterfly(ib, center_strike, wing_width=10, action='ENTRY_CREDIT', qty=1):
    expiry = datetime.datetime.now(EST).strftime('%Y%m%d')
    c_short_call = resolve_option_contract(ib, center_strike, 'C', expiry)
    c_short_put  = resolve_option_contract(ib, center_strike, 'P', expiry)
    c_long_call  = resolve_option_contract(ib, center_strike + wing_width, 'C', expiry)
    c_long_put   = resolve_option_contract(ib, center_strike - wing_width, 'P', expiry)
    
    if not all([c_short_call, c_short_put, c_long_call, c_long_put]):
        logger.error("❌ Failed to qualify all 4 SPX options legs.")
        return None
        
    legs = [
        ComboLeg(conId=c_long_put.conId, action='BUY', ratio=1),
        ComboLeg(conId=c_short_put.conId, action='SELL', ratio=1),
        ComboLeg(conId=c_short_call.conId, action='SELL', ratio=1),
        ComboLeg(conId=c_long_call.conId, action='BUY', ratio=1)
    ]
    bag = Bag(symbol='SPX', exchange='CBOE', currency='USD', comboLegs=legs)
    order_action = 'SELL' if action == 'ENTRY_CREDIT' else 'BUY'
    order = MarketOrder(order_action, qty)
    trade = ib.placeOrder(bag, order)
    
    logger.info(f"Submitting Iron Butterfly Order: {order_action} {qty} combo...")
    while not trade.isDone():
        ib.sleep(0.5)
    return trade

def execute_put_bwb(ib, center_strike, upper_gap=10, lower_gap=20, action='ENTRY_CREDIT', qty=1):
    expiry = datetime.datetime.now(EST).strftime('%Y%m%d')
    c_long_call = resolve_option_contract(ib, center_strike + upper_gap, 'P', expiry)
    c_short_put = resolve_option_contract(ib, center_strike, 'P', expiry)
    c_long_put  = resolve_option_contract(ib, center_strike - lower_gap, 'P', expiry)
    
    if not all([c_long_call, c_short_put, c_long_put]):
        logger.error("❌ Failed to qualify all 3 BWB options legs.")
        return None
        
    legs = [
        ComboLeg(conId=c_long_call.conId, action='BUY', ratio=1),
        ComboLeg(conId=c_short_put.conId, action='SELL', ratio=2),
        ComboLeg(conId=c_long_put.conId, action='BUY', ratio=1)
    ]
    bag = Bag(symbol='SPX', exchange='CBOE', currency='USD', comboLegs=legs)
    order_action = 'SELL' if action == 'ENTRY_CREDIT' else 'BUY'
    order = MarketOrder(order_action, qty)
    trade = ib.placeOrder(bag, order)
    
    logger.info(f"Submitting BWB Order: {order_action} {qty} combo...")
    while not trade.isDone():
        ib.sleep(0.5)
    return trade

def main():
    ib = IB()
    port = 4002
    try:
        ib.connect('127.0.0.1', port, clientId=97)
    except:
        port = 7497
        try:
            ib.connect('127.0.0.1', port, clientId=97)
        except Exception as e:
            logger.critical(f"Could not connect to TWS on port 4002/7497: {e}")
            return

    logger.info(f"🟢 Connected to TWS on port {port}. Initializing test execution...")
    ib.reqMarketDataType(3)  # Use delayed data

    # 1. Fetch SPX price
    spx = get_index_price_yahoo("SPX")
    if spx is None:
        logger.error("❌ Could not retrieve SPX price. Aborting test.")
        ib.disconnect()
        return
    center_strike = round(spx / 5) * 5
    logger.info(f"📊 Market Spot SPX: {spx:.2f} | Rounded ATM Strike: {center_strike}")

    # ==============================================================================
    # TEST 1: IRON BUTTERFLY ENTRY AND EXIT
    # ==============================================================================
    logger.info("--------------------------------------------------")
    logger.info("TEST 1: Executing 10-wide SPX Iron Butterfly...")
    logger.info("--------------------------------------------------")
    
    # Sell Combo
    entry_trade = execute_iron_butterfly(ib, center_strike, wing_width=10, action='ENTRY_CREDIT', qty=1)
    if entry_trade and entry_trade.orderStatus.status == 'Filled':
        fill_price = entry_trade.orderStatus.avgFillPrice
        logger.info(f"✅ Iron Butterfly Entry FILLED! Average Fill Price: {fill_price:.2f} (Credit collected)")
        
        logger.info("Sleeping 5 seconds before closing position...")
        ib.sleep(5.0)
        
        # Close Combo
        logger.info("Executing Close Order (Buy back Combo)...")
        exit_trade = execute_iron_butterfly(ib, center_strike, wing_width=10, action='CLOSE', qty=1)
        if exit_trade and exit_trade.orderStatus.status == 'Filled':
            exit_price = exit_trade.orderStatus.avgFillPrice
            logger.info(f"✅ Iron Butterfly Exit FILLED! Average Fill Price: {exit_price:.2f}")
            pnl = fill_price - exit_price
            logger.info(f"📊 Net PnL on Butterfly Test: {pnl * 100:.2f} USD")
        else:
            logger.error("❌ Iron Butterfly Exit failed or did not fill.")
    else:
        logger.error("❌ Iron Butterfly Entry failed or did not fill.")

    # ==============================================================================
    # TEST 2: BROKEN WING BUTTERFLY (BWB) ENTRY AND EXIT
    # ==============================================================================
    logger.info("--------------------------------------------------")
    logger.info("TEST 2: Executing 10/20-wide SPX Put BWB...")
    logger.info("--------------------------------------------------")
    
    # Sell Combo
    entry_bwb = execute_put_bwb(ib, center_strike, upper_gap=10, lower_gap=20, action='ENTRY_CREDIT', qty=1)
    if entry_bwb and entry_bwb.orderStatus.status == 'Filled':
        fill_price = entry_bwb.orderStatus.avgFillPrice
        logger.info(f"✅ BWB Entry FILLED! Average Fill Price: {fill_price:.2f} (Credit collected)")
        
        logger.info("Sleeping 5 seconds before closing position...")
        ib.sleep(5.0)
        
        # Close Combo
        logger.info("Executing Close Order (Buy back BWB)...")
        exit_bwb = execute_put_bwb(ib, center_strike, upper_gap=10, lower_gap=20, action='CLOSE', qty=1)
        if exit_bwb and exit_bwb.orderStatus.status == 'Filled':
            exit_price = exit_bwb.orderStatus.avgFillPrice
            logger.info(f"✅ BWB Exit FILLED! Average Fill Price: {exit_price:.2f}")
            pnl = fill_price - exit_price
            logger.info(f"📊 Net PnL on BWB Test: {pnl * 100:.2f} USD")
        else:
            logger.error("❌ BWB Exit failed or did not fill.")
    else:
        logger.error("❌ BWB Entry failed or did not fill.")

    ib.disconnect()
    logger.info("Execution test completed.")

if __name__ == '__main__':
    main()
