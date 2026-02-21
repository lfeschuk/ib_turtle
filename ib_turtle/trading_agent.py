import sqlite3
import pandas as pd
import logging
import math
from ib_insync import *
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 1. THE MEMORY (DataManager)
# ==========================================
class DataManager:
    def __init__(self, db_name="trading_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_state (ticker TEXT PRIMARY KEY, last_trade_won INTEGER, virtual_capital REAL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trade_log (id INTEGER PRIMARY KEY, date TEXT, ticker TEXT, action TEXT, price REAL)''')
        self.conn.commit()

        # Initialize Virtual Capital to $5,000 if it doesn't exist
        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO bot_state (ticker, last_trade_won, virtual_capital) VALUES ('MASTER_ACCOUNT', 0, 5000.0)")
            self.conn.commit()

    def get_capital(self):
        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        return self.cursor.fetchone()[0]

    def update_capital(self, realized_pnl):
        current = self.get_capital()
        new_cap = current + realized_pnl
        self.cursor.execute("UPDATE bot_state SET virtual_capital = ? WHERE ticker='MASTER_ACCOUNT'", (new_cap,))
        self.conn.commit()

    def get_system_status(self, ticker):
        self.cursor.execute("SELECT last_trade_won FROM bot_state WHERE ticker=?", (ticker,))
        row = self.cursor.fetchone()
        return row[0] if row else 0 # 0 means we use System 1 (20-day), 1 means System 2 (55-day)

    def log_trade(self, ticker, action, price):
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        self.cursor.execute("INSERT INTO trade_log (date, ticker, action, price) VALUES (?, ?, ?, ?)", (date, ticker, action, price))
        self.conn.commit()

# ==========================================
# 2. THE EXECUTOR (IBBroker)
# ==========================================
class IBBroker:
    def __init__(self, port=7497):
        self.ib = IB()
        self.port = port

    def connect(self):
        self.ib.connect('127.0.0.1', self.port, clientId=1, timeout=30)
        logger.info("🟢 Connected to IBKR.")

    def get_bars(self, ticker, days=260):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        bars = self.ib.reqHistoricalData(contract, endDateTime='', durationStr=f'{days} D', barSizeSetting='1 day', whatToShow='TRADES', useRTH=True)
        df = util.df(bars)
        if df is not None and not df.empty:
            df = df[['date', 'open', 'high', 'low', 'close']]
            df.set_index('date', inplace=True)
            return df
        return pd.DataFrame()

    def place_oco_buy(self, ticker, price, size, stop_price):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        # Parent Buy Stop
        buy_order = StopOrder('BUY', size, price)
        buy_order.ocaGroup = "TURTLE_BASKET_" + datetime.datetime.now().strftime('%H%M')
        buy_order.ocaType = 1 # Cancel all others if this fills
        
        # Child Trailing Stop Loss
        stop_order = StopOrder('SELL', size, stop_price)
        stop_order.parentId = buy_order.orderId
        stop_order.transmit = True # Transmit the whole bracket
        
        self.ib.placeOrder(contract, buy_order)
        self.ib.placeOrder(contract, stop_order)
        logger.info(f"🕸️ Placed OCO Trap for {ticker} at ${price:.2f} (Size: {size})")

    def get_open_positions(self):
        return [p.contract.symbol for p in self.ib.positions() if p.position > 0]

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
            return None # Not enough data

        # Calculate SPY Regime
        spy_close = df_spy['close'].iloc[-1]
        spy_sma200 = df_spy['close'].rolling(200).mean().iloc[-1]
        macro_safe = spy_close > spy_sma200

        # Calculate Stock Indicators
        current_close = df_stock['close'].iloc[-1]
        high_20 = df_stock['high'].rolling(20).max().iloc[-2] # High of previous 20 days
        high_55 = df_stock['high'].rolling(55).max().iloc[-2]
        low_10 = df_stock['low'].rolling(10).min().iloc[-2]
        
        # ATR Calculation
        df_stock['prev_close'] = df_stock['close'].shift(1)
        tr = df_stock[['high', 'prev_close']].max(axis=1) - df_stock[['low', 'prev_close']].min(axis=1)
        atr = tr.rolling(20).mean().iloc[-1]

        # Calculate RS (1-Year Proxy)
        stock_ret = (current_close / df_stock['close'].iloc[-252]) - 1 if len(df_stock) >= 252 else 0
        spy_ret = (spy_close / df_spy['close'].iloc[-252]) - 1 if len(df_spy) >= 252 else 0
        rs = 50 + ((stock_ret - spy_ret) * 100)
        rs_safe = rs >= 70

        # Determine Entry Price based on past wins
        last_won = self.db.get_system_status(ticker)
        entry_price = high_55 if last_won else high_20
        
        # Sizing: Risk 1% of Capital
        risk_amt = self.capital * 0.01
        size = math.floor(risk_amt / atr) if atr > 0 else 0

        is_forced = ticker in self.force_list

        # Signal Generation
        if size > 0:
            if is_forced or (macro_safe and rs_safe):
                if current_close < entry_price: # We haven't broken out yet
                    return {"action": "SET_TRAP", "price": round(entry_price, 2), "stop": round(low_10, 2), "size": size, "rs": round(rs, 1), "forced": is_forced}
        
        return None

# ==========================================
# 4. THE ORCHESTRATOR (Daily Runner)
# ==========================================
def run_daily_workflow():
    db = DataManager()
    broker = IBBroker(port=7497)
    
    # Configure your lists here!
    force_list = ["PLTR", "MSTR"] 
    universe = ["AAPL", "MSFT", "NVDA", "GOOG", "CVX", "JPM", "WM", "COST"]
    
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

    logger.info("📥 Fetching SPY Macro Data...")
    df_spy = broker.get_bars("SPY", days=260)

    strategy = TurtleStrategy(db, capital, force_list)
    targets = []

    # Scan the market
    for ticker in (force_list + universe):
        df_stock = broker.get_bars(ticker, days=260)
        signal = strategy.analyze(ticker, df_stock, df_spy)
        
        if signal and signal['action'] == "SET_TRAP":
            targets.append((ticker, signal))

    # Review the Plan
    print("\n" + "="*50)
    print("📈 PLAN FOR TOMORROW:")
    print("="*50)
    
    if not targets:
        print("No setups found. The robot will sit safely in cash.")
    else:
        # Sort by RS
        targets.sort(key=lambda x: x[1]['rs'], reverse=True)
        for t, s in targets:
            force_tag = "[FORCED]" if s['forced'] else ""
            print(f"- {t}: Buy Stop @ ${s['price']} | Size: {s['size']} | RS: {s['rs']} {force_tag}")
        
        print("="*50)
        # Ask for user preference
        choice = input("\nPress ENTER to place OCO net for all targets, or type a preferred TICKER to only trap one: ").strip().upper()
        
        if choice in [t[0] for t in targets]:
            print(f"User Override: Locking onto {choice} only.")
            targets = [t for t in targets if t[0] == choice]
        
        # Fire Orders to IBKR
        for t, s in targets:
            broker.place_oco_buy(t, s['price'], s['size'], s['stop'])
            db.log_trade(t, "OCO_TRAP_PLACED", s['price'])

    broker.disconnect()
    logger.info("💤 Workflow Complete. Bot returning to sleep.")

if __name__ == "__main__":
    run_daily_workflow()