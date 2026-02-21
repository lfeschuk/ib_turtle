import sqlite3
import pandas as pd
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
    """Calculates if the US Market is currently open and when it opens next."""
    est = pytz.timezone('US/Eastern')
    now_est = datetime.datetime.now(est)
    
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    if now_est.weekday() >= 5: # Saturday or Sunday
        days_ahead = 7 - now_est.weekday()
        next_open = (now_est + datetime.timedelta(days=days_ahead)).replace(hour=9, minute=30, second=0)
        return f"🔴 CLOSED (Weekend). Next Open: {next_open.strftime('%A, %b %d at %H:%M EST')}"
        
    if now_est < market_open:
        return f"🟡 CLOSED (Pre-Market). Opens today at 09:30 EST."
    elif market_open <= now_est <= market_close:
        return f"🟢 OPEN. Closes today at 16:00 EST."
    else: # After 4:00 PM EST
        days_ahead = 3 if now_est.weekday() == 4 else 1 # Skip weekend if Friday
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

        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO bot_state (ticker, last_trade_won, virtual_capital, units_held) VALUES ('MASTER_ACCOUNT', 0, 5000.0, 0)")
            self.conn.commit()

    def save_bars(self, ticker, bars):
        if not bars: return
        insert_query = '''INSERT OR IGNORE INTO market_data (ticker, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)'''
        data_to_insert = [(ticker, bar.date.strftime('%Y-%m-%d'), bar.open, bar.high, bar.low, bar.close, bar.volume) for bar in bars]
        self.cursor.executemany(insert_query, data_to_insert)
        self.conn.commit()

    def load_bars(self, ticker, limit=260):
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
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        self.cursor.execute("INSERT INTO trade_log (date, ticker, action, price) VALUES (?, ?, ?, ?)", (date, ticker, action, price))
        self.conn.commit()

# ==========================================
# 2. THE EXECUTOR (IBBroker)
# ==========================================
class IBBroker:
    def __init__(self, port=4002): 
        self.ib = IB()
        self.port = port
        self.client_id = random.randint(1, 9999) 

    def connect(self):
        self.ib.connect('127.0.0.1', self.port, clientId=self.client_id, timeout=30)
        logger.info(f"🟢 Connected to IBKR using Client ID: {self.client_id}")

    def fetch_missing_bars(self, ticker, days=260):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        bars = self.ib.reqHistoricalData(contract, endDateTime='', durationStr=f'{days} D', barSizeSetting='1 day', whatToShow='TRADES', useRTH=True)
        self.ib.sleep(1) 
        return bars

    def place_oco_buy(self, ticker, price, size, stop_price):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        # --- ORDER TIME-IN-FORCE UPGRADES ---
        # The Entry Order is a DAY order. If it doesn't trigger tomorrow, it dies.
        buy_order = StopOrder('BUY', size, price)
        buy_order.ocaGroup = "TURTLE_BASKET_" + datetime.datetime.now().strftime('%H%M')
        buy_order.ocaType = 1 
        buy_order.tif = 'DAY' 
        
        # The Stop Loss is GTC. If the entry fills, this protects you forever until hit.
        stop_order = StopOrder('SELL', size, stop_price)
        stop_order.parentId = buy_order.orderId
        stop_order.transmit = True 
        stop_order.tif = 'GTC'
        
        self.ib.placeOrder(contract, buy_order)
        self.ib.placeOrder(contract, stop_order)
        logger.info(f"🕸️ Placed OCO Trap for {ticker} at ${price:.2f} (DAY order)")

    def get_open_positions(self):
        return [p.contract.symbol for p in self.ib.positions() if p.position > 0]

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

    def analyze(self, ticker, df_stock, df_spy):
        if len(df_stock) < 55 or len(df_spy) < 200:
            return None 

        spy_close = df_spy['close'].iloc[-1]
        spy_sma200 = df_spy['close'].rolling(200).mean().iloc[-1]
        macro_safe = spy_close > spy_sma200

        current_close = df_stock['close'].iloc[-1]
        high_20 = df_stock['high'].rolling(20).max().iloc[-2] 
        high_55 = df_stock['high'].rolling(55).max().iloc[-2]
        low_10 = df_stock['low'].rolling(10).min().iloc[-2]
        
        df_stock['prev_close'] = df_stock['close'].shift(1)
        tr = df_stock[['high', 'prev_close']].max(axis=1) - df_stock[['low', 'prev_close']].min(axis=1)
        atr = tr.rolling(20).mean().iloc[-1]

        stock_ret = (current_close / df_stock['close'].iloc[-252]) - 1 if len(df_stock) >= 252 else 0
        spy_ret = (spy_close / df_spy['close'].iloc[-252]) - 1 if len(df_spy) >= 252 else 0
        rs = 50 + ((stock_ret - spy_ret) * 100)
        rs_safe = rs >= 70

        last_won = self.db.get_system_status(ticker)
        entry_price = high_55 if last_won else high_20
        
        risk_amt = self.capital * 0.01
        size = math.floor(risk_amt / atr) if atr > 0 else 0
        is_forced = ticker in self.force_list

        if size > 0:
            if is_forced or (macro_safe and rs_safe):
                if current_close < entry_price: 
                    return {
                        "action": "SET_TRAP", 
                        "current": round(current_close, 2), # Passing current price for the Plan
                        "price": round(entry_price, 2), 
                        "stop": round(low_10, 2), 
                        "size": size, 
                        "rs": round(rs, 1), 
                        "forced": is_forced
                    }
        
        return None

# ==========================================
# 4. THE ORCHESTRATOR (Daily Runner)
# ==========================================
def run_daily_workflow():
    db = DataManager()
    broker = IBBroker(port=4002) 
    
    force_list = ["PLTR", "MSTR"] 
    universe = ["AAPL", "MSFT", "NVDA", "GOOG", "CVX", "JPM", "WM", "COST"]
    all_tickers = ["SPY"] + force_list + universe
    
    print(f"\n{get_us_market_status()}")
    logger.info("--- WAKING UP TRADING BOT ---")
    broker.connect()
    
    capital = db.get_capital()
    logger.info(f"💰 Available Virtual Capital: ${capital:,.2f}")
    
    open_positions = broker.get_open_positions()
    logger.info(f"📂 Current Open Positions in IBKR: {open_positions}")

    if len(open_positions) > 0:
        logger.info("We are already in a trade. Skipping new entries to manage current position.")
        broker.disconnect()
        return

    for ticker in all_tickers:
        local_df = db.load_bars(ticker)
        if len(local_df) < 260:
            logger.info(f"📥 Updating offline memory for {ticker} from IBKR...")
            bars = broker.fetch_missing_bars(ticker, days=260)
            db.save_bars(ticker, bars)

    df_spy = db.load_bars("SPY")

    strategy = TurtleStrategy(db, capital, force_list)
    targets = []

    for ticker in (force_list + universe):
        df_stock = db.load_bars(ticker)
        signal = strategy.analyze(ticker, df_stock, df_spy)
        
        if signal and signal['action'] == "SET_TRAP":
            targets.append((ticker, signal))

    # --- THE UPGRADED PLAN VISUALIZATION ---
    print("\n" + "="*80)
    print("📈 PLAN FOR NEXT TRADING SESSION:")
    print("="*80)
    
    if not targets:
        print("No valid setups found today. The robot will sit safely in cash.")
    else:
        targets.sort(key=lambda x: x[1]['rs'], reverse=True)
        for t, s in targets:
            # Calculate distance to breakout
            dist_dollars = s['price'] - s['current']
            dist_pct = (dist_dollars / s['current']) * 100
            
            force_tag = "[FORCED]" if s['forced'] else ""
            
            print(f"🎯 {t: <5} | Current: ${s['current']:<7.2f} | Buy Stop: ${s['price']:<7.2f} (+${dist_dollars:<5.2f} / +{dist_pct:<5.2f}%) | Risk Stop: ${s['stop']:<7.2f} | Size: {s['size']:<4} | RS: {s['rs']:<4} {force_tag}")
        
        print("="*80)
        choice = input("\nPress ENTER to place OCO DAY Orders for all targets, or type a TICKER to trap only one: ").strip().upper()
        
        if choice in [t[0] for t in targets]:
            print(f"User Override: Locking onto {choice} only.")
            targets = [t for t in targets if t[0] == choice]
        
        for t, s in targets:
            broker.place_oco_buy(t, s['price'], s['size'], s['stop'])
            db.log_trade(t, "DAY_TRAP_PLACED", s['price'])

    broker.disconnect()
    logger.info("💤 Workflow Complete. Bot returning to sleep.")

if __name__ == "__main__":
    run_daily_workflow()