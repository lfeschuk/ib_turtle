import sqlite3
import pandas as pd
import numpy as np
import logging
import math
import random
import datetime
import pytz
from ib_insync import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 0. MARKET HOURS CALCULATOR
# ==========================================
def get_us_market_status():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.datetime.now(est)
    
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    if now_est.weekday() >= 5: 
        days_ahead = 7 - now_est.weekday()
        next_open = (now_est + datetime.timedelta(days=days_ahead)).replace(hour=9, minute=30, second=0)
        return f"🔴 CLOSED (Weekend). Next Open: {next_open.strftime('%A, %b %d at %H:%M EST')}"
        
    if now_est < market_open:
        return f"🟡 CLOSED (Pre-Market). Opens today at 09:30 EST."
    elif market_open <= now_est <= market_close:
        return f"🟢 OPEN. Closes today at 16:00 EST."
    else: 
        days_ahead = 3 if now_est.weekday() == 4 else 1 
        next_open = (now_est + datetime.timedelta(days=days_ahead)).replace(hour=9, minute=30, second=0)
        return f"🔴 CLOSED (After-Hours). Next Open: {next_open.strftime('%A, %b %d at %H:%M EST')}"

# ==========================================
# 1. THE UNIFIED MEMORY (DataManager)
# ==========================================
class DataManager:
    def __init__(self, db_name="trading_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS market_data (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER, UNIQUE(ticker, date))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_state (ticker TEXT PRIMARY KEY, last_trade_won INTEGER, virtual_capital REAL, units_held INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trade_log (id INTEGER PRIMARY KEY, date TEXT, ticker TEXT, action TEXT, price REAL)''')
        self.conn.commit()

        try:
            self.cursor.execute("ALTER TABLE bot_state ADD COLUMN last_buy_price REAL DEFAULT 0.0")
            self.conn.commit()
        except sqlite3.OperationalError: pass 
        try:
            self.cursor.execute("ALTER TABLE bot_state ADD COLUMN active_system INTEGER DEFAULT 1")
            self.conn.commit()
        except sqlite3.OperationalError: pass 

        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO bot_state (ticker, last_trade_won, virtual_capital, units_held, last_buy_price, active_system) VALUES ('MASTER_ACCOUNT', 0, 5000.0, 0, 0.0, 1)")
            self.conn.commit()

    def save_bars(self, ticker, bars):
        if not bars: return
        insert_query = '''INSERT OR IGNORE INTO market_data (ticker, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)'''
        data_to_insert = [(ticker, bar.date.strftime('%Y-%m-%d'), bar.open, bar.high, bar.low, bar.close, bar.volume) for bar in bars]
        self.cursor.executemany(insert_query, data_to_insert)
        self.conn.commit()

    def load_bars(self, ticker, limit=300):
        query = f"SELECT date, open, high, low, close FROM market_data WHERE ticker = ? ORDER BY date DESC LIMIT {limit}"
        df = pd.read_sql_query(query, self.conn, params=(ticker,))
        if df.empty: return df
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
        df.set_index('date', inplace=True)
        return df

    def get_capital(self):
        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        return self.cursor.fetchone()[0]

    def get_system_status(self, ticker):
        self.cursor.execute("SELECT last_trade_won FROM bot_state WHERE ticker=?", (ticker,))
        row = self.cursor.fetchone()
        return row[0] if row else 0 

    def log_trade(self, ticker, action, price):
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO trade_log (date, ticker, action, price) VALUES (?, ?, ?, ?)", (date, ticker, action, price))
        self.conn.commit()

# ==========================================
# 2. THE EXECUTOR (IBBroker)
# ==========================================
class IBBroker:
    def __init__(self, port=4002): 
        self.ib = IB()
        self.port = port
        self.client_id = 0 

    def connect(self):
        self.ib.connect('127.0.0.1', self.port, clientId=self.client_id, timeout=30)
        logger.info(f"🟢 Connected to IBKR using Master Client ID: {self.client_id}")
        self.ib.reqAutoOpenOrders(True)

    def fetch_missing_bars(self, ticker, days=300):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        bars = self.ib.reqHistoricalData(contract, endDateTime='', durationStr=f'{days} D', barSizeSetting='1 day', whatToShow='TRADES', useRTH=True)
        self.ib.sleep(1) 
        return bars

    def place_oco_buy(self, ticker, price, size, stop_price):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        buy_order = StopOrder('BUY', size, price)
        buy_order.ocaGroup = "TURTLE_BASKET_" + datetime.datetime.now().strftime('%H%M')
        buy_order.ocaType = 1 
        buy_order.tif = 'DAY' 
        
        stop_order = StopOrder('SELL', size, stop_price)
        stop_order.parentId = buy_order.orderId
        stop_order.transmit = True 
        stop_order.tif = 'GTC'
        
        self.ib.placeOrder(contract, buy_order)
        self.ib.placeOrder(contract, stop_order)
        logger.info(f"🕸️ Placed OCO Trap for {ticker} at ${price:.2f} (DAY order)")

    def liquidate_partial(self, ticker, size):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        sell_order = MarketOrder('SELL', size)
        self.ib.placeOrder(contract, sell_order)
        logger.info(f"💸 Profit Taker: Sold {size} shares of {ticker} at Market.")

    def adjust_stop_loss(self, ticker, stop_price, size):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        stop_order = StopOrder('SELL', size, stop_price)
        stop_order.tif = 'GTC'
        self.ib.placeOrder(contract, stop_order)
        logger.info(f"🛡️ Placed new System 2 Protective Stop Loss for {ticker} at ${stop_price:.2f}")

    def get_positions_details(self):
        return {p.contract.symbol: {"shares": p.position, "avg_cost": p.avgCost} for p in self.ib.positions() if p.position > 0}

    def get_pending_orders(self):
        pending_tickers = []
        try:
            self.ib.reqAllOpenOrders()
            self.ib.sleep(1) 
            trades = self.ib.openTrades()
            for t in trades:
                if hasattr(t, 'contract') and hasattr(t.contract, 'symbol'):
                    pending_tickers.append(t.contract.symbol)
            return list(set(pending_tickers))
        except Exception as e:
            return ['API_ERROR_LOCKOUT']

    def cancel_orders(self, target_tickers):
        if target_tickers == ['ALL']:
            self.ib.reqGlobalCancel()
            self.ib.sleep(3)
        else:
            self.ib.reqAllOpenOrders()
            self.ib.sleep(1)
            trades = self.ib.openTrades()
            count = 0
            for t in trades:
                if hasattr(t, 'contract') and hasattr(t.contract, 'symbol'):
                    if t.contract.symbol in target_tickers:
                        self.ib.cancelOrder(t.order)
                        count += 1
            self.ib.sleep(1)

    def liquidate_positions(self, target_tickers):
        positions = self.ib.positions()
        count = 0
        for p in positions:
            if p.position > 0:
                ticker = p.contract.symbol
                if target_tickers == ['ALL'] or ticker in target_tickers:
                    self.cancel_orders([ticker])
                    contract = Stock(ticker, 'SMART', 'USD')
                    self.ib.qualifyContracts(contract)
                    sell_order = MarketOrder('SELL', p.position)
                    self.ib.placeOrder(contract, sell_order)
                    count += 1
        self.ib.sleep(1)

    def disconnect(self):
        self.ib.disconnect()
        logger.info("🔴 Disconnected from Interactive Brokers.")

# ==========================================
# 3. THE BRAINS (TurtleStrategy)
# ==========================================
class TurtleStrategy:
    def __init__(self, db: DataManager, capital, force_list):
        self.db = db
        self.capital = capital
        self.force_list = force_list

    def _calc_days_above(self, price_series, sma_series):
        above = price_series > sma_series
        count = 0
        for val in reversed(above.values):
            if val: count += 1
            else: break
        return count

    def _calc_adx(self, df, period=14):
        df = df.copy()
        df['up_move'] = df['high'].diff()
        df['down_move'] = df['low'].shift(1) - df['low']
        df['+dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['-dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = df['tr'].ewm(alpha=1/period, adjust=False).mean()
        plus_di = 100 * (df['+dm'].ewm(alpha=1/period, adjust=False).mean() / atr)
        minus_di = 100 * (df['-dm'].ewm(alpha=1/period, adjust=False).mean() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.ewm(alpha=1/period, adjust=False).mean().iloc[-1]

    def get_spy_status(self, df_spy):
        if len(df_spy) < 200: return "Not enough data for SPY Macro."
        close = df_spy['close'].iloc[-1]
        sma50 = df_spy['close'].rolling(50).mean().iloc[-1]
        sma200 = df_spy['close'].rolling(200).mean().iloc[-1]
        days_50 = self._calc_days_above(df_spy['close'], df_spy['close'].rolling(50).mean())
        days_200 = self._calc_days_above(df_spy['close'], df_spy['close'].rolling(200).mean())
        macro_safe = close > sma50 and sma50 > sma200
        status_icon = "🟢 BULL REGIME" if macro_safe else "🔴 BEAR/CHOP REGIME (Cash Only)"
        return f"{status_icon}\nCurrent: ${close:.2f} | 50d SMA: ${sma50:.2f} | 200d SMA: ${sma200:.2f}\nSPY is > 50d for [{days_50}] days | > 200d for [{days_200}] days."

    def analyze_open_position(self, ticker, df_stock, avg_cost, current_shares):
        df_stock = df_stock.copy()
        current_close = df_stock['close'].iloc[-1]
        high_55 = df_stock['high'].rolling(55).max().iloc[-2]
        low_10 = df_stock['low'].rolling(10).min().iloc[-2]
        low_20 = df_stock['low'].rolling(20).min().iloc[-2]

        df_stock['prev_close'] = df_stock['close'].shift(1)
        tr = df_stock[['high', 'prev_close']].max(axis=1) - df_stock[['low', 'prev_close']].min(axis=1)
        atr = tr.rolling(20).mean().iloc[-1]

        self.db.cursor.execute("SELECT units_held, last_buy_price, last_trade_won, active_system FROM bot_state WHERE ticker=?", (ticker,))
        row = self.db.cursor.fetchone()
        
        units_held = row[0] if (row and row[0] is not None and row[0] > 0) else 1
        last_buy = row[1] if (row and row[1] is not None and row[1] > 0) else avg_cost
        last_won = row[2] if (row and row[2] is not None) else 0
        active_sys = row[3] if (row and len(row) > 3 and row[3] is not None) else 1

        stop_price = low_20 if active_sys == 2 else low_10

        if active_sys == 1 and current_close >= high_55:
            base_unit_size = current_shares // units_held if units_held > 0 else current_shares
            sell_size = current_shares - base_unit_size
            return {
                "action": "TRANSITION", "sell_size": sell_size, "keep_size": base_unit_size,
                "new_stop": round(low_20, 2), "current_stop": round(stop_price, 2), "trigger_price": round(high_55, 2)
            }

        if units_held < 4:
            pyramid_price = last_buy + (0.5 * atr)
            multiplier = 2.0 if last_won else 0.5
            adj_risk_amt = (self.capital * 0.01) * multiplier
            size = math.floor(adj_risk_amt / atr) if atr > 0 else 0
            return {
                "action": "PYRAMID", "sys": f"S{active_sys}", "units_held": units_held,
                "last_buy": round(last_buy, 2), "atr": round(atr, 2), "pyramid_price": round(pyramid_price, 2),
                "stop_price": round(stop_price, 2), "size": size
            }
        else:
            return {"action": "MAX_UNITS", "sys": f"S{active_sys}", "units_held": units_held, "stop_price": round(stop_price, 2)}

    def analyze(self, ticker, df_stock, df_spy):
        if len(df_stock) < 55 or len(df_spy) < 200:
            return {"action": "SKIP", "reason": f"Not enough historical data. Has {len(df_stock)} days, needs 55."}

        spy_close = df_spy['close'].iloc[-1]
        spy_sma200 = df_spy['close'].rolling(200).mean().iloc[-1]
        macro_safe = spy_close > spy_sma200

        current_close = df_stock['close'].iloc[-1]
        high_20 = df_stock['high'].rolling(20).max().iloc[-2] 
        high_55 = df_stock['high'].rolling(55).max().iloc[-2]
        low_10 = df_stock['low'].rolling(10).min().iloc[-2]
        
        sma50 = df_stock['close'].rolling(50).mean()
        curr_sma50 = sma50.iloc[-1]
        dist_50 = ((current_close / curr_sma50) - 1) * 100 if curr_sma50 > 0 else 0
        days_50 = self._calc_days_above(df_stock['close'], sma50)

        if len(df_stock) >= 200:
            sma200 = df_stock['close'].rolling(200).mean()
            curr_sma200 = sma200.iloc[-1]
            dist_200 = ((current_close / curr_sma200) - 1) * 100 if curr_sma200 > 0 else 0
            days_200 = self._calc_days_above(df_stock['close'], sma200)
        else:
            dist_200 = "N/A"
            days_200 = "N/A"

        if len(df_stock) >= 252:
            stock_ret = (current_close / df_stock['close'].iloc[-252]) - 1 
            spy_ret = (spy_close / df_spy['close'].iloc[-252]) - 1 
            rs = round(50 + ((stock_ret - spy_ret) * 100), 1)
            rs_safe = rs >= 70
        else:
            rs = "N/A"
            rs_safe = True 
            
        adx_val = self._calc_adx(df_stock, 14)
        
        df_stock['prev_close'] = df_stock['close'].shift(1)
        tr = df_stock[['high', 'prev_close']].max(axis=1) - df_stock[['low', 'prev_close']].min(axis=1)
        atr = tr.rolling(20).mean().iloc[-1]

        last_trade_won = self.db.get_system_status(ticker)
        system_type = "S2 (55d)" if last_trade_won else "S1 (20d)"
        entry_price = high_55 if last_trade_won else high_20
        
        multiplier = 2.0 if last_trade_won else 0.5
        adj_risk_amt = (self.capital * 0.01) * multiplier
        size = math.floor(adj_risk_amt / atr) if atr > 0 else 0
        math_str = f"(${self.capital:,.0f} Acct * 1% Risk) * {multiplier}x Multiplier = ${adj_risk_amt:,.2f} Risk ÷ ${atr:.2f} ATR = {size} Shares"

        is_forced = ticker in self.force_list

        if size <= 0: return {"action": "SKIP", "reason": f"ATR (${atr:.2f}) is too high for current risk limit (${adj_risk_amt:.2f}). Required size is 0."}
        if not (is_forced or (macro_safe and rs_safe)): return {"action": "SKIP", "reason": f"Failed Filters. RS is {rs} (Needs 70). SPY Macro Safe: {macro_safe}"}
        if current_close >= entry_price: return {"action": "SKIP", "reason": f"Already Broken Out. Current (${current_close:.2f}) is above the target trap level (${entry_price:.2f}). Waiting for pullback."}

        return {
            "action": "SET_TRAP", "sys": system_type, "current": round(current_close, 2), "price": round(entry_price, 2), 
            "stop": round(low_10, 2), "size": size, "math_str": math_str, "rs": rs, "adx": round(adx_val, 1),
            "dist_50": round(dist_50, 1), "dist_200": dist_200 if dist_200 == "N/A" else round(dist_200, 1),
            "days_50": days_50, "days_200": days_200, "forced": is_forced
        }

# ==========================================
# 4. THE ORCHESTRATOR (Daily Runner)
# ==========================================
def run_daily_workflow():
    db = DataManager()
    broker = IBBroker(port=4002) 
    
    force_list = ["PLTR", "MSTR"] 
    universe = ["AAPL", "MSFT", "NVDA", "GOOG", "CVX", "JPM", "WM", "COST", "SNDK"]
    
    print(f"\n{get_us_market_status()}")
    logger.info("--- WAKING UP TRADING BOT ---")
    broker.connect()
    
    capital = db.get_capital()
    logger.info(f"💰 Available Virtual Capital: ${capital:,.2f}")
    
    positions_details = broker.get_positions_details()
    open_positions = list(positions_details.keys())
    pending_orders = broker.get_pending_orders()

    # --- THE FIX: DYNAMIC TICKER ARRAY TO PREVENT STALE DATA ON ORPHAN POSITIONS ---
    active_tracking = list(set(["SPY"] + force_list + universe + open_positions + pending_orders))
    if 'API_ERROR_LOCKOUT' in active_tracking: active_tracking.remove('API_ERROR_LOCKOUT')

    print("\n" + "="*60)
    print("📥 SYNCHRONIZING MARKET DATA...")
    for ticker in active_tracking:
        local_df = db.load_bars(ticker)
        # Fetch 300 days if new, otherwise grab the last 5 days to ensure we have the exact close from yesterday
        if len(local_df) < 300:
            bars = broker.fetch_missing_bars(ticker, days=300)
        else:
            bars = broker.fetch_missing_bars(ticker, days=5) 
        db.save_bars(ticker, bars)
    print("✅ Data Sync Complete.")
    print("="*60)

    # --- MANUAL INTERVENTION MENU ---
    if open_positions:
        print(f"\n📂 ACTIVE POSITIONS: {open_positions}")
        choice = input("Type TICKERS to LIQUIDATE (e.g. MSFT,AAPL), 'ALL', or press ENTER to hold: ").strip().upper()
        if choice:
            targets = ['ALL'] if choice == 'ALL' else [x.strip() for x in choice.split(',')]
            broker.liquidate_positions(targets)
            db.log_trade("MANUAL_LIQUIDATE", str(targets), 0)
            print("⏳ Waiting for IBKR server...")
            broker.ib.sleep(3) 
            positions_details = broker.get_positions_details()
            open_positions = list(positions_details.keys())

    if pending_orders and 'API_ERROR_LOCKOUT' not in pending_orders:
        print(f"\n⏳ PENDING ORDERS/TRAPS: {pending_orders}")
        choice = input("Type TICKERS to CANCEL orders for (e.g. GOOG,NVDA), 'ALL', or press ENTER to keep them: ").strip().upper()
        if choice:
            targets = ['ALL'] if choice == 'ALL' else [x.strip() for x in choice.split(',')]
            broker.cancel_orders(targets)
            db.log_trade("MANUAL_CANCEL", str(targets), 0)
            print("⏳ Waiting for IBKR server...")
            broker.ib.sleep(3) 
            pending_orders = broker.get_pending_orders() 

    # -----------------------------------------------------
    # THE SCANNER & PLAN EXECUTION
    # -----------------------------------------------------
    strategy = TurtleStrategy(db, capital, force_list)
    
    # 1. POSITION MANAGEMENT
    if len(open_positions) > 0:
        print("\n" + "="*125)
        print("📈 POSITION MANAGEMENT PLAN:")
        print("="*125)
        
        for ticker in open_positions:
            df_stock = db.load_bars(ticker)
            if len(df_stock) < 55: 
                logger.warning(f"⚠️ Not enough data saved for {ticker}. Skipping management.")
                continue

            avg_cost = positions_details[ticker]["avg_cost"]
            shares = positions_details[ticker]["shares"]
            
            signal = strategy.analyze_open_position(ticker, df_stock, avg_cost, shares)
            
            if signal:
                if signal["action"] == "TRANSITION":
                    print(f"🔄 {ticker: <5} | SYSTEM TRANSITION DETECTED (S1 -> S2) | 55-Day High Hit (${signal['trigger_price']})")
                    if signal['sell_size'] > 0: print(f"   ↳ 💸 Will Sell {signal['sell_size']} excess shares at Market.")
                    print(f"   ↳ 🛡️ Will adjust Stop Loss for remaining {signal['keep_size']} shares to wider S2 floor: ${signal['new_stop']}")
                    
                    choice = input(f"\nPress ENTER to execute Transition Protocol for {ticker}, or type 'SKIP': ").strip().upper()
                    if choice != 'SKIP':
                        broker.cancel_orders([ticker])
                        if signal['sell_size'] > 0:
                            broker.liquidate_partial(ticker, signal['sell_size'])
                            db.log_trade(ticker, "TRANSITION_PARTIAL_SELL", 0)
                        broker.adjust_stop_loss(ticker, signal['new_stop'], signal['keep_size'])
                        db.cursor.execute("UPDATE bot_state SET active_system=2, units_held=1 WHERE ticker=?", (ticker,))
                        db.conn.commit()

                elif signal["action"] == "PYRAMID":
                    print(f"🎯 {ticker: <5} | Unit {signal['units_held']}/4 | Active Sys: {signal['sys']} | Current Stop: ${signal['stop_price']}")
                    print(f"   ↳ 📈 Pyramid Trap: Buy {signal['size']} shares @ ${signal['pyramid_price']}")
                    
                    if ticker not in pending_orders:
                        choice = input(f"\nPress ENTER to place Pyramid Buy Stop for {ticker}, or type 'SKIP': ").strip().upper()
                        if choice != 'SKIP':
                            broker.place_oco_buy(ticker, signal['pyramid_price'], signal['size'], signal['stop_price'])
                    else:
                        print(f"   ↳ ⏳ Pending order active. Skipping trap placement to avoid duplicates.")
                        
                elif signal["action"] == "MAX_UNITS":
                    print(f"🛡️ {ticker: <5} | MAX UNITS REACHED (4/4). Holding position. | Active Sys: {signal['sys']} | Stop Floor: ${signal['stop_price']}")
        print("="*125)

    # 2. STANDARD SCANNER
    elif len(pending_orders) == 0:
        df_spy = db.load_bars("SPY")
        print("\n" + "="*80)
        print("🇺🇸 SPY MACRO STATUS:")
        print("-" * 80)
        print(strategy.get_spy_status(df_spy))
        print("="*80)

        targets, skipped = [], []
        for ticker in (force_list + universe):
            df_stock = db.load_bars(ticker)
            signal = strategy.analyze(ticker, df_stock, df_spy)
            if signal:
                if signal['action'] == "SET_TRAP": targets.append((ticker, signal))
                elif signal['action'] == "SKIP": skipped.append((ticker, signal['reason']))

        print("\n" + "="*125)
        print("📈 PLAN FOR NEXT TRADING SESSION:")
        print("="*125)
        
        if not targets:
            print("No valid setups found today. The robot will sit safely in cash.")
        else:
            def get_rs_sort(x): return float(x[1]['rs']) if x[1]['rs'] != "N/A" else 100.0
            targets.sort(key=get_rs_sort, reverse=True)
            for t, s in targets:
                dist_pct = ((s['price'] / s['current']) - 1) * 100
                force_tag = "[FORCED]" if s['forced'] else ""
                rs_str = str(s['rs'])
                d200_str = f"+{s['dist_200']}%" if s['dist_200'] != "N/A" else "N/A"
                print(f"🎯 {t: <5} | {s['sys']} | Buy: ${s['price']:<7.2f} (+{dist_pct:<4.1f}%) | ADX: {s['adx']:<4.1f} | RS: {rs_str:<4} | >50d: {s['days_50']:<3} (+{s['dist_50']:>4.1f}%) | >200d: {s['days_200']:<3} ({d200_str}) {force_tag}")
                print(f"   ↳ 🧮 Sizing Math: {s['math_str']}")
        
        if skipped:
            print("-" * 125)
            print("❌ REJECTION LOG (Why the bot skipped these stocks):")
            for t, reason in skipped: print(f"   - {t:<5}: {reason}")
            
        print("="*125)
        
        if targets:
            choice = input("\nPress ENTER to place OCO DAY Orders for all targets, or type TICKERS separated by commas (e.g. NVDA,AAPL) to trap specific ones: ").strip().upper()
            if choice:
                chosen_list = [x.strip() for x in choice.split(',')]
                filtered_targets = [t for t in targets if t[0] in chosen_list]
                if filtered_targets:
                    print(f"\n✅ User Override: Locking onto {', '.join([t[0] for t in filtered_targets])} only.")
                    targets = filtered_targets
                else:
                    print("\n⚠️ No matching tickers found from your input. Aborting order placement for safety.")
                    targets = [] 
            
            for t, s in targets:
                broker.place_oco_buy(t, s['price'], s['size'], s['stop'])
                db.log_trade(t, "DAY_TRAP_PLACED", s['price'])

    # ==========================================
    # THE LIVE MONITORING LOOP 
    # ==========================================
    def on_fill(trade, fill):
        ticker = trade.contract.symbol
        side = fill.execution.side  
        price = fill.execution.price
        
        if side == 'BOT':
            db.cursor.execute("SELECT units_held, last_trade_won FROM bot_state WHERE ticker=?", (ticker,))
            row = db.cursor.fetchone()
            current_units = row[0] if (row and row[0] is not None) else 0
            last_won = row[1] if (row and row[1] is not None) else 0
            
            db.cursor.execute("SELECT active_system FROM bot_state WHERE ticker=?", (ticker,))
            sys_row = db.cursor.fetchone()
            active_sys = (2 if last_won else 1) if current_units == 0 else (sys_row[0] if sys_row else 1)

            new_units = current_units + 1
            db.cursor.execute("UPDATE bot_state SET units_held=?, last_buy_price=?, active_system=? WHERE ticker=?", (new_units, price, active_sys, ticker))
            if db.cursor.rowcount == 0:
                db.cursor.execute("INSERT INTO bot_state (ticker, last_trade_won, virtual_capital, units_held, last_buy_price, active_system) VALUES (?, 0, 5000.0, ?, ?, ?)", (ticker, new_units, price, active_sys))
            db.conn.commit()
            
        elif side == 'SLD':
            db.cursor.execute("UPDATE bot_state SET units_held=0, last_buy_price=0.0 WHERE ticker=?", (ticker,))
            db.conn.commit()

        print("\n" + "🚨"*20)
        logger.info(f"LIVE EXECUTION ALERT: Order Filled!")
        logger.info(f"Action: {side} | Ticker: {ticker} | Price: ${price:.2f}")

        broker.ib.sleep(1)
        open_orders = broker.ib.reqAllOpenOrders()
        current_stop = "None Found"
        for o in open_orders:
            if o.contract.symbol == ticker and o.orderType == 'STP' and o.action == 'SELL':
                current_stop = f"${o.auxPrice:.2f}"
                break
        
        logger.info(f"Active Protective Stop Loss is currently: {current_stop}")
        print("🚨"*20 + "\n")
        
        db.log_trade(ticker, f"LIVE_FILL_{side}", price)

    broker.ib.execDetailsEvent += on_fill
    
    print("\n👁️  Bot is now in LIVE MONITORING MODE. Waiting for fills...")
    print("Press Ctrl+C to stop the bot at any time.")
    
    try:
        broker.ib.run()
    except KeyboardInterrupt:
        print("\nManually stopped by user.")
        broker.disconnect()

if __name__ == "__main__":
    run_daily_workflow()