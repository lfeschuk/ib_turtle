import sqlite3
import pandas as pd
import numpy as np
import logging
import math
import datetime
import pytz
import time
from ib_insync import *

# --- SYSTEM SETTINGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('ib_insync').setLevel(logging.WARNING)

# Timezones
IST = pytz.timezone('Asia/Jerusalem')
EST = pytz.timezone('US/Eastern')

# ==============================================================================
# 1. STATE ARCHITECTURE (DataManager)
# ==============================================================================
class DataManager:
    def __init__(self, db_name="spx_bwb_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_state 
            (ticker TEXT PRIMARY KEY, current_side TEXT, entry_strike REAL, entry_credit REAL, qty INTEGER)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trade_log 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp_ist TEXT, ticker TEXT, action TEXT, strike REAL, price REAL, qty INTEGER, pnl REAL DEFAULT 0.0)''')
        self.conn.commit()

        # Initialize BWB state
        self.cursor.execute("SELECT current_side FROM bot_state WHERE ticker='SPX_BWB'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO bot_state VALUES ('SPX_BWB', 'FLAT', 0.0, 0.0, 0)")
            self.conn.commit()

    def get_position_state(self):
        self.cursor.execute("SELECT current_side, entry_strike, entry_credit, qty FROM bot_state WHERE ticker='SPX_BWB'")
        row = self.cursor.fetchone()
        if row:
            return {"side": row[0], "strike": row[1], "credit": row[2], "qty": row[3]}
        return {"side": "FLAT", "strike": 0.0, "credit": 0.0, "qty": 0}

    def update_position_state(self, side, strike, credit, qty):
        self.cursor.execute("INSERT OR REPLACE INTO bot_state (ticker, current_side, entry_strike, entry_credit, qty) VALUES ('SPX_BWB', ?, ?, ?, ?)",
                            (side, strike, credit, qty))
        self.conn.commit()

    def log_transaction(self, action, strike, price, qty, pnl=0.0):
        timestamp_ist = datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO trade_log (timestamp_ist, ticker, action, strike, price, qty, pnl) VALUES (?, 'SPX_BWB', ?, ?, ?, ?, ?)", 
                            (timestamp_ist, action, strike, price, qty, pnl))
        self.conn.commit()

    def print_visible_ledger(self):
        df = pd.read_sql_query("SELECT timestamp_ist, action, strike, price, qty, pnl FROM trade_log ORDER BY id DESC LIMIT 10", self.conn)
        print("\n" + "🍗" + "="*85 + "🍗")
        print(f"{'IST TIMESTAMP':<20} | {'ACTION':<22} | {'ATM STRIKE':<10} | {'PRICE':<8} | {'QTY':<4} | {'REALIZED PNL'}")
        print("-" * 91)
        if df.empty:
            print(f"{'NO TRANSACTIONS LOGGED YET. AWAITING 1:30 PM EST ENTRY WINDOW...':^91}")
        for _, row in df.iterrows():
            pnl_val = row['pnl']
            pnl_str = f"${pnl_val:+.2f}" if pnl_val != 0.0 else "-"
            print(f"{row['timestamp_ist']:<20} | {row['action']:<22} | {row['strike']:<10.1f} | {row['price']:<8.2f} | {row['qty']:<4} | {pnl_str}")
        print("="*89)

# ==============================================================================
# 2. OPTIONS EXECUTION INTERFACE (IBBroker)
# ==============================================================================
class IBBroker:
    def __init__(self, port=4002, client_id=60):
        self.ib = IB()
        self.port = port
        self.client_id = client_id

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', self.port, clientId=self.client_id)
            logger.info(f"🟢 SPX BWB Agent online on port {self.port}. Client ID: {self.client_id}")
            
            # Paper trading check
            accounts = self.ib.managedAccounts()
            is_paper = (self.port in [4002, 7497]) or any(acc.upper().startswith(('DU', 'DF')) for acc in accounts)
            if is_paper:
                self.ib.reqMarketDataType(3)
            else:
                self.ib.reqMarketDataType(1)
            return True
        except Exception as e:
            logger.error(f"❌ Connection to TWS failed: {e}")
            return False

    def get_index_price_yahoo(self, symbol):
        import urllib.request
        import json
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

    def get_index_price(self, symbol):
        contract = Index(symbol, 'CBOE')
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(2.0)
        price = ticker.last if not math.isnan(ticker.last) else ticker.close
        self.ib.cancelMktData(contract)
        
        if price is not None and not math.isnan(price):
            return price
            
        # Fallback 1: Yahoo Finance (instant, real-time, free)
        logger.info(f"Ticker price for {symbol} is NaN on TWS. Fetching from Yahoo Finance...")
        yahoo_price = self.get_index_price_yahoo(symbol)
        if yahoo_price is not None:
            return yahoo_price

        # Fallback 2: Historical 1-minute bar from TWS (fail-safe)
        logger.info(f"Yahoo Finance failed. Fetching latest historical bar from TWS...")
        bars = self.ib.reqHistoricalData(
            contract, endDateTime='', durationStr='600 S',
            barSizeSetting='1 min', whatToShow='MIDPOINT', useRTH=True
        )
        if bars:
            return bars[-1].close
        return None

    def get_leg_mid_price(self, contract):
        ticker = self.ib.reqMktData(contract, '', False, False)
        # Poll for up to 5 seconds to let the delayed/live feed load
        for _ in range(10):
            self.ib.sleep(0.5)
            if not math.isnan(ticker.bid) and not math.isnan(ticker.ask) and ticker.bid > 0 and ticker.ask > 0:
                break
        bid = ticker.bid
        ask = ticker.ask
        self.ib.cancelMktData(contract)
        
        if not math.isnan(bid) and not math.isnan(ask) and bid > 0 and ask > 0:
            return (bid + ask) / 2
        return None

    def resolve_option_contract(self, strike, right, expiry):
        contract = Option(symbol='SPX', lastTradeDateOrContractMonth=expiry, strike=strike, right=right, exchange='CBOE', multiplier='100', currency='USD')
        qualified = self.ib.qualifyContracts(contract)
        return qualified[0] if qualified else None

    def execute_put_bwb(self, center_strike, upper_gap=10, lower_gap=20, action='ENTRY_CREDIT', qty=1):
        expiry = datetime.datetime.now(EST).strftime('%Y%m%d')
        
        c_long_upper = self.resolve_option_contract(center_strike + upper_gap, 'P', expiry)
        c_short      = self.resolve_option_contract(center_strike, 'P', expiry)
        c_long_lower = self.resolve_option_contract(center_strike - lower_gap, 'P', expiry)
        
        if not all([c_long_upper, c_short, c_long_lower]):
            logger.error("❌ Failed to qualify all 3 Put BWB options legs.")
            return None
            
        # 1. Fetch mid-prices for each leg
        p_upper = self.get_leg_mid_price(c_long_upper)
        p_center = self.get_leg_mid_price(c_short)
        p_lower = self.get_leg_mid_price(c_long_lower)
        
        # Calculate net credit collected (2 * short_center - long_upper - long_lower)
        net_credit = None
        if all(p is not None for p in [p_upper, p_center, p_lower]):
            net_credit = round((2.0 * p_center) - p_upper - p_lower, 2)
            logger.info(f"   BWB Legs Mid: Upper={p_upper:.2f} | Center={p_center:.2f} | Lower={p_lower:.2f} | Calculated Net Credit={net_credit:.2f}")

        # Check entry rules
        if action == 'ENTRY_CREDIT':
            if net_credit is None:
                logger.error("❌ Aborting BWB Entry: Unable to fetch option leg bid/ask quotes.")
                return None
            if net_credit <= 0.00:
                logger.warning(f"🚫 BWB Entry aborted: Calculated net credit is negative/flat ({net_credit:.2f}). We require a net premium to enter.")
                return None
                
        legs = [
            ComboLeg(conId=c_long_lower.conId, action='BUY', ratio=1),
            ComboLeg(conId=c_short.conId, action='SELL', ratio=2),
            ComboLeg(conId=c_long_upper.conId, action='BUY', ratio=1)
        ]
        
        bag = Bag(symbol='SPX', exchange='CBOE', currency='USD', comboLegs=legs)
        order_action = 'BUY' if action == 'ENTRY_CREDIT' else 'SELL'
        
        if net_credit is not None:
            # Combo limit price is negative when buying a credit combo
            lmt_price = round(p_lower - 2.0 * p_center + p_upper, 2)
            order = LimitOrder(order_action, qty, lmtPrice=lmt_price, tif='DAY')
            logger.info(f"Submitting BWB Limit Order: {order_action} {qty} combo @ Limit Price: {lmt_price} (Est Credit: {abs(lmt_price):.2f})...")
        else:
            # Closing fallback to Market Order if pricing fails
            order = MarketOrder(order_action, qty, tif='DAY')
            logger.warning(f"⚠️ Close BWB pricing failed. Falling back to Market Order to ensure flat exit.")
            
        trade = self.ib.placeOrder(bag, order)
        # Wait until order is filled / completed
        while not trade.isDone():
            self.ib.sleep(0.5)
        return trade

# ==============================================================================
# 3. RUNNER LOOP
# ==============================================================================
def run_live_bwb_bot():
    db = DataManager()
    
    port = 4002
    broker = IBBroker(port=port, client_id=60)
    if not broker.connect():
        port = 7497
        broker = IBBroker(port=port, client_id=60)
        if not broker.connect():
            logger.critical("❌ Could not connect to IBKR TWS/Gateway on ports 4002/7497.")
            return
            
    db.print_visible_ledger()
    
    max_vix_limit = 20.0
    trade_qty = 1
    upper_g = 10
    lower_g = 15
    
    last_eval_date = None
    entered_today = False
    skipped_today = False

    while True:
        try:
            now_ist = datetime.datetime.now(IST)
            now_est = now_ist.astimezone(EST)
            current_time_str = now_ist.strftime('%H:%M')
            today_str = now_ist.strftime('%Y-%m-%d')
            
            is_weekend = now_est.weekday() >= 5
            
            state = db.get_position_state()

            # Reset daily trackers
            if last_eval_date != today_str:
                last_eval_date = today_str
                entered_today = False
                skipped_today = False
                logger.info(f"🌅 New BWB trading day initialized: {today_str}")

            # ------------------------------------------------------------------
            # ENTRY BLOCK (Executes exactly at 1:30 PM EST / 20:30 IST)
            # ------------------------------------------------------------------
            if state["side"] == "FLAT" and not is_weekend and not skipped_today:
                # Trigger at 20:30 IST, or catch up if bot started late during the afternoon (before 21:00 IST)
                if current_time_str == "20:30" or ("20:30" < current_time_str < "21:00"):
                    if not entered_today:
                        vix = broker.get_index_price("VIX")
                        if vix is not None and not math.isnan(vix):
                            if vix <= max_vix_limit:
                                spx = broker.get_index_price("SPX")
                                if spx is not None and not math.isnan(spx):
                                    center_strike = round(spx / 5) * 5
                                    logger.info(f"🎯 1:30 PM BWB Entry: VIX={vix:.2f} | SPX={spx:.2f} | ATM Strike={center_strike}")
                                    
                                    trade = broker.execute_put_bwb(center_strike, upper_g, lower_g, 'ENTRY_CREDIT', trade_qty)
                                    if trade is not None and trade.orderStatus.status == 'Filled':
                                        credit = abs(trade.orderStatus.avgFillPrice)
                                        db.log_transaction("ENTRY_CREDIT", center_strike, credit, trade_qty)
                                        db.update_position_state("ACTIVE", center_strike, credit, trade_qty)
                                        entered_today = True
                                        db.print_visible_ledger()
                                    else:
                                        logger.warning("🚫 Put BWB Entry did not execute or fill (credit threshold not met or quoting failed). Skipping entry for today.")
                                        skipped_today = True
                                else:
                                    logger.warning("⚠️ SPX price query returned NaN or None. Retrying on next tick...")
                            else:
                                logger.warning(f"🚫 VIX is {vix:.2f} (above {max_vix_limit:.2f}). Skipping BWB entry today.")
                                skipped_today = True
                        else:
                            logger.warning("⚠️ VIX price query returned NaN or None. Retrying on next tick...")

            # ------------------------------------------------------------------
            # EXIT BLOCK (Executes exactly at 3:58 PM EST / 22:58 IST)
            # ------------------------------------------------------------------
            if state["side"] == "ACTIVE":
                if now_est.hour == 15 and now_est.minute >= 58:
                    logger.info("⚠️ TIME CUT-OFF REACHED. Closing Put BWB position at market...")
                    
                    trade = broker.execute_put_bwb(state["strike"], upper_g, lower_g, 'CLOSE', trade_qty)
                    exit_price = abs(trade.orderStatus.avgFillPrice) if trade and trade.fills else 0.0
                    
                    # PnL = Entry Credit - Exit Cost
                    # Note: Since the combo is priced negatively (credit), at expiration/close the exit debit is positive.
                    # PnL = (Entry Credit - Exit Debit) * 100
                    pnl = (state["credit"] - exit_price) * 100.0 * trade_qty
                    
                    db.log_transaction("TIME_CUT_EXIT", state["strike"], exit_price, trade_qty, pnl=pnl)
                    db.update_position_state("FLAT", 0.0, 0.0, 0)
                    db.print_visible_ledger()

        except Exception as err:
            logger.error(f"Error in BWB loop cycle: {err}")

        time.sleep(15)

if __name__ == '__main__':
    run_live_bwb_bot()
