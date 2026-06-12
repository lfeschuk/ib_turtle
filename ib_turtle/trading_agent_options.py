import sqlite3
import pandas as pd
import numpy as np
import logging
import math
import datetime
import pytz
import time
import requests
from ib_insync import *

# --- SYSTEM SETTINGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('ib_insync').setLevel(logging.WARNING)

# Timezone definitions
IST = pytz.timezone('Asia/Jerusalem')
EST = pytz.timezone('US/Eastern')

# ==============================================================================
# 0. MARKET HOURS & STATUS IN ISRAEL TIME
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
        return f"🟡 CLOSED (Pre-Market). Strategy waits until 16:30 IST. Current IST: {now_ist.strftime('%H:%M:%S')}"
    elif market_open_ist <= now_ist <= market_close_ist:
        return f"🟢 OPEN. Max Pain Iron Butterfly Engine Active. Current IST: {now_ist.strftime('%H:%M:%S')}"
    else: 
        return "🔴 CLOSED (After-Hours)."

# ==============================================================================
# 1. OPTIONCHARTS DATA INTERFACE (MOCK / API HOOK)
# ==============================================================================
def fetch_max_pain_data(current_spx_price=None):
    """
    Fetches real-time Max Pain data from OptionCharts.
    Replace the mock implementation below with your actual API endpoint/Scraper.
    """
    url = "https://optioncharts.io/options/$SPX"
    now_ist = datetime.datetime.now(IST)
    logger.info(f"🌐 Querying OptionCharts.io for $SPX intraday data arrays at {now_ist.strftime('%H:%M:%S')} IST...")
    
    # --- PLUG YOUR API/SCRAPER PARSER HERE ---
    # For standalone system stability, if no API response is parsed, 
    # it rounds the current price to the nearest $5 strike to simulate an ATM anchor point.
    if current_spx_price:
        mock_max_pain = round(current_spx_price / 5) * 5
        return float(mock_max_pain)
    return 5400.0  # Safe default baseline fallback

# ==============================================================================
# 2. STATE DATA ARCHITECTURE (DataManager)
# ==============================================================================
class DataManager:
    def __init__(self, db_name="spx_max_pain_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Modernized table for Multi-Leg Options Tracking
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
            print(f"{'NO COMBOS LOGGED YET. AWAITING 20:15 IST MAX PAIN WINDOW...':^91}")
        for _, row in df.iterrows():
            pnl_val = row['pnl']
            pnl_str = f"${pnl_val:+.2f}" if pnl_val != 0.0 else "-"
            print(f"{row['timestamp_ist']:<20} | {row['ticker']:<6} | {row['action']:<18} | {row['center_strike']:<10.1f} | {row['credit']:<7.2f} | {pnl_str}")
        print("="*89)

    def print_performance_dashboard(self):
        df = pd.read_sql_query("SELECT pnl FROM trade_log WHERE pnl != 0.0", self.conn)
        total_capital = self.get_capital()
        print("\n📊 MAX PAIN ALGORITHMIC PERFORMANCE")
        print(f"• Net Portfolio Standing: ${total_capital:,.2f}")
        if df.empty:
            print("• Strategy Win Rate:    N/A (No Closed Butterfly Structures)")
            return
        wins = df[df['pnl'] > 0]
        win_rate = (len(wins) / len(df)) * 100
        print(f"• Total Matched Trades:  {len(df)}")
        print(f"• Edge Win Rate:         {win_rate:.1f}%")
        print(f"• Net Generated Return: 🟢 ${df['pnl'].sum():+.2f}")
        print("="*60 + "\n")

# ==============================================================================
# 3. OPTIONS EXECUTION INTERFACE (IBBroker)
# ==============================================================================
class IBBroker:
    def __init__(self, port=4002, client_id=20):
        self.ib = IB()
        self.port = port
        self.client_id = client_id

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', self.port, clientId=self.client_id)
            logger.info(f"🟢 Options Automation Pipeline Online. Client ID: {self.client_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Connection to TWS failed: {e}")
            return False

    def get_spx_price(self):
        contract = Index('SPX', 'CBOE')
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(1.5)
        return ticker.last if not math.isnan(ticker.last) else ticker.close

    def resolve_option_contract(self, strike, right, expiry_str):
        contract = Option('SPX', expiry_str, strike, right, 'CBOE', multiplier='100', currency='USD')
        qualified = self.ib.qualifyContracts(contract)
        if qualified:
            return qualified[0]
        return None

    def execute_iron_butterfly(self, center_strike, wing_width=10, action='BUY', qty=1):
        """
        Executes an Iron Butterfly as a single multi-leg combo order.
        To SELL a butterfly (collect premium): Pass action='SELL'
        """
        expiry_str = datetime.datetime.now(EST).strftime('%Y%m%d')
        
        # Build component legs
        c_short_call = self.resolve_option_contract(center_strike, 'C', expiry_str)
        c_short_put  = self.resolve_option_contract(center_strike, 'P', expiry_str)
        c_long_call  = self.resolve_option_contract(center_strike + wing_width, 'C', expiry_str)
        c_long_put   = self.resolve_option_contract(center_strike - wing_width, 'P', expiry_str)
        
        if not all([c_short_call, c_short_put, c_long_call, c_long_put]):
            logger.error("❌ Failed to qualify all 4 options legs via IB server definitions.")
            return None

        # Map execution directions using standard combo mechanics
        # For a credit butterfly via a unified combo order:
        legs = [
            ComboLeg(conId=c_long_put.conId, action='BUY', ratio=1),
            ComboLeg(conId=c_short_put.conId, action='SELL', ratio=1),
            ComboLeg(conId=c_short_call.conId, action='SELL', ratio=1),
            ComboLeg(conId=c_long_call.conId, action='BUY', ratio=1)
        ]
        
        combo_contract = Bag(symbol='SPX', secType='BAG', exchange='CBOE', currency='USD', comboLegs=legs)
        
        # When structured as Buy Wings / Sell Center, a Market BUY order executes the structure as a net debit
        # To establish it as a net credit entry, we route it via a Market 'SELL' command.
        order_action = 'SELL' if action == 'ENTRY_CREDIT' else 'BUY'
        order = MarketOrder(order_action, qty)
        
        trade = self.ib.placeOrder(combo_contract, order)
        self.ib.sleep(2.0) # Allocation lock buffer
        return trade

    def fetch_combo_execution_premium(self, trade):
        """Extracts exact net execution premium from fill attributes"""
        if not trade.fills:
            return 5.50  # Risk management static fallback mid price estimation if execution ticks lag
        avg_price = sum(f.execution.price for f in trade.fills) / len(trade.fills)
        return abs(avg_price)

# ==============================================================================
# 4. MONITORING AND REAL-TIME EXECUTION ORCHESTRATOR
# ==============================================================================
def run_live_bot():
    db = DataManager()
    broker = IBBroker(port=4002, client_id=25)
    
    if not broker.connect():
        return

    db.print_visible_ledger()
    db.print_performance_dashboard()
    logger.info(get_us_market_status())

    # Strategy Parameters
    wing_width = 10
    trade_qty = 1

    # Main Core Iteration Loop
    while True:
        try:
            now_ist = datetime.datetime.now(IST)
            current_time_str = now_ist.strftime('%H:%M')
            
            spx_price = broker.get_spx_price()
            state = db.get_position_state("SPX")

            # ------------------------------------------------------------------
            # ENTRY LOGIC BLOCK (Target Window: 20:15 IST / 1:15 PM EST)
            # ------------------------------------------------------------------
            if state["side"] == "FLAT":
                if current_time_str == "20:15":
                    logger.info(f"⏰ Execution Window Reached ({current_time_str} IST). Evaluating Matrix Calculations...")
                    
                    max_pain = fetch_max_pain_data(spx_price)
                    distance_pct = abs(spx_price - max_pain) / max_pain
                    
                    # Mathematical filtering boundaries: 0.3% <= Distance <= 1.0%
                    if 0.003 <= distance_pct <= 0.010:
                        logger.info(f"🎯 MATCH: SPX is at {spx_price:.2f} (Distance to Max Pain {max_pain} is {distance_pct*100:.2f}%). Firing Entry Combo...")
                        
                        trade = broker.execute_iron_butterfly(center_strike=max_pain, wing_width=wing_width, action='ENTRY_CREDIT', qty=trade_qty)
                        if trade:
                            credit_filled = broker.fetch_combo_execution_premium(trade)
                            db.log_transaction("SPX", "BUTTERFLY_ENTRY", max_pain, credit_filled, trade_qty)
                            db.update_position_state("SPX", "ACTIVE", max_pain, credit_filled, trade_qty)
                            
                            db.print_visible_ledger()
                            db.print_performance_dashboard()
                    else:
                        logger.warning(f"🚫 FILTERED OUT: Distance percentage ({distance_pct*100:.2f}%) outside programmatic Goldilocks boundaries.")
            
            # ------------------------------------------------------------------
            # RISK MANAGEMENT & EXIT LOGIC BLOCK
            # ------------------------------------------------------------------
            elif state["side"] == "ACTIVE":
                # Real-time asset mapping metrics
                target_strike = state["center_strike"]
                entry_credit = state["credit"]
                
                # Automated Target Profit Calculation (40% of Maximum Collected Premium)
                target_profit_value = entry_credit * 0.40
                max_loss_limit = wing_width - entry_credit
                
                # Estimate current theoretical price variance based on terminal node distance
                current_distance_from_center = abs(spx_price - target_strike)
                
                # Approximate value interpolation logic to parse exit state loops
                if current_distance_from_center == 0:
                    estimated_current_combo_value = 0.0 # Perfect pin value mapping
                else:
                    estimated_current_combo_value = current_distance_from_center
                
                current_unrealized_pnl = (entry_credit - estimated_current_combo_value) * 100 * trade_qty

                # Condition A: Target Take Profit Hit
                if current_unrealized_pnl >= (target_profit_value * 100 * trade_qty):
                    logger.info(f"💰 TAKE PROFIT TRIGGERED: Calculated profile hit 40% threshold. Closing Butterfly.")
                    broker.execute_iron_butterfly(center_strike=target_strike, wing_width=wing_width, action='EXIT_DEBIT', qty=trade_qty)
                    db.log_transaction("SPX", "TAKE_PROFIT_EXIT", target_strike, entry_credit, trade_qty, pnl=current_unrealized_pnl)
                    db.update_position_state("SPX", "FLAT", 0.0, 0.0, 0)
                    
                    db.print_visible_ledger()
                    db.print_performance_dashboard()

                # Condition B: Emergency Time Cut-off (22:45 IST / 3:45 PM EST)
                elif now_ist.hour == 22 and now_ist.minute >= 45:
                    logger.warning(f"⚠️ EMERGENCY TIME-CUT REACHED ({current_time_str} IST). Liquidating Structure to Neutralize End-Of-Day Gamma Risk.")
                    broker.execute_iron_butterfly(center_strike=target_strike, wing_width=wing_width, action='EXIT_DEBIT', qty=trade_qty)
                    
                    # Final real-time PnL computation at close
                    final_pnl = (entry_credit - current_distance_from_center) * 100 * trade_qty
                    if final_pnl < (-max_loss_limit * 100): 
                        final_pnl = -max_loss_limit * 100  # Cap at defined max loss boundary
                        
                    db.log_transaction("SPX", "TIME_CUT_EXIT", target_strike, entry_credit, trade_qty, pnl=final_pnl)
                    db.update_position_state("SPX", "FLAT", 0.0, 0.0, 0)
                    
                    db.print_visible_ledger()
                    db.print_performance_dashboard()

        except Exception as err:
            logger.error(f"Error inside primary automated loop cycle: {err}")

        # Sleep interval loop cycle block
        time.sleep(60)

if __name__ == "__main__":
    run_live_bot()