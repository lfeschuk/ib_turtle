import sqlite3
import pandas as pd
import numpy as np
import logging
import math
import datetime
import pytz
from ib_insync import *

# --- SYSTEM SETTINGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('ib_insync').setLevel(logging.WARNING)

# Tickers to trade (Filtered top performers by R2, plus GOOGL and SNDK)
TRADABLE_TICKERS = ['MU', 'QCOM', 'ARM', 'AMD', 'FTNT', 'CSCO', 'DDOG', 'NXPI', 'CRWD', 'SNDK', 'GOOGL']

# ==============================================================================
# 0. MARKET HOURS & STATUS
# ==============================================================================
def get_us_market_status():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.datetime.now(est)
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    if now_est.weekday() >= 5: 
        return "US Market is CLOSED (Weekend)."
    if now_est < market_open:
        return f"US Market is CLOSED (Pre-Market). Strategy triggers at 09:30 EST. Current time EST: {now_est.strftime('%H:%M')}"
    elif market_open <= now_est <= market_close:
        return f"US Market is OPEN. Scanning 11 trend-following stocks for 5m EMA Crossovers."
    else: 
        return "US Market is CLOSED (After-Hours)."

# ==============================================================================
# 1. VISIBLE PROGRESS MEMORY ENGINE (DataManager)
# ==============================================================================
class DataManager:
    def __init__(self, db_name="ema_trading_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Core Tables - Drop bot_state and trade_log on startup to migrate schema cleanly
        self.cursor.execute("DROP TABLE IF EXISTS bot_state")
        self.cursor.execute("DROP TABLE IF EXISTS trade_log")
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_state 
            (ticker TEXT PRIMARY KEY, current_side TEXT, virtual_capital REAL, shares_held INTEGER, last_execution_price REAL, stop_price REAL)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS trade_log 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, ticker TEXT, action TEXT, price REAL, size INTEGER, pnl REAL DEFAULT 0.0, explanation TEXT)''')
        self.conn.commit()

        # Init global capital allocation state if not present
        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO bot_state VALUES ('MASTER_ACCOUNT', 'FLAT', 100000.0, 0, 0.0, NULL)")
            self.conn.commit()

    def get_capital(self):
        self.cursor.execute("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'")
        return self.cursor.fetchone()[0]

    def get_position_state(self, ticker):
        self.cursor.execute("SELECT current_side, shares_held, last_execution_price, stop_price FROM bot_state WHERE ticker=?", (ticker,))
        row = self.cursor.fetchone()
        if row:
            return {"side": row[0], "shares": row[1], "price": row[2], "stop_price": row[3]}
        return {"side": "FLAT", "shares": 0, "price": 0.0, "stop_price": None}

    def get_active_position(self):
        self.cursor.execute("SELECT ticker FROM bot_state WHERE current_side != 'FLAT' AND ticker != 'MASTER_ACCOUNT'")
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    def update_position_state(self, ticker, side, shares, price, stop_price=None):
        self.cursor.execute("INSERT OR REPLACE INTO bot_state (ticker, current_side, virtual_capital, shares_held, last_execution_price, stop_price) VALUES (?, ?, (SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'), ?, ?, ?)",
                            (ticker, side, shares, price, stop_price))
        self.conn.commit()

    def log_transaction(self, ticker, action, price, size, pnl=0.0, explanation=""):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO trade_log (timestamp, ticker, action, price, size, pnl, explanation) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                            (timestamp, ticker, action, price, size, pnl, explanation))
        if pnl != 0.0:
            self.cursor.execute("UPDATE bot_state SET virtual_capital = virtual_capital + ? WHERE ticker='MASTER_ACCOUNT'", (pnl,))
        self.conn.commit()

    def print_visible_ledger(self):
        """Builds a beautiful execution ledger directly inside the terminal window"""
        df = pd.read_sql_query("SELECT timestamp, ticker, action, price, size, pnl, explanation FROM trade_log ORDER BY id DESC LIMIT 10", self.conn)
        print("\n" + "📜" + "="*85 + "📜")
        print(f"{'TIMESTAMP':<20} | {'TICKER':<6} | {'ACTION':<12} | {'PRICE':<8} | {'QTY':<5} | {'REALIZED PNL'}")
        print("-" * 91)
        if df.empty:
            print(f"{'NO EXECUTIONS LOGGED YET. WAITING FOR 5-MIN EMA TRIGGERS...':^91}")
        for _, row in df.iterrows():
            pnl_val = row['pnl']
            pnl_str = f"${pnl_val:+.2f}" if pnl_val != 0.0 else "-"
            print(f"{row['timestamp']:<20} | {row['ticker']:<6} | {row['action']:<12} | {row['price']:<8.2f} | {row['size']:<5} | {pnl_str}")
            explanation = row['explanation'] if row['explanation'] else "No explanation recorded."
            print(f"  └─ 💡 {explanation}")
            print("-" * 91)
        print("="*89)

    def print_performance_dashboard(self):
        df = pd.read_sql_query("SELECT pnl FROM trade_log WHERE pnl != 0.0", self.conn)
        total_capital = self.get_capital()
        
        print("\n📊 CRITICAL METRICS DASHBOARD")
        print(f"• Net Portfolio Standing: ${total_capital:,.2f}")
        if df.empty:
            print("• Win Rate: N/A (No Closed Round-Trip Trades)")
            return
        
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] <= 0]
        win_rate = (len(wins) / len(df)) * 100
        print(f"• Total Complete Trades: {len(df)}")
        print(f"• Win Rate:              {win_rate:.1f}%")
        print(f"• Average Winner:        🟢 ${wins['pnl'].mean():.2f}" if not wins.empty else "• Average Winner: N/A")
        print(f"• Average Loser:         🔴 ${losses['pnl'].mean():.2f}" if not losses.empty else "• Average Loser: N/A")
        print("="*60 + "\n")

# ==============================================================================
# 2. BROAD EXECUTION ENGINE (IBBroker)
# ==============================================================================
class IBBroker:
    def __init__(self, port=4002, client_id=10):
        self.ib = IB()
        self.port = port
        self.client_id = client_id

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', self.port, clientId=self.client_id)
            logger.info(f"🟢 Trading System Active. Connected via Client ID: {self.client_id}")
            
            # Detect if paper account or live account
            accounts = self.ib.managedAccounts()
            self.is_paper = (self.port in [4002, 7497]) or any(acc.upper().startswith(('DU', 'DF')) for acc in accounts)
            
            if self.is_paper:
                logger.info("ℹ️ Paper Trading account detected. Requesting delayed market data (Type 3).")
                self.ib.reqMarketDataType(3)
            else:
                logger.info("ℹ️ Live Trading account detected. Requesting real-time market data (Type 1).")
                self.ib.reqMarketDataType(1)
                
            return True
        except Exception as e:
            logger.error(f"❌ Connection to TWS failed: {e}. Check that API Settings allow port {self.port}")
            return False

    def get_historical_dataframe(self, ticker, duration='5 D', size='5 mins'):
        if self.is_paper:
            # Fetch from Yahoo Finance to avoid paid subscription requirements for paper accounts
            yahoo_interval = '5m'
            if 'hour' in size or '1 hour' in size:
                yahoo_interval = '1h'
            
            yahoo_range = '5d'
            if '20' in duration:
                yahoo_range = '20d'
            elif '3' in duration:
                yahoo_range = '3d'
                
            import urllib.request
            import json
            import pytz
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={yahoo_interval}&range={yahoo_range}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    res = json.loads(response.read().decode())
                    result = res['chart']['result'][0]
                    timestamps = result['timestamp']
                    quote = result['indicators']['quote'][0]
                    opens = quote['open']
                    highs = quote['high']
                    lows = quote['low']
                    closes = quote['close']
                    volumes = quote['volume']
                    
                    records = []
                    est = pytz.timezone('US/Eastern')
                    for i in range(len(timestamps)):
                        if opens[i] is None or closes[i] is None:
                            continue
                        dt = datetime.datetime.fromtimestamp(timestamps[i], datetime.timezone.utc).astimezone(est)
                        records.append({
                            "date": dt,
                            "open": float(opens[i]),
                            "high": float(highs[i]),
                            "low": float(lows[i]),
                            "close": float(closes[i]),
                            "volume": int(volumes[i])
                        })
                    df = pd.DataFrame(records)
                    if not df.empty:
                        df.set_index('date', inplace=True)
                    return df
            except Exception as e:
                logger.error(f"Error fetching Yahoo Finance historical bars for {ticker}: {e}")
            return pd.DataFrame()
        else:
            # Live account with subscriptions
            contract = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            bars = self.ib.reqHistoricalData(
                contract, endDateTime='', durationStr=duration,
                barSizeSetting=size, whatToShow='TRADES', useRTH=True
            )
            if not bars: return pd.DataFrame()
            df = util.asDataFrame(bars)
            df.set_index('date', inplace=True)
            return df

    def fire_market_order(self, ticker, action, size):
        contract = Stock(ticker, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        order = MarketOrder(action, size, tif='DAY')
        trade = self.ib.placeOrder(contract, order)
        logger.info(f"🚀 Fired {action} Market Order for {size} shares of {ticker}.")
        return trade

# ==============================================================================
# 3. LIVE MATHEMATICAL STRATEGY EVALUATOR
# ==============================================================================
def calculate_indicators_and_signal(df_5m, df_1h):
    """Calculates EMA structures across timeframes and returns real-time signals"""
    if df_5m.empty or df_1h.empty:
        return "HOLD", 0.0, 0.0, 0.0

    # 1. Establish 1-Hour Macro Trend Filter (100 EMA - matching our backtested model)
    h1_close = df_1h['close']
    h1_ema100 = h1_close.ewm(span=100, adjust=False).mean()
    macro_trend_bullish = h1_close.iloc[-1] > h1_ema100.iloc[-1]

    # 2. Establish 5-Minute Trigger Lines
    m5_close = df_5m['close']
    ema10 = m5_close.ewm(span=10, adjust=False).mean()
    ema21 = m5_close.ewm(span=21, adjust=False).mean()

    # Peek at current state vs prior state to see crossover
    crossed_above = (ema10.iloc[-1] > ema21.iloc[-1]) and (ema10.iloc[-2] <= ema21.iloc[-2])
    crossed_below = (ema10.iloc[-1] < ema21.iloc[-1]) and (ema10.iloc[-2] >= ema21.iloc[-2])

    current_price = m5_close.iloc[-1]

    # Strategy Evaluation Engine
    if macro_trend_bullish and crossed_above:
        return "LONG_ENTRY", current_price, ema10.iloc[-1], h1_ema100.iloc[-1]
    elif not macro_trend_bullish and crossed_below:
        return "SHORT_ENTRY", current_price, ema10.iloc[-1], h1_ema100.iloc[-1]
    elif crossed_below:
        return "LONG_EXIT", current_price, ema10.iloc[-1], h1_ema100.iloc[-1]
    elif crossed_above:
        return "SHORT_EXIT", current_price, ema10.iloc[-1], h1_ema100.iloc[-1]

    return "HOLD", current_price, ema10.iloc[-1], h1_ema100.iloc[-1]

def calculate_atr_df(df, period=14):
    """Calculates the current ATR for 5m bar dataframe"""
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr.iloc[-1]

# ==============================================================================
# 4. MONITORING AND REAL-TIME EXECUTION ORCHESTRATOR
# ==============================================================================
def run_live_bot():
    heartbeat_ticker = "QQQ"  # QQQ acts as the synchronization heartbeat for 5-minute bars
    db = DataManager()
    broker = IBBroker(port=4002, client_id=15)
    
    if not broker.connect():
        return

    # Print baseline tracking metrics on startup
    db.print_visible_ledger()
    db.print_performance_dashboard()

    print(get_us_market_status())
    logger.info(f"System operational. Listening to QQQ 5-minute heartbeat to trade: {TRADABLE_TICKERS}")

    def scan_and_execute():
        try:
            active_ticker = db.get_active_position()
            
            # --- SCENARIO 1: MANAGE EXISTING ACTIVE POSITION ---
            if active_ticker is not None:
                df_5m = broker.get_historical_dataframe(active_ticker, duration='3 D', size='5 mins')
                df_1h = broker.get_historical_dataframe(active_ticker, duration='20 D', size='1 hour')
                
                if df_5m.empty or df_1h.empty:
                    return
                    
                signal, price, fast_ema, filter_ema = calculate_indicators_and_signal(df_5m, df_1h)
                state = db.get_position_state(active_ticker)
                
                if state["side"] == "LONG":
                    # Check stop loss
                    if state["stop_price"] is not None and price <= state["stop_price"]:
                        explanation = f"STOP LOSS TRIGGERED: Price ({price:.2f}) dropped below ATR stop level ({state['stop_price']:.2f}) for long position."
                        logger.info(f"🚨 {explanation}")
                        broker.fire_market_order(active_ticker, 'SELL', state["shares"])
                        realized_pnl = (price - state["price"]) * state["shares"]
                        db.log_transaction(active_ticker, "SELL_STOP", price, state["shares"], realized_pnl, explanation)
                        db.update_position_state(active_ticker, "FLAT", 0, 0.0, None)
                        db.print_visible_ledger()
                        db.print_performance_dashboard()
                    # Check crossover exit
                    elif signal in ["LONG_EXIT", "SHORT_ENTRY"]:
                        explanation = f"CROSSOVER EXIT: 10 EMA crossed below 21 EMA at price {price:.2f}. Closing long position."
                        logger.info(f"⚠️ {explanation}")
                        broker.fire_market_order(active_ticker, 'SELL', state["shares"])
                        realized_pnl = (price - state["price"]) * state["shares"]
                        db.log_transaction(active_ticker, "SELL_EXIT", price, state["shares"], realized_pnl, explanation)
                        db.update_position_state(active_ticker, "FLAT", 0, 0.0, None)
                        db.print_visible_ledger()
                        db.print_performance_dashboard()
                        
                elif state["side"] == "SHORT":
                    # Check stop loss
                    if state["stop_price"] is not None and price >= state["stop_price"]:
                        explanation = f"STOP LOSS TRIGGERED: Price ({price:.2f}) rose above ATR stop level ({state['stop_price']:.2f}) for short position."
                        logger.info(f"🚨 {explanation}")
                        broker.fire_market_order(active_ticker, 'BUY', state["shares"])
                        realized_pnl = (state["price"] - price) * state["shares"]
                        db.log_transaction(active_ticker, "BUY_STOP", price, state["shares"], realized_pnl, explanation)
                        db.update_position_state(active_ticker, "FLAT", 0, 0.0, None)
                        db.print_visible_ledger()
                        db.print_performance_dashboard()
                    # Check crossover exit
                    elif signal in ["SHORT_EXIT", "LONG_ENTRY"]:
                        explanation = f"CROSSOVER EXIT: 10 EMA crossed above 21 EMA at price {price:.2f}. Covering short position."
                        logger.info(f"⚠️ {explanation}")
                        broker.fire_market_order(active_ticker, 'BUY', state["shares"])
                        realized_pnl = (state["price"] - price) * state["shares"]
                        db.log_transaction(active_ticker, "BUY_COVER", price, state["shares"], realized_pnl, explanation)
                        db.update_position_state(active_ticker, "FLAT", 0, 0.0, None)
                        db.print_visible_ledger()
                        db.print_performance_dashboard()
                        
            # --- SCENARIO 2: FLAT - SCAN tradable list to enter FIRST trigger ---
            else:
                for ticker in TRADABLE_TICKERS:
                    df_5m = broker.get_historical_dataframe(ticker, duration='3 D', size='5 mins')
                    df_1h = broker.get_historical_dataframe(ticker, duration='20 D', size='1 hour')
                    
                    if df_5m.empty or df_1h.empty:
                        continue
                        
                    signal, price, fast_ema, filter_ema = calculate_indicators_and_signal(df_5m, df_1h)
                    
                    if signal in ["LONG_ENTRY", "SHORT_ENTRY"]:
                        atr = calculate_atr_df(df_5m, 14)
                        stop_dist = atr * 2.0
                        
                        # Stop Loss distance filter check: must not exceed 1% of stock price
                        if price > 0 and (stop_dist / price) > 0.01:
                            logger.debug(f"⏭️ [SKIP] {ticker} Stop Loss distance {stop_dist:.2f} exceeds 1% of price {price:.2f}. Volatility too high.")
                            continue
                            
                        capital = db.get_capital()
                        risk_amt = capital * 0.01  # Risk 1% of capital
                        
                        if stop_dist > 0:
                            size = int(risk_amt / stop_dist)
                            max_size = int((capital * 0.95) / price)
                            size = min(size, max_size)
                            
                            if size > 0:
                                if signal == "LONG_ENTRY":
                                    stop_price = price - stop_dist
                                    explanation = f"LONG ENTRY: 10 EMA crossed above 21 EMA. Price ({price:.2f}) > 1h 100EMA ({filter_ema:.2f}). ATR stop loss set at {stop_price:.2f} ({stop_dist:.2f} distance)."
                                    logger.info(f"⚡ {explanation}")
                                    broker.fire_market_order(ticker, 'BUY', size)
                                    db.log_transaction(ticker, "BUY_ENTRY", price, size, 0.0, explanation)
                                    db.update_position_state(ticker, "LONG", size, price, stop_price)
                                    db.print_visible_ledger()
                                    db.print_performance_dashboard()
                                    break  # Enter the first one we see
                                    
                                elif signal == "SHORT_ENTRY":
                                    stop_price = price + stop_dist
                                    explanation = f"SHORT ENTRY: 10 EMA crossed below 21 EMA. Price ({price:.2f}) < 1h 100EMA ({filter_ema:.2f}). ATR stop loss set at {stop_price:.2f} ({stop_dist:.2f} distance)."
                                    logger.info(f"⚡ {explanation}")
                                    broker.fire_market_order(ticker, 'SELL', size)
                                    db.log_transaction(ticker, "SHORT_ENTRY", price, size, 0.0, explanation)
                                    db.update_position_state(ticker, "SHORT", size, price, stop_price)
                                    db.print_visible_ledger()
                                    db.print_performance_dashboard()
                                    break  # Enter the first one we see

        except Exception as err:
            logger.error(f"Error inside live processing loop: {err}")

    if broker.is_paper:
        # Polling heartbeat loop - reqRealTimeBars does not support delayed data on paper accounts.
        # We poll QQQ historical data instead to detect new completed bars.
        logger.info(f"Listening to {heartbeat_ticker} 5-minute heartbeat via delayed polling...")
        last_processed_time = None
        
        try:
            while True:
                broker.ib.sleep(15)  # Yield execution and sleep for 15 seconds
                
                # Fetch latest heartbeat bar
                df_heartbeat = broker.get_historical_dataframe(heartbeat_ticker, duration='1 D', size='5 mins')
                if df_heartbeat.empty:
                    continue
                    
                latest_bar_time = df_heartbeat.index[-1]
                
                if last_processed_time is None:
                    last_processed_time = latest_bar_time
                    logger.info(f"Initialized heartbeat at bar time: {latest_bar_time}")
                    scan_and_execute()
                elif latest_bar_time > last_processed_time:
                    last_processed_time = latest_bar_time
                    scan_and_execute()
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutting down execution arrays smoothly. Tracking state preserved.")
            broker.ib.disconnect()
    else:
        # Live accounts use push-based realtime bars for maximum precision and speed
        logger.info(f"Listening to {heartbeat_ticker} 5-minute heartbeat via push-based real-time bars...")
        heartbeat_contract = Stock(heartbeat_ticker, 'SMART', 'USD')
        broker.ib.qualifyContracts(heartbeat_contract)
        realtime_bars = broker.ib.reqRealTimeBars(heartbeat_contract, 5, 'TRADES', useRTH=True)
        
        def on_bar_update(bars, hasNewBar):
            if hasNewBar:
                scan_and_execute()

        realtime_bars.updateEvent += on_bar_update
        
        try:
            broker.ib.run()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down execution arrays smoothly. Tracking state preserved.")
            broker.ib.cancelRealTimeBars(realtime_bars)
            broker.ib.disconnect()

if __name__ == "__main__":
    run_live_bot()