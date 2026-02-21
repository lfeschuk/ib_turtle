import backtrader as bt
import yfinance as yf
import pandas as pd
import datetime
import math

# --- STRATEGY CLASS ---
class TurtleSystem2Long(bt.Strategy):
    params = (
        ('risk_per_trade', 0.01),  
        ('printlog', True), 
        ('earnings_dates', set()), 
    )

    def __init__(self):
        # 1. Breakout & Volatility Indicators (System 2)
        self.atr = bt.indicators.ATR(self.data, period=20)
        self.H55 = bt.indicators.Highest(self.data.high(-1), period=55) # 55-Day High (Entry)
        self.L20 = bt.indicators.Lowest(self.data.low(-1), period=20)   # 20-Day Low (Exit)

        # 2. State Variables
        self.units_held = 0            
        self.last_buy_price = 0.0      
        
        self.total_cost_basis = 0.0    
        self.trade_list = [] 
        self.pnl_by_year = {}

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        if self.params.printlog:
            print(f'{dt.isoformat()} | {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'[BUY EXECUTED] Price: {order.executed.price:.2f} | Size: {order.executed.size}')
                cost_of_this_buy = order.executed.price * order.executed.size
                self.total_cost_basis += cost_of_this_buy
                self.units_held += 1
                self.last_buy_price = order.executed.price
                
            elif order.issell():
                self.log(f'[SELL EXECUTED] Price: {order.executed.price:.2f} | Size: {order.executed.size}')
                if self.position.size == 0:
                    self.units_held = 0 

            self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        pnl = trade.pnl
        if self.total_cost_basis > 0:
            pnl_pct = (pnl / self.total_cost_basis) * 100
        else:
            pnl_pct = 0.0

        result = "WIN" if pnl > 0 else "LOSS"

        self.log(f'--- TRADE CLOSED ---')
        self.log(f'PnL: ${pnl:.2f} ({pnl_pct:.2f}%) | Result: {result}')
        self.log(f'Total Investment: ${self.total_cost_basis:.2f}')
        self.log(f'--------------------')

        self.trade_list.append(pnl)

        # Record PnL by Year
        current_year = self.datas[0].datetime.date(0).year
        if current_year not in self.pnl_by_year:
            self.pnl_by_year[current_year] = 0.0
        self.pnl_by_year[current_year] += pnl

        self.total_cost_basis = 0.0

    def next(self):
        # 1. Cleanup pending orders
        for order in self.broker.get_orders_open():
            self.broker.cancel(order)
            
        today = self.datas[0].datetime.date(0)
        
        # 2. Earnings Protection Lockdown
        earnings_imminent = any(
            (today + datetime.timedelta(days=i)) in self.params.earnings_dates 
            for i in range(1, 4)
        )

        if earnings_imminent:
            if self.position:
                self.log("⚠️ EARNINGS IMMINENT: Force liquidating position to avoid gap risk.")
                self.close() 
            return 

        # 3. Volatility Check
        n_val = self.atr[0]
        if n_val == 0: return

        # Calculate Unit Size (1% Risk)
        account_value = self.broker.get_value()
        risk_amt = account_value * self.params.risk_per_trade
        unit_size = math.floor(risk_amt / n_val)

        # STATE 1: NO POSITION -> LOOK FOR ENTRY
        if not self.position:
            if unit_size > 0:
                # System 2 Entry: 55-Day High
                self.buy(exectype=bt.Order.Stop, price=self.H55[0], size=unit_size)

        # STATE 2: IN POSITION -> MANAGE EXIT AND PYRAMID
        else:
            # System 2 Exit: 20-Day Low
            stop_price = self.L20[0]
            self.sell(exectype=bt.Order.Stop, price=stop_price, size=self.position.size)
            
            # Pyramiding (Add up to 4 units)
            if self.units_held < 4:
                pyramid_price = self.last_buy_price + (0.5 * n_val)
                if pyramid_price > stop_price:
                    self.buy(exectype=bt.Order.Stop, price=pyramid_price, size=unit_size)

    def stop(self):
        if not self.trade_list:
            print("No trades occurred.")
            return

        wins = [x for x in self.trade_list if x > 0]
        losses = [x for x in self.trade_list if x <= 0]
        total_trades = len(self.trade_list)
        win_rate = len(wins) / total_trades
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        total_pnl = sum(self.trade_list)
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        print("\n========== PNL BY YEAR ==========")
        for year in sorted(self.pnl_by_year.keys()):
            color = "🟢" if self.pnl_by_year[year] > 0 else "🔴"
            print(f"{year}: {color} ${self.pnl_by_year[year]:.2f}")

        print("\n========== FINAL RESULTS ==========")
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate:     {win_rate:.2%}")
        print(f"Total PnL:    ${total_pnl:.2f}")
        print(f"Avg Win:      ${avg_win:.2f}")
        print(f"Avg Loss:     ${avg_loss:.2f}")
        print(f"Expectancy:   ${expectancy:.2f} per trade")
        print("===================================")


# --- RUNNER FUNCTION ---
def run_turtle_backtest(ticker, start, end):
    cerebro = bt.Cerebro()
    
    print(f"Fetching Earnings Calendar for {ticker}...")
    earnings_dates = set()
    try:
        ticker_obj = yf.Ticker(ticker)
        earnings_df = ticker_obj.get_earnings_dates(limit=100) 
        if earnings_df is not None and not earnings_df.empty:
            clean_index = earnings_df.index.tz_localize(None)
            earnings_dates = set([d.date() for d in clean_index])
            print(f"Found {len(earnings_dates)} earnings events for backtest context.")
    except Exception as e:
        print(f"Warning: Could not fetch earnings dates ({e}). Running without earnings protection.")
    
    print(f"Downloading historical price data for {ticker}...")
    df = yf.download(ticker, start=start, end=end, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.addstrategy(TurtleSystem2Long, earnings_dates=earnings_dates)

    cerebro.broker.setcash(100000.0) 
    cerebro.broker.setcommission(commission=0.001, leverage=2.0)

    print(f"Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}")
    cerebro.run()
    print(f"Final Portfolio Value:    ${cerebro.broker.getvalue():.2f}")

# --- CONFIGURATION ---
if __name__ == '__main__':
    run_turtle_backtest(
        ticker="GOOG",           
        start="2025-01-01", 
        end="2026-10-01"
    )