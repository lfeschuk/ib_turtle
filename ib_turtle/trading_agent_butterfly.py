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

# Timezone definitions
IST = pytz.timezone('Asia/Jerusalem')
EST = pytz.timezone('US/Eastern')

# ==============================================================================
# 0. MARKET HOURS & STATUS
# ==============================================================================
def get_us_market_status():
    now_ist = datetime.datetime.now(IST)
    now_est = now_ist.astimezone(EST)
    
    # 09:30 EST -> 16:30 IST | 16:00 EST -> 23:00 IST
    market_open_ist = now_ist.replace(hour=16, minute=30, second=0, microsecond=0)
    market_close_ist = now_ist.replace(hour=23, minute=0, second=0, microsecond=0)
    
    if now_est.weekday() >= 5: 
        return "🔴 CLOSED (Weekend)."
    if now_ist < market_open_ist:
        return f"🟡 CLOSED (Pre-Market). Current IST: {now_ist.strftime('%H:%M:%S')}"
    elif market_open_ist <= now_ist <= market_close_ist:
        return f"🟢 OPEN. 0 DTE SPX Butterfly Bot Active. Current IST: {now_ist.strftime('%H:%M:%S')}"
    else: 
        return "🔴 CLOSED (After-Hours)."

# ==============================================================================
# 1. STATE DATA ARCHITECTURE (DataManager)
# ==============================================================================
class DataManager:
    def __init__(self, db_name="spx_butterfly_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_state 
            (ticker TEXT PRIMARY KEY, current_side TEXT, virtual_capital REAL, center_strike REAL, credit_received REAL, qty INTEGER)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trade_log 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp_ist TEXT, ticker TEXT, action TEXT, center_strike REAL, credit REAL, pnl REAL DEFAULT 0.0)''')
        self.conn.commit()

        # Init Master Account balances
        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO bot_state VALUES ('MASTER_ACCOUNT', 'FLAT', 100000.0, 0.0, 0.0, 0)")
            self.conn.commit()

    def get_capital(self):
        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        return self.cursor.fetchone()[0]

    def get_position_state(self, ticker="SPX"):
        self.cursor.execute("SELECT current_side, center_strike, credit_received, qty FROM bot_state WHERE ticker=?", (ticker,))
        row = self.cursor.fetchone()
        if row:
            return {"side": row[0], "center_strike": row[1], "credit": row[2], "qty": row[3]}
        return {"side": "FLAT", "center_strike": 0.0, "credit": 0.0, "qty": 0}

    def update_position_state(self, ticker, side, center_strike, credit, qty):
        self.cursor.execute("INSERT OR REPLACE INTO bot_state (ticker, current_side, virtual_capital, center_strike, credit_received, qty) VALUES (?, ?, (SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'), ?, ?, ?)",
                            (ticker, side, center_strike, credit, qty))
        self.conn.commit()

    def log_transaction(self, ticker, action, center_strike, credit, qty, pnl=0.0):
        timestamp_ist = datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO trade_log (timestamp_ist, ticker, action, center_strike, credit, pnl) VALUES (?, ?, ?, ?, ?, ?)", 
                            (timestamp_ist, ticker, action, center_strike, credit, pnl))
        if pnl != 0.0:
            self.cursor.execute("UPDATE bot_state SET virtual_capital = virtual_capital + ? WHERE ticker='MASTER_ACCOUNT'", (pnl,))
        self.conn.commit()

    def print_visible_ledger(self):
        df = pd.read_sql_query("SELECT timestamp_ist, ticker, action, center_strike, credit, pnl FROM trade_log ORDER BY id DESC LIMIT 10", self.conn)
        print("\n" + "🦋" + "="*85 + "🦋")
        print(f"{'IST TIMESTAMP':<20} | {'ASSET':<6} | {'STRATEGY ACTION':<18} | {'CENTER STK':<10} | {'CREDIT':<7} | {'REALIZED PNL'}")
        print("-" * 91)
        if df.empty:
            print(f"{'NO COMBOS LOGGED YET. AWAITING 1:30 PM EST ENTRY WINDOW...':^91}")
        for _, row in df.iterrows():
            pnl_val = row['pnl']
            pnl_str = f"${pnl_val:+.2f}" if pnl_val != 0.0 else "-"
            print(f"{row['timestamp_ist']:<20} | {row['ticker']:<6} | {row['action']:<18} | {row['center_strike']:<10.1f} | {row['credit']:<7.2f} | {pnl_str}")
        print("="*89)

# ==============================================================================
# 2. OPTIONS EXECUTION INTERFACE (IBBroker)
# ==============================================================================
class IBBroker:
    def __init__(self, port=4002, client_id=30):
        self.ib = IB()
        self.port = port
        self.client_id = client_id

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', self.port, clientId=self.client_id)
            logger.info(f"🟢 SPX Option Agent online on port {self.port}. Client ID: {self.client_id}")
            
            # Detect if paper account or live account
            accounts = self.ib.managedAccounts()
            self.is_paper = any(acc.startswith('DU') for acc in accounts)
            
            if self.is_paper:
                logger.info("ℹ️ Paper Trading account detected. Requesting delayed market data (Type 3).")
                self.ib.reqMarketDataType(3)
            else:
                logger.info("ℹ️ Live Trading account detected. Requesting real-time market data (Type 1).")
                self.ib.reqMarketDataType(1)
                
            return True
        except Exception as e:
            logger.error(f"❌ Connection to TWS failed: {e}")
            return False

    def get_spx_price(self):
        contract = Index('SPX', 'CBOE')
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(1.5)
        price = ticker.last if not math.isnan(ticker.last) else ticker.close
        self.ib.cancelMktData(contract)
        return price
        
    def get_vix_price(self):
        contract = Index('VIX', 'CBOE')
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(1.5)
        price = ticker.last if not math.isnan(ticker.last) else ticker.close
        self.ib.cancelMktData(contract)
        return price

    def resolve_option_contract(self, strike, right, expiry_str):
        contract = Option(symbol='SPX', lastTradeDateOrContractMonth=expiry_str, strike=strike, right=right, exchange='CBOE', multiplier='100', currency='USD')
        qualified = self.ib.qualifyContracts(contract)
        if qualified:
            return qualified[0]
        return None

    def get_butterfly_premium(self, center_strike, wing_width=10):
        expiry_str = datetime.datetime.now(EST).strftime('%Y%m%d')
        
        c_short_call = self.resolve_option_contract(center_strike, 'C', expiry_str)
        c_short_put  = self.resolve_option_contract(center_strike, 'P', expiry_str)
        c_long_call  = self.resolve_option_contract(center_strike + wing_width, 'C', expiry_str)
        c_long_put   = self.resolve_option_contract(center_strike - wing_width, 'P', expiry_str)
        
        if not all([c_short_call, c_short_put, c_long_call, c_long_put]):
            logger.error("❌ Failed to qualify all 4 options legs for pricing.")
            return None
            
        tickers = self.ib.reqTickers(c_short_call, c_short_put, c_long_call, c_long_put)
        
        # Helper to get mid or last price of a contract safely
        def get_mid(t):
            bid = t.bid
            ask = t.ask
            if not math.isnan(bid) and not math.isnan(ask) and bid > 0 and ask > 0:
                return (bid + ask) / 2.0
            if not math.isnan(t.last) and t.last > 0:
                return t.last
            return t.close if not math.isnan(t.close) else None

        mid_prices = [get_mid(t) for t in tickers]
        
        # Cancel market data request updates
        for ticker in tickers:
            self.ib.cancelMktData(ticker.contract)
            
        if any(p is None for p in mid_prices):
            logger.warning("⚠️ Some option leg prices could not be resolved from current tick data.")
            return None
            
        short_call_p, short_put_p, long_call_p, long_put_p = mid_prices
        
        # Butterfly Premium Collected = (Shorts) - (Longs)
        butterfly_premium = (short_call_p + short_put_p) - (long_call_p + long_put_p)
        return butterfly_premium

    def execute_iron_butterfly(self, center_strike, wing_width=10, action='BUY', qty=1):
        """
        Executes an Iron Butterfly as a single multi-leg combo order.
        To SELL a butterfly (collect premium): Pass action='SELL'
        """
        expiry_str = datetime.datetime.now(EST).strftime('%Y%m%d')
        
        c_short_call = self.resolve_option_contract(center_strike, 'C', expiry_str)
        c_short_put  = self.resolve_option_contract(center_strike, 'P', expiry_str)
        c_long_call  = self.resolve_option_contract(center_strike + wing_width, 'C', expiry_str)
        c_long_put   = self.resolve_option_contract(center_strike - wing_width, 'P', expiry_str)
        
        if not all([c_short_call, c_short_put, c_long_call, c_long_put]):
            logger.error("❌ Failed to qualify all 4 options legs via IB server definitions.")
            return None

        legs = [
            ComboLeg(conId=c_long_put.conId, action='BUY', ratio=1),
            ComboLeg(conId=c_short_put.conId, action='SELL', ratio=1),
            ComboLeg(conId=c_short_call.conId, action='SELL', ratio=1),
            ComboLeg(conId=c_long_call.conId, action='BUY', ratio=1)
        ]
        
        combo_contract = Bag(symbol='SPX', exchange='CBOE', currency='USD', comboLegs=legs)
        
        order_action = 'SELL' if action == 'ENTRY_CREDIT' else 'BUY'
        order = MarketOrder(order_action, qty)
        
        trade = self.ib.placeOrder(combo_contract, order)
        self.ib.sleep(2.0)
        return trade

    def fetch_combo_execution_premium(self, trade):
        if not trade.fills:
            return 8.00  # Fallback estimate
        avg_price = sum(f.execution.price for f in trade.fills) / len(trade.fills)
        return abs(avg_price)

# ==============================================================================
# 3. RUNNER ORCHESTRATOR
# ==============================================================================
def run_live_bot():
    db = DataManager()
    
    # Try port 4002 (Paper Gateway) and fallback to 7497 (Paper TWS)
    port = 4002
    broker = IBBroker(port=port, client_id=30)
    
    if not broker.connect():
        # Fallback to TWS Paper Port
        port = 7497
        broker = IBBroker(port=port, client_id=30)
        if not broker.connect():
            logger.critical("❌ Could not connect to IBKR TWS or Gateway on ports 4002/7497.")
            return
            
    db.print_visible_ledger()
    logger.info(get_us_market_status())
    
    wing_width = 10
    trade_qty = 1               # Fixed 1 contract per trade
    max_vix_limit = 20.0        # Max VIX threshold
    
    # Track state daily
    last_eval_date = None
    max_premium_seen_today = 0.0
    skipped_today_logged = False
    entered_today = False

    while True:
        try:
            now_ist = datetime.datetime.now(IST)
            current_time_str = now_ist.strftime('%H:%M')
            today_str = now_ist.strftime('%Y-%m-%d')
            
            # Check market status
            is_weekend = now_ist.weekday() >= 5
            
            state = db.get_position_state("SPX")

            # Reset daily trackers when the day changes
            if last_eval_date != today_str:
                last_eval_date = today_str
                max_premium_seen_today = 0.0
                skipped_today_logged = False
                entered_today = False
                logger.info(f"🌅 New trading day initialized: {today_str}")

            # ------------------------------------------------------------------
            # ENTRY LOGIC BLOCK (Executes exactly at 1:30 PM EST / 20:30 IST)
            # ------------------------------------------------------------------
            if state["side"] == "FLAT" and not is_weekend:
                # Trigger at 20:30, or catch up if we are past 20:30 and before 22:00 IST (3:00 PM EST)
                if current_time_str == "20:30" or ("20:30" < current_time_str < "22:00"):
                    if not entered_today:
                        spx_price = broker.get_spx_price()
                        vix_price = broker.get_vix_price()
                        
                        if spx_price is not None and not math.isnan(spx_price) and vix_price is not None and not math.isnan(vix_price):
                            # VIX filter check
                            if vix_price <= max_vix_limit:
                                center_strike = round(spx_price / 5) * 5
                                premium = broker.get_butterfly_premium(center_strike, wing_width)
                                
                                if premium is not None:
                                    logger.info(f"👀 1:30 PM Entry Conditions: VIX={vix_price:.2f} (Pass) | SPX={spx_price:.2f} | Strike={center_strike} | Premium=${premium:.2f}")
                                    logger.info(f"🎯 TRIGGER: Entering trade for {trade_qty} contract(s)...")
                                    
                                    trade = broker.execute_iron_butterfly(center_strike=center_strike, wing_width=wing_width, action='ENTRY_CREDIT', qty=trade_qty)
                                    if trade:
                                        credit_filled = broker.fetch_combo_execution_premium(trade)
                                        db.log_transaction("SPX", "BUTTERFLY_ENTRY", center_strike, credit_filled, trade_qty)
                                        db.update_position_state("SPX", "ACTIVE", center_strike, credit_filled, trade_qty)
                                        entered_today = True
                                        db.print_visible_ledger()
                            else:
                                if not skipped_today_logged:
                                    logger.warning(f"🚫 VIX LIMIT FILTER: VIX is {vix_price:.2f} (above maximum {max_vix_limit:.2f} limit). Skipping today's trade.")
                                    skipped_today_logged = True
                                    entered_today = True  # Stop checking for the day
                                        
                # If time has passed 20:30 IST and we haven't entered or logged a skip today
                elif current_time_str > "20:30":
                    if not entered_today and not skipped_today_logged:
                        logger.warning("🚫 SKIP TRADE: 1:30 PM entry time has passed. Skipping trade execution for today.")
                        skipped_today_logged = True
            
            # ------------------------------------------------------------------
            # RISK MANAGEMENT & EXIT LOGIC BLOCK
            # ------------------------------------------------------------------
            elif state["side"] == "ACTIVE":
                target_strike = state["center_strike"]
                entry_credit = state["credit"]
                active_qty = state["qty"]
                
                # Emergency Time Cut-off (22:58 IST / 3:58 PM EST, 2 minutes before market close)
                if now_ist.hour == 22 and now_ist.minute >= 58:
                    logger.warning(f"⚠️ TIME-CUT REACHED ({current_time_str} IST). Closing position before market close...")
                    
                    broker.execute_iron_butterfly(center_strike=target_strike, wing_width=wing_width, action='EXIT_DEBIT', qty=active_qty)
                    
                    spx_price = broker.get_spx_price()
                    close_distance = abs(spx_price - target_strike) if spx_price else 10.0
                    
                    final_pnl = (entry_credit - min(wing_width, close_distance)) * 100 * active_qty
                    
                    db.log_transaction("SPX", "TIME_CUT_EXIT", target_strike, entry_credit, active_qty, pnl=final_pnl)
                    db.update_position_state("SPX", "FLAT", 0.0, 0.0, 0)
                    db.print_visible_ledger()

        except Exception as err:
            logger.error(f"Error inside primary automated loop cycle: {err}")

        # Sleep for 15 seconds to check time accurately
        time.sleep(15)

if __name__ == "__main__":
    run_live_bot()
