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
        # --- THE MASTER KEY UPGRADE ---
        self.client_id = 0 

    def connect(self):
        self.ib.connect('127.0.0.1', self.port, clientId=self.client_id, timeout=30)
        logger.info(f"🟢 Connected to IBKR using Master Client ID: {self.client_id}")
        # Command IBKR to hand over control of ALL orders to this script
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

    def get_open_positions(self):
        return [p.contract.symbol for p in self.ib.positions() if p.position > 0]

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
            logger.error(f"🔴 CRITICAL API ERROR: Could not parse open orders. Error: {e}")
            logger.error("🛑 Engaging Fail-Safe: Bot will assume traps are already set to prevent double-ordering.")
            return ['API_ERROR_LOCKOUT']

    def cancel_orders(self, target_tickers):
        if target_tickers == ['ALL']:
            # THE GLOBAL NUKE: Bypasses Client IDs and wipes the entire server board
            self.ib.reqGlobalCancel()
            logger.info("☢️ GLOBAL CANCEL EXECUTED: Commanded IBKR to wipe ALL open orders.")
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
                        logger.info(f"🗑️ Canceled active order for {t.contract.symbol}")
                        count += 1
            self.ib.sleep(1)
            if count > 0: print(f"✅ Successfully sent cancel request for {count} specific order(s).")

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
                    logger.info(f"💥 Liquidating {p.position} shares of {ticker} at MARKET price.")
                    count += 1
        self.ib.sleep(1)
        if count > 0: print(f"✅ Successfully fired {count} Market Sell order(s).")

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
        adx = dx.ewm(alpha=1/period, adjust=False).mean()
        return adx.iloc[-1]

    def get_spy_status(self, df_spy):
        if len(df_spy) < 200: return "Not enough data for SPY Macro."
        
        close = df_spy['close'].iloc[-1]
        sma50 = df_spy['close'].rolling(50).mean()
        sma200 = df_spy['close'].rolling(200).mean()
        
        curr_sma50 = sma50.iloc[-1]
        curr_sma200 = sma200.iloc[-1]
        
        days_above_50 = self._calc_days_above(df_spy['close'], sma50)
        days_above_200 = self._calc_days_above(df_spy['close'], sma200)
        
        macro_safe = close > curr_sma50 and curr_sma50 > curr_sma200
        status_icon = "🟢 BULL REGIME" if macro_safe else "🔴 BEAR/CHOP REGIME (Cash Only)"
        
        return (f"{status_icon}\n"
                f"Current: ${close:.2f} | 50d SMA: ${curr_sma50:.2f} | 200d SMA: ${curr_sma200:.2f}\n"
                f"SPY is > 50d for [{days_above_50}] days | > 200d for [{days_above_200}] days.")

    def analyze(self, ticker, df_stock, df_spy):
        if len(df_stock) < 200 or len(df_spy) < 200:
            return None 

        spy_close = df_spy['close'].iloc[-1]
        spy_sma200 = df_spy['close'].rolling(200).mean().iloc[-1]
        macro_safe = spy_close > spy_sma200

        current_close = df_stock['close'].iloc[-1]
        high_20 = df_stock['high'].rolling(20).max().iloc[-2] 
        high_55 = df_stock['high'].rolling(55).max().iloc[-2]
        low_10 = df_stock['low'].rolling(10).min().iloc[-2]
        
        sma50 = df_stock['close'].rolling(50).mean()
        sma200 = df_stock['close'].rolling(200).mean()
        curr_sma50 = sma50.iloc[-1]
        curr_sma200 = sma200.iloc[-1]
        
        dist_50 = ((current_close / curr_sma50) - 1) * 100 if curr_sma50 > 0 else 0
        dist_200 = ((current_close / curr_sma200) - 1) * 100 if curr_sma200 > 0 else 0
        days_50 = self._calc_days_above(df_stock['close'], sma50)
        days_200 = self._calc_days_above(df_stock['close'], sma200)
        adx_val = self._calc_adx(df_stock, 14)
        
        df_stock['prev_close'] = df_stock['close'].shift(1)
        tr = df_stock[['high', 'prev_close']].max(axis=1) - df_stock[['low', 'prev_close']].min(axis=1)
        atr = tr.rolling(20).mean().iloc[-1]

        stock_ret = (current_close / df_stock['close'].iloc[-252]) - 1 if len(df_stock) >= 252 else 0
        spy_ret = (spy_close / df_spy['close'].iloc[-252]) - 1 if len(df_spy) >= 252 else 0
        rs = 50 + ((stock_ret - spy_ret) * 100)
        rs_safe = rs >= 70

        last_won = self.db.get_system_status(ticker)
        system_type = "S2 (55d)" if last_won else "S1 (20d)"
        entry_price = high_55 if last_won else high_20
        
        risk_amt = self.capital * 0.01
        size = math.floor(risk_amt / atr) if atr > 0 else 0
        is_forced = ticker in self.force_list

        if size > 0:
            if is_forced or (macro_safe and rs_safe):
                if current_close < entry_price: 
                    return {
                        "action": "SET_TRAP", 
                        "sys": system_type,
                        "current": round(current_close, 2), 
                        "price": round(entry_price, 2), 
                        "stop": round(low_10, 2), 
                        "size": size, 
                        "rs": round(rs, 1), 
                        "adx": round(adx_val, 1),
                        "dist_50": round(dist_50, 1),
                        "dist_200": round(dist_200, 1),
                        "days_50": days_50,
                        "days_200": days_200,
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
    if open_positions:
        print("\n" + "="*60)
        print(f"📂 ACTIVE POSITIONS: {open_positions}")
        print("="*60)
        choice = input("Type TICKERS to LIQUIDATE (e.g. MSFT,AAPL), 'ALL', or press ENTER to hold: ").strip().upper()
        if choice:
            targets = ['ALL'] if choice == 'ALL' else [x.strip() for x in choice.split(',')]
            broker.liquidate_positions(targets)
            db.log_trade("MANUAL_LIQUIDATE", str(targets), 0)
            print("⏳ Waiting for IBKR server to process liquidation...")
            broker.ib.sleep(3) 
            open_positions = broker.get_open_positions() 

    pending_orders = broker.get_pending_orders()
    if pending_orders and 'API_ERROR_LOCKOUT' not in pending_orders:
        print("\n" + "="*60)
        print(f"⏳ PENDING ORDERS/TRAPS: {pending_orders}")
        print("="*60)
        choice = input("Type TICKERS to CANCEL orders for (e.g. GOOG,NVDA), 'ALL', or press ENTER to keep them: ").strip().upper()
        if choice:
            targets = ['ALL'] if choice == 'ALL' else [x.strip() for x in choice.split(',')]
            broker.cancel_orders(targets)
            db.log_trade("MANUAL_CANCEL", str(targets), 0)
            
            # --- THE SERVER SYNC DELAY FIX ---
            print("⏳ Waiting for IBKR server to process cancellations...")
            broker.ib.sleep(3) 
            
            pending_orders = broker.get_pending_orders() 

    # -----------------------------------------------------
    # THE SCANNER & PLAN EXECUTION
    # -----------------------------------------------------
    if len(open_positions) == 0 and len(pending_orders) == 0:
        for ticker in all_tickers:
            local_df = db.load_bars(ticker)
            if len(local_df) < 300:
                logger.info(f"📥 Updating offline memory for {ticker} from IBKR...")
                bars = broker.fetch_missing_bars(ticker, days=300)
                db.save_bars(ticker, bars)

        df_spy = db.load_bars("SPY")
        strategy = TurtleStrategy(db, capital, force_list)
        
        print("\n" + "="*80)
        print("🇺🇸 SPY MACRO STATUS:")
        print("-" * 80)
        print(strategy.get_spy_status(df_spy))
        print("="*80)

        targets = []
        for ticker in (force_list + universe):
            df_stock = db.load_bars(ticker)
            signal = strategy.analyze(ticker, df_stock, df_spy)
            
            if signal and signal['action'] == "SET_TRAP":
                targets.append((ticker, signal))

        print("\n" + "="*125)
        print("📈 PLAN FOR NEXT TRADING SESSION:")
        print("="*125)
        
        if not targets:
            print("No valid setups found today. The robot will sit safely in cash.")
        else:
            targets.sort(key=lambda x: x[1]['rs'], reverse=True)
            for t, s in targets:
                dist_pct = ((s['price'] / s['current']) - 1) * 100
                force_tag = "[FORCED]" if s['forced'] else ""
                print(f"🎯 {t: <5} | {s['sys']} | Buy: ${s['price']:<7.2f} (+{dist_pct:<4.1f}%) | ADX: {s['adx']:<4.1f} | RS: {s['rs']:<4.1f} | >50d: {s['days_50']:<3} (+{s['dist_50']:>4.1f}%) | >200d: {s['days_200']:<3} (+{s['dist_200']:>4.1f}%) {force_tag}")
            
            print("="*125)
            
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
        
        print("\n" + "🚨"*20)
        logger.info(f"LIVE EXECUTION ALERT: Order Filled!")
        logger.info(f"Action: {side} | Ticker: {ticker} | Price: ${price:.2f}")
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