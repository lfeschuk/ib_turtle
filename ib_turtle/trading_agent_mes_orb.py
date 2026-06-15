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
# 1. STATE DATA ARCHITECTURE (DataManager)
# ==============================================================================
class DataManager:
    def __init__(self, db_name="mes_orb_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_state 
            (ticker TEXT PRIMARY KEY, current_side TEXT, range_high REAL, range_low REAL, entry_price REAL, stop_loss_price REAL, qty INTEGER)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trade_log 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp_ist TEXT, ticker TEXT, action TEXT, price REAL, qty INTEGER, pnl REAL DEFAULT 0.0)''')
        self.conn.commit()

        # Initialize State for MES if not exists
        self.cursor.execute("SELECT current_side FROM bot_state WHERE ticker='MES'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO bot_state VALUES ('MES', 'FLAT', 0.0, 0.0, 0.0, 0.0, 0)")
            self.conn.commit()

    def get_bot_state(self, ticker="MES"):
        self.cursor.execute("SELECT current_side, range_high, range_low, entry_price, stop_loss_price, qty FROM bot_state WHERE ticker=?", (ticker,))
        row = self.cursor.fetchone()
        if row:
            return {
                "side": row[0],
                "range_high": row[1],
                "range_low": row[2],
                "entry_price": row[3],
                "stop_loss_price": row[4],
                "qty": row[5]
            }
        return {"side": "FLAT", "range_high": 0.0, "range_low": 0.0, "entry_price": 0.0, "stop_loss_price": 0.0, "qty": 0}

    def update_bot_state(self, ticker, side, range_high, range_low, entry_price, stop_loss_price, qty):
        self.cursor.execute("INSERT OR REPLACE INTO bot_state (ticker, current_side, range_high, range_low, entry_price, stop_loss_price, qty) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (ticker, side, range_high, range_low, entry_price, stop_loss_price, qty))
        self.conn.commit()

    def log_transaction(self, ticker, action, price, qty, pnl=0.0):
        timestamp_ist = datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO trade_log (timestamp_ist, ticker, action, price, qty, pnl) VALUES (?, ?, ?, ?, ?, ?)", 
                            (timestamp_ist, ticker, action, price, qty, pnl))
        self.conn.commit()

    def print_visible_ledger(self):
        df = pd.read_sql_query("SELECT timestamp_ist, ticker, action, price, qty, pnl FROM trade_log ORDER BY id DESC LIMIT 10", self.conn)
        print("\n" + "🎯" + "="*85 + "🎯")
        print(f"{'IST TIMESTAMP':<20} | {'ASSET':<6} | {'STRATEGY ACTION':<18} | {'PRICE':<10} | {'QTY':<5} | {'REALIZED PNL'}")
        print("-" * 91)
        if df.empty:
            print(f"{'NO COMBOS LOGGED YET. AWAITING 11:30 AM EST ENTRY WINDOW...':^91}")
        for _, row in df.iterrows():
            pnl_val = row['pnl']
            pnl_str = f"${pnl_val:+.2f}" if pnl_val != 0.0 else "-"
            print(f"{row['timestamp_ist']:<20} | {row['ticker']:<6} | {row['action']:<18} | {row['price']:<10.2f} | {row['qty']:<5} | {pnl_str}")
        print("="*89)

# ==============================================================================
# 2. FUTURES EXECUTION INTERFACE (IBBroker)
# ==============================================================================
class IBBroker:
    def __init__(self, port=4002, client_id=40):
        self.ib = IB()
        self.port = port
        self.client_id = client_id
        self.active_contract = None

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', self.port, clientId=self.client_id)
            logger.info(f"🟢 MES Breakout Agent online on port {self.port}. Client ID: {self.client_id}")
            
            # Paper trading check
            accounts = self.ib.managedAccounts()
            self.is_paper = (self.port in [4002, 7497]) or any(acc.upper().startswith(('DU', 'DF')) for acc in accounts)
            if self.is_paper:
                self.ib.reqMarketDataType(3)
            else:
                self.ib.reqMarketDataType(1)
                
            self.resolve_mes_contract()
            return True
        except Exception as e:
            logger.error(f"❌ Connection to TWS failed: {e}")
            return False

    def resolve_mes_contract(self):
        # Resolve active front-month contract
        contract = Future('MES', multiplier='5', exchange='CME', currency='USD')
        details = self.ib.reqContractDetails(contract)
        if not details:
            logger.error("❌ Could not retrieve MES contract details.")
            return None
            
        now_str = datetime.datetime.now().strftime('%Y%m%d')
        valid_contracts = []
        for d in details:
            c = d.contract
            if c.lastTradeDateOrContractMonth >= now_str:
                valid_contracts.append(c)
                
        valid_contracts.sort(key=lambda x: x.lastTradeDateOrContractMonth)
        if valid_contracts:
            self.active_contract = valid_contracts[0]
            self.ib.qualifyContracts(self.active_contract)
            logger.info(f"🎯 Resolved active front-month MES Contract: {self.active_contract.localSymbol} (Expiry: {self.active_contract.lastTradeDateOrContractMonth})")
        else:
            logger.error("❌ No active MES contract found.")

    def get_vix_price(self):
        contract = Index('VIX', 'CBOE')
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(1.5)
        price = ticker.last if not math.isnan(ticker.last) else ticker.close
        self.ib.cancelMktData(contract)
        return price

    def get_2h_range(self):
        """Retrieves range high and low for MES from 9:30 AM to 11:30 AM EST"""
        if not self.active_contract:
            self.resolve_mes_contract()
            
        logger.info("📊 Requesting historical bars to calculate 2-hour range...")
        # Request historical 5-minute bars for the past 1 day
        bars = self.ib.reqHistoricalData(
            self.active_contract,
            endDateTime='',
            durationStr='1 D',
            barSizeSetting='5 mins',
            whatToShow='TRADES',
            useRTH=True
        )
        
        if not bars:
            logger.error("❌ Failed to retrieve historical bars for range calculation.")
            return None, None
            
        # Filter bars within the current day between 9:30 AM and 11:30 AM EST
        now_est = datetime.datetime.now(EST)
        start_range = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
        end_range = now_est.replace(hour=11, minute=30, second=0, microsecond=0)
        
        range_high = -999999.0
        range_low = 999999.0
        bars_count = 0
        
        for bar in bars:
            # bar.date is timezone-aware EST or local time depending on settings
            bar_date = bar.date
            if isinstance(bar_date, datetime.date) and not isinstance(bar_date, datetime.datetime):
                continue
                
            bar_est = bar_date.astimezone(EST)
            if start_range <= bar_est <= end_range:
                bars_count += 1
                if bar.high > range_high:
                    range_high = bar.high
                if bar.low < range_low:
                    range_low = bar.low
                    
        if bars_count == 0:
            logger.error("❌ No bars found in the 9:30 - 11:30 AM EST range. Check system time or connection.")
            return None, None
            
        logger.info(f"📊 Range calculated using {bars_count} bars: High={range_high:.2f} | Low={range_low:.2f}")
        return range_high, range_low

    def place_stop_order(self, action, stop_price, qty):
        order = Order()
        order.action = action
        order.orderType = 'STP'
        order.auxPrice = stop_price
        order.totalQuantity = qty
        order.transmit = True
        
        trade = self.ib.placeOrder(self.active_contract, order)
        self.ib.sleep(1.0)
        return trade

    def place_market_order(self, action, qty):
        order = MarketOrder(action, qty)
        trade = self.ib.placeOrder(self.active_contract, order)
        self.ib.sleep(1.0)
        return trade

    def cancel_all_active_orders(self):
        for order in self.ib.orders():
            if order.status in ['Submitted', 'PreSubmitted', 'Accepted']:
                self.ib.cancelOrder(order)
        self.ib.sleep(1.0)

# ==============================================================================
# 3. RUNNER ORCHESTRATOR
# ==============================================================================
def run_live_bot():
    db = DataManager()
    
    # Port configuration
    port = 4002
    broker = IBBroker(port=port, client_id=40)
    
    if not broker.connect():
        port = 7497
        broker = IBBroker(port=port, client_id=40)
        if not broker.connect():
            logger.critical("❌ Could not connect to IBKR TWS or Gateway on ports 4002/7497.")
            return
            
    db.print_visible_ledger()
    
    # Strategy Settings
    max_vix_limit = 20.0
    trade_qty = 1
    
    last_eval_date = None
    skipped_today = False
    range_established = False
    
    # Active orders pointers
    buy_stop_order = None
    sell_stop_order = None
    stop_loss_order = None

    while True:
        try:
            now_ist = datetime.datetime.now(IST)
            now_est = now_ist.astimezone(EST)
            current_time_str = now_ist.strftime('%H:%M')
            today_str = now_ist.strftime('%Y-%m-%d')
            
            is_weekend = now_est.weekday() >= 5
            
            # Reset daily trackers
            if last_eval_date != today_str:
                last_eval_date = today_str
                skipped_today = False
                range_established = False
                buy_stop_order = None
                sell_stop_order = None
                stop_loss_order = None
                logger.info(f"🌅 New trading day initialized: {today_str}")

            state = db.get_bot_state("MES")

            # ------------------------------------------------------------------
            # 1. RANGE ESTABLISHMENT & ORDER ENTRY (11:30 AM EST / 18:30 IST)
            # ------------------------------------------------------------------
            if state["side"] == "FLAT" and not is_weekend and not skipped_today:
                # Target time is exactly 11:30 AM EST (18:30 IST)
                if current_time_str == "18:30" and not range_established:
                    vix_price = broker.get_vix_price()
                    
                    if vix_price is not None and not math.isnan(vix_price):
                        if vix_price > max_vix_limit:
                            logger.info(f"🔥 VIX is {vix_price:.2f} (above {max_vix_limit:.2f}). Triggering 2h ORB setup...")
                            
                            range_high, range_low = broker.get_2h_range()
                            if range_high and range_low:
                                range_established = True
                                
                                # Place Entry Stop Orders
                                long_entry_price = range_high + 0.50
                                short_entry_price = range_low - 0.50
                                
                                logger.info(f"🛒 Placing OCO Entry Stop Orders: Buy Stop at {long_entry_price:.2f} | Sell Stop at {short_entry_price:.2f}")
                                
                                broker.cancel_all_active_orders()
                                buy_stop_order = broker.place_stop_order('BUY', long_entry_price, trade_qty)
                                sell_stop_order = broker.place_stop_order('SELL', short_entry_price, trade_qty)
                                
                                db.update_bot_state("MES", "PENDING_OCO", range_high, range_low, 0.0, 0.0, trade_qty)
                        else:
                            logger.warning(f"🚫 VIX is {vix_price:.2f} (below {max_vix_limit:.2f}). Skipping ORB strategy today.")
                            skipped_today = True
                            
                elif current_time_str > "18:35" and not range_established and state["side"] == "FLAT":
                    logger.warning("🚫 11:30 AM EST has passed and range was not established today. Sitting in cash.")
                    skipped_today = True

            # ------------------------------------------------------------------
            # 2. PENDING OCO MONITORING (Waiting for fill)
            # ------------------------------------------------------------------
            elif state["side"] == "PENDING_OCO":
                # Check if either stop order was filled
                broker.ib.update()
                
                long_filled = buy_stop_order and buy_stop_order.orderStatus.status == 'Filled'
                short_filled = sell_stop_order and sell_stop_order.orderStatus.status == 'Filled'
                
                if long_filled:
                    logger.info("🟢 LONG ENTRY FILLED! Cancelling short stop entry and setting Stop Loss...")
                    broker.cancel_all_active_orders()
                    
                    fill_price = buy_stop_order.orderStatus.avgFillPrice
                    stop_loss_price = state["range_low"]
                    
                    # Place Stop Loss at the low of the range
                    stop_loss_order = broker.place_stop_order('SELL', stop_loss_price, trade_qty)
                    
                    db.log_transaction("MES", "LONG_BREAKOUT_ENTRY", fill_price, trade_qty)
                    db.update_bot_state("MES", "ACTIVE_LONG", state["range_high"], state["range_low"], fill_price, stop_loss_price, trade_qty)
                    db.print_visible_ledger()
                    
                elif short_filled:
                    logger.info("🔴 SHORT ENTRY FILLED! Cancelling long stop entry and setting Stop Loss...")
                    broker.cancel_all_active_orders()
                    
                    fill_price = sell_stop_order.orderStatus.avgFillPrice
                    stop_loss_price = state["range_high"]
                    
                    # Place Stop Loss at the high of the range
                    stop_loss_order = broker.place_stop_order('BUY', stop_loss_price, trade_qty)
                    
                    db.log_transaction("MES", "SHORT_BREAKOUT_ENTRY", fill_price, trade_qty)
                    db.update_bot_state("MES", "ACTIVE_SHORT", state["range_high"], state["range_low"], fill_price, stop_loss_price, trade_qty)
                    db.print_visible_ledger()

            # ------------------------------------------------------------------
            # 3. RISK MANAGEMENT & TIME CLOSE
            # ------------------------------------------------------------------
            elif state["side"] in ["ACTIVE_LONG", "ACTIVE_SHORT"]:
                broker.ib.update()
                
                # A. Check Stop Loss execution
                stop_filled = stop_loss_order and stop_loss_order.orderStatus.status == 'Filled'
                if stop_filled:
                    logger.warning("💥 STOP LOSS TRIGGERED. Position closed.")
                    exit_price = stop_loss_order.orderStatus.avgFillPrice
                    
                    if state["side"] == "ACTIVE_LONG":
                        pnl = (exit_price - state["entry_price"]) * 5.0 * trade_qty
                    else:
                        pnl = (state["entry_price"] - exit_price) * 5.0 * trade_qty
                        
                    db.log_transaction("MES", "STOP_LOSS_EXIT", exit_price, trade_qty, pnl=pnl)
                    db.update_bot_state("MES", "FLAT", 0.0, 0.0, 0.0, 0.0, 0)
                    db.print_visible_ledger()
                
                # B. Time Exit Cut-off (3:58 PM EST / 22:58 IST)
                elif now_est.hour == 15 and now_est.minute >= 58:
                    logger.info("⚠️ TIME CUT-OFF REACHED. Closing position at market close...")
                    broker.cancel_all_active_orders()
                    
                    action = 'SELL' if state["side"] == "ACTIVE_LONG" else 'BUY'
                    trade = broker.place_market_order(action, trade_qty)
                    
                    exit_price = trade.orderStatus.avgFillPrice if trade.orderStatus.avgFillPrice > 0 else broker.active_contract.marketPrice()
                    
                    if state["side"] == "ACTIVE_LONG":
                        pnl = (exit_price - state["entry_price"]) * 5.0 * trade_qty
                    else:
                        pnl = (state["entry_price"] - exit_price) * 5.0 * trade_qty
                        
                    db.log_transaction("MES", "TIME_CUT_EXIT", exit_price, trade_qty, pnl=pnl)
                    db.update_bot_state("MES", "FLAT", 0.0, 0.0, 0.0, 0.0, 0)
                    db.print_visible_ledger()

        except Exception as err:
            logger.error(f"Error in automated loop cycle: {err}")

        time.sleep(15)

if __name__ == '__main__':
    run_live_bot()
