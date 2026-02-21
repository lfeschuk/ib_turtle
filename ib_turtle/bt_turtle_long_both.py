import backtrader as bt
import yfinance as yf
import pandas as pd
import datetime
import math

# --- STRATEGY CLASS ---
class TurtleUnifiedLong(bt.Strategy):
    params = (
        ('risk_per_trade', 0.01),  
        ('printlog', True),
        ('filter_win_pct', 0.0),  
        ('earnings_dates', set()), 
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(self.data, period=20)
        
        self.H20 = bt.indicators.Highest(self.data.high(-1), period=20) 
        self.L10 = bt.indicators.Lowest(self.data.low(-1), period=10)   
        
        self.H55 = bt.indicators.Highest(self.data.high(-1), period=55) 
        self.L20 = bt.indicators.Lowest(self.data.low(-1), period=20)   

        self.sys1_filtered = False     
        self.active_system = None      
        self.units_held = 0            
        self.last_buy_price = 0.0      
        
        self.total_cost_basis = 0.0    
        self.trade_list = [] 
        self.pnl_by_year = {}

        self.virtual_active = False
        self.virtual_entry_price = 0.0
        self.virtual_stop_price = 0.0

        self.s1_entry_order = None
        self.s2_entry_order = None
        self.pyramid_order = None
        self.exit_order = None
        self.s2_transition_order = None
        
        # --- NEW: TRACK DATES FOR CAGR MATH ---
        self.start_date = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        if self.params.printlog:
            print(f'{dt.isoformat()} | {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                if order == self.s1_entry_order:
                    self.active_system = 1
                    self.log(f'🟢 [SYS 1 ENTRY] Breakout at 20-Day High | Price: {order.executed.price:.2f} | Size: {order.executed.size}')
                
                elif order == self.s2_entry_order:
                    self.active_system = 2
                    self.log(f'🔥 [SYS 2 ENTRY] FILTER IGNORED! Breakout at 55-Day High | Price: {order.executed.price:.2f} | Size: {order.executed.size}')
                
                elif order == self.pyramid_order:
                    self.log(f'🔼 [PYRAMID BUY] Adding Unit {self.units_held + 1} | Price: {order.executed.price:.2f} | Size: {order.executed.size}')
                
                else:
                    self.log(f'[BUY EXECUTED] Price: {order.executed.price:.2f} | Size: {order.executed.size}')

                cost_of_this_buy = order.executed.price * order.executed.size
                self.total_cost_basis += cost_of_this_buy
                self.units_held += 1
                self.last_buy_price = order.executed.price
                
            elif order.issell():
                if order == self.exit_order:
                    stop_days = "10-Day" if self.active_system == 1 else "20-Day"
                    self.log(f'🛡️ [SYS {self.active_system} EXIT] Hit {stop_days} Trailing Stop | Price: {order.executed.price:.2f} | Size: {order.executed.size}')
                
                elif order == self.s2_transition_order:
                    self.log(f'💰 [TRANSITION SELL] Dumped excess units. Secured profit! | Price: {order.executed.price:.2f} | Size: {order.executed.size}')
                    
                else:
                    self.log(f'🛑 [FORCE EXIT] Liquidated | Price: {order.executed.price:.2f} | Size: {order.executed.size}')

                if self.position.size == 0:
                    self.units_held = 0 
                    self.active_system = None 

            self.s1_entry_order = None
            self.s2_entry_order = None
            self.pyramid_order = None
            self.exit_order = None
            self.s2_transition_order = None

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

        current_year = self.datas[0].datetime.date(0).year
        if current_year not in self.pnl_by_year:
            self.pnl_by_year[current_year] = 0.0
        self.pnl_by_year[current_year] += pnl

        if pnl_pct >= self.params.filter_win_pct:
            self.sys1_filtered = True
            self.log(f"🧠 Logic: WIN >= {self.params.filter_win_pct}%. Filter is ON.")
        else:
            self.sys1_filtered = False
            self.log(f"🧠 Logic: Result < {self.params.filter_win_pct}%. Filter is OFF.")

        self.total_cost_basis = 0.0

    def next(self):
        for order in self.broker.get_orders_open():
            self.broker.cancel(order)
            
        today = self.datas[0].datetime.date(0)
        
        # Capture the very first day the strategy actually starts running
        if self.start_date is None:
            self.start_date = today
        
        earnings_imminent = any(
            (today + datetime.timedelta(days=i)) in self.params.earnings_dates 
            for i in range(1, 4)
        )

        if self.sys1_filtered:
            if not self.virtual_active:
                if self.data.high[0] > self.H20[0]:
                    self.virtual_active = True
                    self.virtual_entry_price = self.H20[0]
                    self.virtual_stop_price = self.L10[0] 
                    self.log(f"👻 [SHADOW] Virtual Sys 1 BUY triggered at {self.virtual_entry_price:.2f}")
            else:
                self.virtual_stop_price = max(self.virtual_stop_price, self.L10[0])
                if self.data.low[0] < self.virtual_stop_price:
                    virtual_pnl = self.virtual_stop_price - self.virtual_entry_price
                    virtual_pnl_pct = (virtual_pnl / self.virtual_entry_price) * 100 if self.virtual_entry_price > 0 else 0.0
                    self.virtual_active = False
                    
                    if virtual_pnl_pct < self.params.filter_win_pct:
                        self.sys1_filtered = False
                        self.log(f"👻 [SHADOW] Virtual Trade failed ({virtual_pnl_pct:.2f}%). Filter RESET.")
                    else:
                        self.log(f"👻 [SHADOW] Virtual Trade WIN. Filter stays ON.")

        # if earnings_imminent:
        #     if self.position:
        #         self.log("⚠️ EARNINGS IMMINENT: Force liquidating position to avoid gap risk.")
        #         self.close() 
        #     return 

        n_val = self.atr[0]
        if n_val == 0: return

        account_value = self.broker.get_value()
        risk_amt = account_value * self.params.risk_per_trade
        unit_size = math.floor(risk_amt / n_val)

        # STATE 1: NO POSITION -> LOOK FOR ENTRY
        if not self.position:
            if unit_size > 0:
                if not self.sys1_filtered:
                    self.s1_entry_order = self.buy(exectype=bt.Order.Stop, price=self.H20[0], size=unit_size)
                else:
                    self.s2_entry_order = self.buy(exectype=bt.Order.Stop, price=self.H55[0], size=unit_size)

        # STATE 2: IN POSITION -> MANAGE EXIT AND PYRAMID
        else:
            target_size = self.position.size

            if self.active_system == 1 and self.data.high[0] >= self.H55[0]:
                self.log(f'🔄 [TRANSITION] 55-Day Breakout Hit! Morphing Sys 1 trade into Sys 2.')
                
                self.active_system = 2
                self.last_buy_price = self.H55[0] 
                
                if self.units_held > 1:
                    one_unit_size = self.position.size // self.units_held
                    excess_size = self.position.size - one_unit_size
                    
                    if excess_size > 0:
                        self.s2_transition_order = self.sell(size=excess_size)
                        self.log(f'📉 [TAKE PROFIT] Dumping {self.units_held - 1} excess units ({excess_size} shares). Leaving 1 unit to ride.')
                        
                        target_size = one_unit_size 

                self.units_held = 1

            stop_price = self.L10[0] if self.active_system == 1 else self.L20[0]
            self.exit_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=target_size)
            
            if self.units_held < 4:
                pyramid_price = self.last_buy_price + (0.5 * n_val)
                if pyramid_price > stop_price:
                    self.pyramid_order = self.buy(exectype=bt.Order.Stop, price=pyramid_price, size=unit_size)

    def stop(self):
        # --- NEW: CALCULATE CAGR ---
        end_date = self.datas[0].datetime.date(0)
        total_days = (end_date - self.start_date).days if self.start_date else 0
        total_years = total_days / 365.25 if total_days > 0 else 1
        
        start_value = self.broker.startingcash
        end_value = self.broker.getvalue()
        
        if start_value > 0 and total_years > 0:
            cagr = ((end_value / start_value) ** (1 / total_years)) - 1
        else:
            cagr = 0.0

        if not self.trade_list:
            print("No trades occurred.")
            return

        wins = [x for x in self.trade_list if x > 0]
        losses = [x for x in self.trade_list if x <= 0]
        total_trades = len(self.trade_list)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
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
        print(f"CAGR:         {cagr:.2%}")   # <--- PRINT CAGR HERE
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
    except Exception as e:
        print(f"Warning: Could not fetch earnings dates ({e}). Running without earnings protection.")
    
    print(f"Downloading historical price data for {ticker}...")
    df = yf.download(ticker, start=start, end=end, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.addstrategy(TurtleUnifiedLong, earnings_dates=earnings_dates)

    cerebro.broker.setcash(100000.0) 
    cerebro.broker.setcommission(commission=0.001, leverage=2.0)

    print(f"Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}")
    cerebro.run()
    print(f"Final Portfolio Value:    ${cerebro.broker.getvalue():.2f}")

# --- CONFIGURATION ---
if __name__ == '__main__':
    run_turtle_backtest(
        ticker="GOOG",           
        start="2020-01-01", 
        end="2026-01-01"
    )