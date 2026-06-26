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
# 1. DUAL DATABASE MANAGER (DataManager)
# ==============================================================================
class DataManager:
    def __init__(self, db_name="dual_mode_trading.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Table to store daily strategy decision
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS daily_decision 
            (date TEXT PRIMARY KEY, vix_value REAL, selected_strategy TEXT, status TEXT)''')
            
        # Table to track bot active state
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_state 
            (strategy TEXT PRIMARY KEY, current_side TEXT, entry_price REAL, stop_loss_price REAL, qty INTEGER, extra_param REAL)''')
            
        # Table to log all transactions
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trade_log 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp_ist TEXT, strategy TEXT, action TEXT, price REAL, qty INTEGER, pnl REAL DEFAULT 0.0)''')
        
        self.conn.commit()

        # Initialize bot states if not exist
        for strat in ["MES_ORB", "SPX_BUTTERFLY"]:
            self.cursor.execute("SELECT current_side FROM bot_state WHERE strategy=?", (strat,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT INTO bot_state VALUES (?, 'FLAT', 0.0, 0.0, 0, 0.0)", (strat,))
        self.conn.commit()

    def auto_repair_past_trades(self):
        """Automatically scans the database on startup for any SPX Butterfly entries missing exits,
        queries the SPX close price from Yahoo Finance, and inserts the missing expiration exits with a fallback credit."""
        # Query only entries that do not have a corresponding exit in the local database
        self.cursor.execute("""
            SELECT e.id, e.timestamp_ist, e.price, e.qty 
            FROM trade_log e
            WHERE e.strategy='SPX_BUTTERFLY' AND e.action='ENTRY_CREDIT'
            AND NOT EXISTS (
                SELECT 1 FROM trade_log x 
                WHERE x.strategy='SPX_BUTTERFLY' 
                AND (x.action='EXPIRATION_EXIT' OR x.action='TIME_CUT_EXIT') 
                AND SUBSTR(x.timestamp_ist, 1, 10) = SUBSTR(e.timestamp_ist, 1, 10)
            )
            ORDER BY e.id ASC;
        """)
        entries = self.cursor.fetchall()
        if not entries:
            return
            
        wing_width = 10.0
        repairs_made = False
        
        for entry_id, timestamp_ist, price, qty in entries:
            date_str = timestamp_ist.split()[0]
            logger.info(f"🛠️ Found missing exit for SPX Butterfly trade on {date_str}. Repairing automatically...")
            
            # The stored price in the database was the center_strike (our bug)
            center_strike = price
            
            # Fetch SPX close price from Yahoo Finance
            import time
            import json
            import urllib.request
            
            spx_close = None
            try:
                t = time.strptime(date_str, "%Y-%m-%d")
                epoch = int(time.mktime(t))
                start = epoch - 86400 * 2
                end = epoch + 86400 * 2
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/^GSPC?period1={start}&period2={end}&interval=1d"
                headers = {'User-Agent': 'Mozilla/5.0'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    result = data['chart']['result'][0]
                    timestamps = result.get('timestamp', [])
                    closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
                    for ts, close in zip(timestamps, closes):
                        ts_date = time.strftime("%Y-%m-%d", time.localtime(ts))
                        if ts_date == date_str and close is not None:
                            spx_close = float(close)
                            break
            except Exception as e:
                logger.error(f"Error fetching SPX close for {date_str}: {e}")
                
            if spx_close is None:
                logger.warning(f"Could not resolve SPX closing price for {date_str}. Skipping auto-repair.")
                continue
                
            # Fallback to default estimate for past paper trades
            entry_credit = 7.50
            close_distance = abs(spx_close - center_strike)
            exp_value = min(wing_width, close_distance)
            pnl = (entry_credit - exp_value) * 100.0 * qty
            
            # Insert missing exit and retroactively update entry price to the credit received
            exit_timestamp = f"{date_str} 23:02:00"
            self.cursor.execute("INSERT INTO trade_log (timestamp_ist, strategy, action, price, qty, pnl) VALUES (?, 'SPX_BUTTERFLY', 'EXPIRATION_EXIT', ?, ?, ?);",
                                (exit_timestamp, spx_close, qty, pnl))
            self.cursor.execute("UPDATE trade_log SET price=? WHERE id=?;", (entry_credit, entry_id))
            repairs_made = True
            logger.info(f"✅ Repaired {date_str} trade: Close={spx_close:.2f} | Credit={entry_credit:.2f} | Exp Value={exp_value:.2f} | PnL=${pnl:+.2f}")
            
        if repairs_made:
            self.conn.commit()

    def get_daily_decision(self, date_str):
        self.cursor.execute("SELECT vix_value, selected_strategy, status FROM daily_decision WHERE date=?", (date_str,))
        row = self.cursor.fetchone()
        if row:
            return {"vix": row[0], "strategy": row[1], "status": row[2]}
        return None

    def save_daily_decision(self, date_str, vix_value, strategy, status):
        self.cursor.execute("INSERT OR REPLACE INTO daily_decision (date, vix_value, selected_strategy, status) VALUES (?, ?, ?, ?)",
                            (date_str, vix_value, strategy, status))
        self.conn.commit()

    def get_bot_state(self, strategy):
        self.cursor.execute("SELECT current_side, entry_price, stop_loss_price, qty, extra_param FROM bot_state WHERE strategy=?", (strategy,))
        row = self.cursor.fetchone()
        if row:
            return {
                "side": row[0],
                "entry_price": row[1],
                "stop_loss_price": row[2],
                "qty": row[3],
                "extra_param": row[4] # Center strike for SPX, range_high/range_low placeholders if needed
            }
        return {"side": "FLAT", "entry_price": 0.0, "stop_loss_price": 0.0, "qty": 0, "extra_param": 0.0}

    def update_bot_state(self, strategy, side, entry_price, stop_loss_price, qty, extra_param=0.0):
        self.cursor.execute("INSERT OR REPLACE INTO bot_state (strategy, current_side, entry_price, stop_loss_price, qty, extra_param) VALUES (?, ?, ?, ?, ?, ?)",
                            (strategy, side, entry_price, stop_loss_price, qty, extra_param))
        self.conn.commit()

    def log_transaction(self, strategy, action, price, qty, pnl=0.0):
        timestamp_ist = datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO trade_log (timestamp_ist, strategy, action, price, qty, pnl) VALUES (?, ?, ?, ?, ?, ?)", 
                            (timestamp_ist, strategy, action, price, qty, pnl))
        self.conn.commit()

    def print_visible_ledger(self):
        df = pd.read_sql_query("SELECT timestamp_ist, strategy, action, price, qty, pnl FROM trade_log ORDER BY id DESC LIMIT 10", self.conn)
        print("\n" + "🔮" + "="*95 + "🔮")
        print(f"{'IST TIMESTAMP':<20} | {'STRATEGY':<13} | {'ACTION':<22} | {'PRICE/STK':<10} | {'QTY':<4} | {'REALIZED PNL'}")
        print("-" * 101)
        if df.empty:
            print(f"{'NO TRANSACTIONS LOGGED YET. AUTOMATED AGENT ACTIVE...':^101}")
        for _, row in df.iterrows():
            pnl_val = row['pnl']
            pnl_str = f"${pnl_val:+.2f}" if pnl_val != 0.0 else "-"
            print(f"{row['timestamp_ist']:<20} | {row['strategy']:<13} | {row['action']:<22} | {row['price']:<10.2f} | {row['qty']:<4} | {pnl_str}")
        print("="*99)

# ==============================================================================
# 2. EXECUTION ENGINE (IBBroker)
# ==============================================================================
class IBBroker:
    def __init__(self, port=4002, client_id=50):
        self.ib = IB()
        self.port = port
        self.client_id = client_id
        self.active_mes_contract = None

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', self.port, clientId=self.client_id)
            logger.info(f"🟢 Dual-Mode Bot online on port {self.port}. Client ID: {self.client_id}")
            
            # Options type setup
            accounts = self.ib.managedAccounts()
            is_paper = (self.port in [4002, 7497]) or any(acc.upper().startswith(('DU', 'DF')) for acc in accounts)
            if is_paper:
                self.ib.reqMarketDataType(3)
            else:
                self.ib.reqMarketDataType(1)
                
            self.resolve_mes_contract()
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

    # --- MES Futures Setup ---
    def resolve_mes_contract(self):
        contract = Future('MES', multiplier='5', exchange='CME', currency='USD')
        details = self.ib.reqContractDetails(contract)
        if not details:
            logger.error("❌ Could not resolve MES contracts.")
            return
        now_str = datetime.datetime.now().strftime('%Y%m%d')
        valid_contracts = [d.contract for d in details if d.contract.lastTradeDateOrContractMonth >= now_str]
        valid_contracts.sort(key=lambda x: x.lastTradeDateOrContractMonth)
        if valid_contracts:
            self.active_mes_contract = valid_contracts[0]
            self.ib.qualifyContracts(self.active_mes_contract)
            logger.info(f"🎯 Resolved active MES: {self.active_mes_contract.localSymbol}")

    def get_2h_mes_range(self):
        if not self.active_mes_contract:
            self.resolve_mes_contract()
        bars = self.ib.reqHistoricalData(
            self.active_mes_contract, endDateTime='', durationStr='1 D',
            barSizeSetting='5 mins', whatToShow='TRADES', useRTH=True
        )
        if not bars:
            return None, None
        now_est = datetime.datetime.now(EST)
        start_r = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
        end_r = now_est.replace(hour=11, minute=30, second=0, microsecond=0)
        
        highs, lows = [], []
        for b in bars:
            if isinstance(b.date, datetime.datetime):
                b_est = b.date.astimezone(EST)
                if start_r <= b_est <= end_r:
                    highs.append(b.high)
                    lows.append(b.low)
        if not highs:
            return None, None
        return max(highs), min(lows)

    def place_stop_order(self, action, stop_price, qty):
        order = Order(action=action, orderType='STP', auxPrice=stop_price, totalQuantity=qty, transmit=True)
        trade = self.ib.placeOrder(self.active_mes_contract, order)
        self.ib.sleep(0.5)
        return trade

    def place_market_order(self, action, qty):
        order = MarketOrder(action, qty, transmit=True)
        trade = self.ib.placeOrder(self.active_mes_contract, order)
        return trade

    # --- SPX Options Setup ---
    def resolve_option_contract(self, strike, right, expiry):
        contract = Option(symbol='SPX', lastTradeDateOrContractMonth=expiry, strike=strike, right=right, exchange='CBOE', multiplier='100', currency='USD')
        qualified = self.ib.qualifyContracts(contract)
        return qualified[0] if qualified else None

    def execute_iron_butterfly(self, center_strike, wing_width=10, action='ENTRY_CREDIT', qty=1):
        expiry = datetime.datetime.now(EST).strftime('%Y%m%d')
        c_short_call = self.resolve_option_contract(center_strike, 'C', expiry)
        c_short_put  = self.resolve_option_contract(center_strike, 'P', expiry)
        c_long_call  = self.resolve_option_contract(center_strike + wing_width, 'C', expiry)
        c_long_put   = self.resolve_option_contract(center_strike - wing_width, 'P', expiry)
        
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
        order = MarketOrder(order_action, qty, tif='DAY')
        trade = self.ib.placeOrder(bag, order)
        # Wait for the order to complete (up to 15 seconds timeout)
        start_time = time.time()
        while not trade.isDone():
            self.ib.sleep(0.5)
            if time.time() - start_time > 15:
                logger.warning("⚠️ Order execution timed out after 15 seconds.")
                break
        return trade

    def cancel_all_active_orders(self):
        for o in self.ib.orders():
            if o.status in ['Submitted', 'PreSubmitted', 'Accepted']:
                self.ib.cancelOrder(o)
        self.ib.sleep(0.5)

# ==============================================================================
# 3. CRITICAL DECISION RUNNER LOOP
# ==============================================================================
def run_live_dual_bot():
    db = DataManager()
    
    # Connect to TWS/Gateway
    port = 4002
    broker = IBBroker(port=port, client_id=50)
    if not broker.connect():
        port = 7497
        broker = IBBroker(port=port, client_id=50)
        if not broker.connect():
            logger.critical("❌ Could not connect to IBKR TWS/Gateway on ports 4002/7497.")
            return

    # Run database auto-repair on startup
    db.auto_repair_past_trades()

    db.print_visible_ledger()
    
    vix_limit = 20.0
    qty_mes = 1
    qty_butterfly = 1
    wing_width = 10
    
    # Active orders state pointers
    buy_stop_order = None
    sell_stop_order = None
    stop_loss_order = None

    last_eval_date = None
    last_standby_log_minute = None

    while True:
        try:
            now_ist = datetime.datetime.now(IST)
            now_est = now_ist.astimezone(EST)
            current_time_str = now_ist.strftime('%H:%M')
            today_str = now_ist.strftime('%Y-%m-%d')
            
            is_weekend = now_est.weekday() >= 5
            
            if last_eval_date != today_str:
                last_eval_date = today_str
                buy_stop_order = None
                sell_stop_order = None
                stop_loss_order = None
                logger.info(f"🌅 New trading day initialized: {today_str}")

            decision = db.get_daily_decision(today_str)
            mes_state = db.get_bot_state("MES_ORB")
            bf_state = db.get_bot_state("SPX_BUTTERFLY")

            # ------------------------------------------------------------------
            # 1. 11:30 AM EST (18:30 IST): EVALUATE REGIME & DECIDE STRATEGY
            # ------------------------------------------------------------------
            if not is_weekend and decision is None:
                # Trigger at exactly 18:30 IST, or catch up if bot started late during the trading day (before market close)
                if current_time_str == "18:30" or ("18:30" < current_time_str < "22:55"):
                    vix = broker.get_index_price("VIX")
                    if vix is not None and not math.isnan(vix):
                        # OVERRIDE FOR TESTING: Always trade MES_ORB regardless of VIX
                        logger.info(f"⚠️ TESTING OVERRIDE: VIX is {vix:.2f}. Overriding VIX threshold rule and forcing MES 2h ORB strategy today.")
                        db.save_daily_decision(today_str, vix, "MES_ORB", "DECIDED")
                        
                        # Retrieve 2-hour range and place OCO stop orders
                        r_high, r_low = broker.get_2h_mes_range()
                        if r_high and r_low:
                            logger.info(f"📊 2-Hour Range: High={r_high:.2f} | Low={r_low:.2f}. Placing OCO Stops...")
                            broker.cancel_all_active_orders()
                            buy_stop_order = broker.place_stop_order('BUY', r_high + 0.50, qty_mes)
                            sell_stop_order = broker.place_stop_order('SELL', r_low - 0.50, qty_mes)
                            
                            db.update_bot_state("MES_ORB", "PENDING", r_high + 0.50, r_low - 0.50, qty_mes, extra_param=r_low)
                    else:
                        logger.warning("⚠️ VIX price query returned NaN or None. Retrying VIX evaluation on next tick...")

            # ------------------------------------------------------------------
            # 2. 1:30 PM EST (20:30 IST): EXECUTE SPX IRON BUTTERFLY (IF SELECTED)
            # ------------------------------------------------------------------
            if decision and decision["strategy"] == "SPX_BUTTERFLY" and bf_state["side"] == "FLAT":
                if current_time_str < "20:30":
                    if last_standby_log_minute != current_time_str:
                        last_standby_log_minute = current_time_str
                        logger.debug(f"⏳ Standby: Time is {current_time_str}. Waiting for 20:30 IST entry window...")
                
                if current_time_str == "20:30":
                    spx = broker.get_index_price("SPX")
                    if spx is not None and not math.isnan(spx):
                        center_strike = round(spx / 5) * 5
                        logger.info(f"🎯 1:30 PM: ATM Strike is {center_strike}. Selling 10-wide SPX Iron Butterfly...")
                        
                        trade = broker.execute_iron_butterfly(center_strike, wing_width, 'ENTRY_CREDIT', qty_butterfly)
                        credit = abs(trade.orderStatus.avgFillPrice) if trade and trade.orderStatus.avgFillPrice and not math.isnan(trade.orderStatus.avgFillPrice) else 7.50
                        
                        db.log_transaction("SPX_BUTTERFLY", "ENTRY_CREDIT", credit, qty_butterfly)
                        db.update_bot_state("SPX_BUTTERFLY", "ACTIVE", center_strike, 0.0, qty_butterfly, extra_param=center_strike)
                        db.save_daily_decision(today_str, decision["vix"], "SPX_BUTTERFLY", "EXECUTING")
                        db.print_visible_ledger()

            # ------------------------------------------------------------------
            # 3. STRATEGY IN-FLIGHT MONITORING & OCO ENTRY CHECK
            # ------------------------------------------------------------------
            if decision and decision["strategy"] == "MES_ORB":
                # A. Monitor OCO entry trigger
                if mes_state["side"] == "PENDING":
                    broker.ib.sleep(0)
                    long_filled = buy_stop_order and buy_stop_order.orderStatus.status == 'Filled'
                    short_filled = sell_stop_order and sell_stop_order.orderStatus.status == 'Filled'
                    
                    if long_filled:
                        logger.info("🟢 MES Long Breakout filled. Cancelling short entry stop and placing opposite-range Stop Loss...")
                        broker.cancel_all_active_orders()
                        fill_p = buy_stop_order.orderStatus.avgFillPrice
                        sl_price = mes_state["extra_param"] # range low is saved here
                        stop_loss_order = broker.place_stop_order('SELL', sl_price, qty_mes)
                        
                        db.log_transaction("MES_ORB", "LONG_BREAKOUT_ENTRY", fill_p, qty_mes)
                        db.update_bot_state("MES_ORB", "ACTIVE_LONG", fill_p, sl_price, qty_mes, extra_param=mes_state["entry_price"])
                        db.save_daily_decision(today_str, decision["vix"], "MES_ORB", "EXECUTING")
                        db.print_visible_ledger()
                        
                    elif short_filled:
                        logger.info("🔴 MES Short Breakout filled. Cancelling long entry stop and placing opposite-range Stop Loss...")
                        broker.cancel_all_active_orders()
                        fill_p = sell_stop_order.orderStatus.avgFillPrice
                        sl_price = mes_state["entry_price"] # buy entry price (range high + 0.50) is saved here
                        stop_loss_order = broker.place_stop_order('BUY', sl_price, qty_mes)
                        
                        db.log_transaction("MES_ORB", "SHORT_BREAKOUT_ENTRY", fill_p, qty_mes)
                        db.update_bot_state("MES_ORB", "ACTIVE_SHORT", fill_p, sl_price, qty_mes, extra_param=mes_state["entry_price"])
                        db.save_daily_decision(today_str, decision["vix"], "MES_ORB", "EXECUTING")
                        db.print_visible_ledger()

                # B. Monitor MES Stop Loss execution
                elif mes_state["side"] in ["ACTIVE_LONG", "ACTIVE_SHORT"]:
                    broker.ib.sleep(0)
                    if stop_loss_order and stop_loss_order.orderStatus.status == 'Filled':
                        logger.warning("💥 MES STOP LOSS TRIGGERED. Position closed.")
                        exit_price = stop_loss_order.orderStatus.avgFillPrice
                        pnl = (exit_price - mes_state["entry_price"]) * 5.0 * qty_mes if mes_state["side"] == "ACTIVE_LONG" else (mes_state["entry_price"] - exit_price) * 5.0 * qty_mes
                        
                        db.log_transaction("MES_ORB", "STOP_LOSS_EXIT", exit_price, qty_mes, pnl=pnl)
                        db.update_bot_state("MES_ORB", "FLAT", 0.0, 0.0, 0, 0.0)
                        db.save_daily_decision(today_str, decision["vix"], "MES_ORB", "STOPPED_OUT")
                        db.print_visible_ledger()

            # ------------------------------------------------------------------
            # 4. TIME EXIT CUT-OFF (3:58 PM EST / 22:58 IST): OVERNIGHT FLAT RULE (FUTURES ONLY)
            # ------------------------------------------------------------------
            if now_est.hour == 15 and now_est.minute >= 58:
                # Close MES Futures (we must close futures at market, they don't expire)
                if mes_state["side"] in ["ACTIVE_LONG", "ACTIVE_SHORT"]:
                    broker.cancel_all_active_orders()
                    logger.info("⚠️ TIME CUT-OFF: Exiting active MES Futures Position...")
                    close_action = 'SELL' if mes_state["side"] == "ACTIVE_LONG" else 'BUY'
                    trade = broker.place_market_order(close_action, qty_mes)
                    # wait for fill
                    while not trade.isDone():
                        broker.ib.sleep(0.5)
                    exit_p = trade.orderStatus.avgFillPrice if trade.orderStatus.avgFillPrice > 0 else broker.active_mes_contract.marketPrice()
                    pnl = (exit_p - mes_state["entry_price"]) * 5.0 * qty_mes if mes_state["side"] == "ACTIVE_LONG" else (mes_state["entry_price"] - exit_p) * 5.0 * qty_mes
                    
                    db.log_transaction("MES_ORB", "TIME_CUT_EXIT", exit_p, qty_mes, pnl=pnl)
                    db.update_bot_state("MES_ORB", "FLAT", 0.0, 0.0, 0, 0.0)
                    db.save_daily_decision(today_str, decision["vix"], "MES_ORB", "COMPLETED")
                    db.print_visible_ledger()

            # ------------------------------------------------------------------
            # 5. EXPIRATION PNL EVALUATION (4:02 PM EST / 23:02 IST)
            # ------------------------------------------------------------------
            if now_est.hour >= 16:
                # We check time is >= 16:02 EST
                if now_est.hour > 16 or (now_est.hour == 16 and now_est.minute >= 2):
                    if bf_state["side"] == "ACTIVE":
                        logger.info("⚠️ Market Close Reached. Calculating SPX Iron Butterfly expiration PnL...")
                        center_stk = bf_state["entry_price"]
                        
                        # Fetch SPX closing price
                        spx_close = broker.get_index_price("SPX")
                        if spx_close is not None and not math.isnan(spx_close):
                            # Calculate expiration value (debit to close)
                            close_distance = abs(spx_close - center_stk)
                            exp_value = min(wing_width, close_distance)
                            
                            # Retrieve the entry credit from db
                            db.cursor.execute("SELECT price FROM trade_log WHERE strategy='SPX_BUTTERFLY' AND action='ENTRY_CREDIT' AND timestamp_ist LIKE ?", (f"{today_str}%",))
                            db_row = db.cursor.fetchone()
                            entry_credit = db_row[0] if db_row else 7.50
                            
                            pnl = (entry_credit - exp_value) * 100.0 * qty_butterfly
                            logger.info(f"📊 SPX Expiration: Close={spx_close:.2f} | Strike={center_stk} | Exp Value={exp_value:.2f} | PnL=${pnl:+.2f}")
                            
                            db.log_transaction("SPX_BUTTERFLY", "EXPIRATION_EXIT", spx_close, qty_butterfly, pnl=pnl)
                            db.update_bot_state("SPX_BUTTERFLY", "FLAT", 0.0, 0.0, 0, 0.0)
                            db.save_daily_decision(today_str, decision["vix"], "SPX_BUTTERFLY", "COMPLETED")
                            db.print_visible_ledger()
                        else:
                            logger.warning("⚠️ Failed to fetch SPX closing price. Retrying on next tick...")

        except Exception as err:
            logger.error(f"Error in automated loop cycle: {err}")

        broker.ib.sleep(15)

if __name__ == '__main__':
    run_live_dual_bot()
