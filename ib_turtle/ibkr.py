import sqlite3
import pandas as pd
import logging
from ib_insync import *
import datetime

# --- LOGGING SETUP ---
# This ensures the bot explains every decision it makes in a clean format.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==========================================
# MODULE 1: THE MEMORY (DataManager)
# ==========================================
class DataManager:
    def __init__(self, db_name="trading_state.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._build_tables()

    def _build_tables(self):
        """Creates the database schema if it doesn't exist yet."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                ticker TEXT,
                date TEXT,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                UNIQUE(ticker, date)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_state (
                ticker TEXT PRIMARY KEY,
                active_system INTEGER,
                units_held INTEGER
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                ticker TEXT,
                action TEXT,
                price REAL,
                size INTEGER,
                reason TEXT
            )
        ''')
        self.conn.commit()
        logger.info(f"💾 Database '{self.db_name}' initialized and verified.")

    def save_bars(self, ticker, bars):
        """Saves daily OHLCV bars into the database. Ignores duplicates."""
        if not bars:
            return
        
        # Insert OR Ignore ensures we don't duplicate data if we run the bot twice in one day
        insert_query = '''
            INSERT OR IGNORE INTO market_data (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        data_to_insert = [
            (ticker, bar.date.strftime('%Y-%m-%d'), bar.open, bar.high, bar.low, bar.close, bar.volume)
            for bar in bars
        ]
        
        self.cursor.executemany(insert_query, data_to_insert)
        self.conn.commit()
        logger.info(f"📊 Saved {len(bars)} days of historical data for {ticker}.")

    def load_bars(self, ticker, limit=60):
        """Loads the most recent bars for a ticker directly into a Pandas DataFrame."""
        query = f"SELECT date, open, high, low, close, volume FROM market_data WHERE ticker = ? ORDER BY date DESC LIMIT {limit}"
        df = pd.read_sql_query(query, self.conn, params=(ticker,))
        
        if df.empty:
            return df
            
        # Sort ascending so the oldest date is at the top (required for Backtrader/Math)
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
        return df

    def clean_removed_tickers(self, active_tickers):
        """Deletes any data for stocks that are no longer in your active lists."""
        # Get all unique tickers currently in the database
        self.cursor.execute("SELECT DISTINCT ticker FROM market_data")
        db_tickers = [row[0] for row in self.cursor.fetchall()]
        
        removed = [t for t in db_tickers if t not in active_tickers]
        
        if removed:
            placeholders = ','.join('?' for _ in removed)
            self.cursor.execute(f"DELETE FROM market_data WHERE ticker IN ({placeholders})", removed)
            self.cursor.execute(f"DELETE FROM bot_state WHERE ticker IN ({placeholders})", removed)
            self.conn.commit()
            logger.info(f"🧹 Cleaned up removed tickers: {removed}")


# ==========================================
# MODULE 2: THE EXECUTOR (IBBroker)
# ==========================================
class IBBroker:
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id

    def connect(self):
        try:
            # timeout=30 gives IBKR time to wake up
            self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=30)
            logger.info("🟢 Successfully connected to Interactive Brokers.")
        except Exception as e:
            logger.error(f"🔴 CRITICAL: Failed to connect to IBKR. Is TWS/Gateway open? Error: {e}")
            raise SystemExit

    def disconnect(self):
        self.ib.disconnect()
        logger.info("🔴 Disconnected from Interactive Brokers.")

    def fetch_daily_history(self, ticker, days_back=60):
        """Fetches historical daily candles from IBKR."""
        contract = Stock(ticker, 'SMART', 'USD')
        
        try:
            # qualifyContracts resolves the contract to get the unique IBKR ID (conId)
            self.ib.qualifyContracts(contract)
        except Exception as e:
            logger.warning(f"⚠️ Could not qualify contract for {ticker}. Check ticker symbol. Error: {e}")
            return []

        logger.info(f"📡 Fetching {days_back} days of history for {ticker}...")
        
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=f'{days_back} D',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        
        if not bars:
            logger.warning(f"⚠️ IBKR returned no data for {ticker}.")
            
        return bars

# ==========================================
# TEST & INITIALIZATION RUNNER
# ==========================================
if __name__ == "__main__":
    # 1. Define your universe and force list
    force_list = ["PLTR", "MSTR"] # Bypasses macro/RS filters
    standard_watchlist = ["AAPL", "MSFT", "NVDA", "SPY"] # SPY is required for Macro filter
    
    all_active_tickers = force_list + standard_watchlist
    
    # 2. Boot up the core modules
    db = DataManager()
    broker = IBBroker(port=7497) # Use 7496 for Live, 7497 for Paper
    
    # 3. Clean up any old garbage data before we start
    db.clean_removed_tickers(all_active_tickers)
    
    # 4. Connect to the market
    broker.connect()
    
    # 5. The Daily Sync: Fetch and save data
    for ticker in all_active_tickers:
        bars = broker.fetch_daily_history(ticker, days_back=65) # Fetch 65 to safely get 55 trading days
        db.save_bars(ticker, bars)
        
        # Verification check
        local_df = db.load_bars(ticker)
        logger.info(f"✅ Verified local DB has {len(local_df)} days of usable data for {ticker}.")

    broker.disconnect()
    logger.info("🏁 Daily Data Sync Complete.")