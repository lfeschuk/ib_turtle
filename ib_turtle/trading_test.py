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
logging.getLogger('ib_insync').setLevel(logging.WARNING)

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

def get_leg_mid_price(ib, contract):
    ticker = ib.reqMktData(contract, '', False, False)
    ib.sleep(2.0)
    bid = ticker.bid
    ask = ticker.ask
    ib.cancelMktData(contract)
    
    if not math.isnan(bid) and not math.isnan(ask) and bid > 0 and ask > 0:
        return round((bid + ask) / 2, 2)
        
    # Fallback to historical 1-minute bar midpoint
    bars = ib.reqHistoricalData(
        contract, endDateTime='', durationStr='600 S',
        barSizeSetting='1 min', whatToShow='MIDPOINT', useRTH=True
    )
    if bars:
        return round(bars[-1].close, 2)
    return 0.0

def calculate_combo_mid_price(ib, legs_with_contracts):
    net_mid = 0.0
    for leg, contract in legs_with_contracts:
        price = get_leg_mid_price(ib, contract)
        factor = 1.0 if leg.action.upper() == 'BUY' else -1.0
        logger.info(f"   Leg {contract.localSymbol}: {leg.action} (Ratio {leg.ratio}) | Est. Mid Price = {price}")
        net_mid += leg.ratio * factor * price
    return round(net_mid, 2)

def execute_iron_butterfly_limit(ib, center_strike, wing_width=10, action='ENTRY_CREDIT', qty=1):
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
    
    # Map legs to qualified contracts to calculate net mid price
    legs_map = [
        (legs[0], c_long_put),
        (legs[1], c_short_put),
        (legs[2], c_short_call),
        (legs[3], c_long_call)
    ]
    
    logger.info("Calculating Iron Butterfly Net Mid Price...")
    lmt_price = calculate_combo_mid_price(ib, legs_map)
    
    # If closing, we buy back the combo (reverse the sign)
    if action == 'CLOSE':
        # Closing is a BUY order. We pay the positive net debit.
        # But wait, if we calculated net SELL price, buying it back is the same value but positive.
        lmt_price = abs(lmt_price)
        
    bag = Bag(symbol='SPX', exchange='CBOE', currency='USD', comboLegs=legs)
    order_action = 'SELL' if action == 'ENTRY_CREDIT' else 'BUY'
    
    order = LimitOrder(order_action, qty, lmtPrice=lmt_price, tif='DAY')
    trade = ib.placeOrder(bag, order)
    
    logger.info(f"Submitting Iron Butterfly Limit Order: {order_action} {qty} combo @ Limit Price: {lmt_price}...")
    while not trade.isDone():
        ib.sleep(0.5)
    return trade

def execute_put_bwb_limit(ib, center_strike, upper_gap=10, lower_gap=20, action='ENTRY_CREDIT', qty=1):
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
    
    legs_map = [
        (legs[0], c_long_call),
        (legs[1], c_short_put),
        (legs[2], c_long_put)
    ]
    
    logger.info("Calculating Put BWB Net Mid Price...")
    lmt_price = calculate_combo_mid_price(ib, legs_map)
    
    if action == 'CLOSE':
        lmt_price = abs(lmt_price)
        
    bag = Bag(symbol='SPX', exchange='CBOE', currency='USD', comboLegs=legs)
    order_action = 'SELL' if action == 'ENTRY_CREDIT' else 'BUY'
    
    order = LimitOrder(order_action, qty, lmtPrice=lmt_price, tif='DAY')
    trade = ib.placeOrder(bag, order)
    
    logger.info(f"Submitting BWB Limit Order: {order_action} {qty} combo @ Limit Price: {lmt_price}...")
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

    logger.info(f"🟢 Connected to TWS on port {port}. Initializing Mid-Price Limit Order test...")
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
    logger.info("TEST 1: Executing 10-wide SPX Iron Butterfly (Limit Orders)...")
    logger.info("--------------------------------------------------")
    
    # Sell Combo at Mid Price
    entry_trade = execute_iron_butterfly_limit(ib, center_strike, wing_width=10, action='ENTRY_CREDIT', qty=1)
    if entry_trade and entry_trade.orderStatus.status == 'Filled':
        fill_price = entry_trade.orderStatus.avgFillPrice
        logger.info(f"✅ Iron Butterfly Entry FILLED! Average Fill Price: {fill_price:.2f}")
        
        logger.info("Sleeping 5 seconds before closing position...")
        ib.sleep(5.0)
        
        # Close Combo at Mid Price
        logger.info("Executing Close Limit Order (Buy back Combo)...")
        exit_trade = execute_iron_butterfly_limit(ib, center_strike, wing_width=10, action='CLOSE', qty=1)
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
    logger.info("TEST 2: Executing 10/20-wide SPX Put BWB (Limit Orders)...")
    logger.info("--------------------------------------------------")
    
    # Sell Combo at Mid Price
    entry_bwb = execute_put_bwb_limit(ib, center_strike, upper_gap=10, lower_gap=20, action='ENTRY_CREDIT', qty=1)
    if entry_bwb and entry_bwb.orderStatus.status == 'Filled':
        fill_price = entry_bwb.orderStatus.avgFillPrice
        logger.info(f"✅ BWB Entry FILLED! Average Fill Price: {fill_price:.2f}")
        
        logger.info("Sleeping 5 seconds before closing position...")
        ib.sleep(5.0)
        
        # Close Combo at Mid Price
        logger.info("Executing Close Limit Order (Buy back BWB)...")
        exit_bwb = execute_put_bwb_limit(ib, center_strike, upper_gap=10, lower_gap=20, action='CLOSE', qty=1)
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
