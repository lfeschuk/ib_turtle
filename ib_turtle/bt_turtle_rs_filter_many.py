import backtrader as bt
import yfinance as yf
import pandas as pd
import datetime
import math

# --- CUSTOM ROLLING RS INDICATOR ---
class RSProxy(bt.Indicator):
    lines = ('rs',)
    params = (('period', 252),) 

    def __init__(self):
        self.addminperiod(self.p.period)

    def next(self):
        stock_ret = ((self.data0.close[0] / self.data0.close[-self.p.period]) - 1) * 100
        spy_ret = ((self.data1.close[0] / self.data1.close[-self.p.period]) - 1) * 100
        
        raw = 50 + stock_ret - spy_ret
        self.lines.rs[0] = max(1, min(99, raw))

# --- PORTFOLIO STRATEGY CLASS ---
class TurtlePortfolioManager(bt.Strategy):
    params = (
        ('risk_per_trade', 0.01),  
        ('printlog', False), 
        ('rs_threshold', 70),
        ('mom_period', 63),
        ('max_oco_orders', 3), 
        ('debug_year', 2025), # <--- NEW: Only print detailed logs for this year
    )

    def __init__(self):
        self.spy = self.datas[0] 
        self.inds = {}
        self.sys1_filtered = {}
        
        for d in self.datas[1:]:
            self.sys1_filtered[d._name] = False
            rs = RSProxy(d, self.spy, period=252)
            
            self.inds[d._name] = {
                'atr': bt.indicators.ATR(d, period=20),
                'H20': bt.indicators.Highest(d.high(-1), period=20),
                'L10': bt.indicators.Lowest(d.low(-1), period=10),
                'H55': bt.indicators.Highest(d.high(-1), period=55),
                'L20': bt.indicators.Lowest(d.low(-1), period=20),
                'rs': rs,
                'mom': bt.indicators.Momentum(rs.rs, period=self.params.mom_period)
            }

        self.active_ticker = None      
        self.units_held = 0            
        self.last_buy_price = 0.0      
        self.active_system = None
        self.total_cost_basis = 0.0    
        
        self.entry_orders = [] 
        self.pyramid_order = None
        self.exit_order = None
        self.transition_order = None

        self.yearly_pnl_by_stock = {}  
        self.year_starts = {}
        self.year_ends = {}
        self.start_date = None

    def prenext(self):
        self.next()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            ticker = order.data._name
            order_date = order.data.datetime.date(0)
            
            if order.isbuy():
                if order in self.entry_orders:
                    self.active_ticker = ticker
                    self.units_held = 1
                    self.active_system = getattr(order, 'sys_type', 1) 
                    self.entry_orders = [] 
                    
                    # --- DEBUG PRINT: CAUGHT THE BREAKOUT ---
                    if order_date.year == self.params.debug_year:
                        print(f"  🎯 [{order_date}] TRIGGERED: Bought {ticker} @ ${order.executed.price:.2f}")
                    
                elif order == self.pyramid_order:
                    self.units_held += 1
                    
                cost_of_this_buy = order.executed.price * order.executed.size
                self.total_cost_basis += cost_of_this_buy
                self.last_buy_price = order.executed.price
                
            elif order.issell():
                if self.getposition(order.data).size == 0:
                    
                    # --- DEBUG PRINT: EXITED TRADE ---
                    if order_date.year == self.params.debug_year:
                        print(f"  🛑 [{order_date}] EXITED: Sold {ticker} @ ${order.executed.price:.2f} (Back to Cash)")
                        
                    self.active_ticker = None
                    self.units_held = 0 
                    self.active_system = None 

            self.pyramid_order = None
            self.exit_order = None
            self.transition_order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        ticker = trade.data._name
        pnl = trade.pnl
        pnl_pct = (pnl / self.total_cost_basis) * 100 if self.total_cost_basis > 0 else 0.0

        if pnl_pct >= 0.0:
            self.sys1_filtered[ticker] = True
        else:
            self.sys1_filtered[ticker] = False

        year = trade.data.datetime.date(0).year
        if year not in self.yearly_pnl_by_stock:
            self.yearly_pnl_by_stock[year] = {}
        if ticker not in self.yearly_pnl_by_stock[year]:
            self.yearly_pnl_by_stock[year][ticker] = 0.0
            
        self.yearly_pnl_by_stock[year][ticker] += pnl
        self.total_cost_basis = 0.0

    def next(self):
        if len(self.spy) < 315: return 

        for order in self.broker.get_orders_open():
            self.broker.cancel(order)
            
        today = self.spy.datetime.date(0)
        curr_year = today.year
        
        if curr_year not in self.year_starts:
            self.year_starts[curr_year] = self.broker.get_value()
        self.year_ends[curr_year] = self.broker.get_value()
        
        if self.start_date is None:
            self.start_date = today

        # ==========================================
        # STATE 1: SITTING ON CASH -> CAST THE OCO NET
        # ==========================================
        if self.active_ticker is None:
            candidates = []
            
            for d in self.datas[1:]:
                if len(d) < 315: 
                    continue

                ticker = d._name
                inds = self.inds[ticker]
                
                if math.isnan(inds['rs'].rs[0]) or math.isnan(inds['mom'][0]): 
                    continue
                
                if inds['rs'].rs[0] >= self.params.rs_threshold and inds['mom'][0] > 0:
                    candidates.append((d, inds['rs'].rs[0]))
            
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                top_candidates = candidates[:self.params.max_oco_orders]
                
                # --- DEBUG PRINT: THE DAILY SCANNER ---
                if curr_year == self.params.debug_year:
                    passing_str = ", ".join([f"{c[0]._name}({c[1]:.0f})" for c in candidates])
                    traps_str = ", ".join([c[0]._name for c in top_candidates])
                    print(f"\n🔍 [{today}] SCANNER: Passing RS>70: [{passing_str}]")
                    print(f"   => Setting OCO Breakout Traps for: [{traps_str}]")
                
                oco_base = None
                self.entry_orders = []
                
                for c in top_candidates:
                    winner_d = c[0]
                    ticker = winner_d._name
                    inds = self.inds[ticker]
                    
                    n_val = inds['atr'][0]
                    if n_val == 0: continue
                    
                    risk_amt = self.broker.get_value() * self.params.risk_per_trade
                    unit_size = math.floor(risk_amt / n_val)
                    if unit_size <= 0: continue
                    
                    sys_type = 2 if self.sys1_filtered[ticker] else 1
                    entry_price = inds['H55'][0] if sys_type == 2 else inds['H20'][0]
                    
                    if oco_base is None:
                        oco_base = self.buy(data=winner_d, exectype=bt.Order.Stop, price=entry_price, size=unit_size)
                        oco_base.sys_type = sys_type
                        self.entry_orders.append(oco_base)
                    else:
                        order = self.buy(data=winner_d, exectype=bt.Order.Stop, price=entry_price, size=unit_size, oco=oco_base)
                        order.sys_type = sys_type
                        self.entry_orders.append(order)

        # ==========================================
        # STATE 2: IN A TRADE -> MANAGE THE POSITION
        # ==========================================
        else:
            d = self.getdatabyname(self.active_ticker)
            inds = self.inds[self.active_ticker]
            target_size = self.getposition(d).size

            if self.active_system == 1 and d.high[0] >= inds['H55'][0]:
                self.active_system = 2
                self.last_buy_price = inds['H55'][0] 
                
                if self.units_held > 1:
                    one_unit_size = target_size // self.units_held
                    excess_size = target_size - one_unit_size
                    if excess_size > 0:
                        self.transition_order = self.sell(data=d, size=excess_size)
                        target_size = one_unit_size 
                self.units_held = 1

            stop_price = inds['L10'][0] if self.active_system == 1 else inds['L20'][0]
            self.exit_order = self.sell(data=d, exectype=bt.Order.Stop, price=stop_price, size=target_size)
            
            if self.units_held < 4:
                n_val = inds['atr'][0]
                pyramid_price = self.last_buy_price + (0.5 * n_val)
                if pyramid_price > stop_price:
                    risk_amt = self.broker.get_value() * self.params.risk_per_trade
                    unit_size = math.floor(risk_amt / n_val)
                    self.pyramid_order = self.buy(data=d, exectype=bt.Order.Stop, price=pyramid_price, size=unit_size)

    def stop(self):
        print("\n" + "="*70)
        print("========== YEARLY PORTFOLIO MVP REPORT ==========")
        print("="*70)
        
        for year in sorted(self.year_starts.keys()):
            start_val = self.year_starts[year]
            end_val = self.year_ends.get(year, start_val)
            pct_return = ((end_val / start_val) - 1) * 100
            
            color = "🟢" if pct_return > 0 else "🔴"
            
            best_stock = "None"
            best_pnl = 0.0
            
            if year in self.yearly_pnl_by_stock and self.yearly_pnl_by_stock[year]:
                sorted_stocks = sorted(self.yearly_pnl_by_stock[year].items(), key=lambda item: item[1], reverse=True)
                best_stock = sorted_stocks[0][0]
                best_pnl = sorted_stocks[0][1]
            
            print(f"{year:<5} | Port Return: {color} {pct_return:>6.2f}% | MVP Stock: {best_stock:<5} (+${best_pnl:,.2f})")

        print("="*70)
        
        start_value = self.broker.startingcash
        end_value = self.broker.getvalue()
        total_days = (self.spy.datetime.date(0) - self.start_date).days if self.start_date else 0
        years = total_days / 365.25 if total_days > 0 else 1
        cagr = ((end_value / start_value) ** (1 / years)) - 1 if start_value > 0 and years > 0 else 0.0
        
        print(f"\nFINAL PORTFOLIO VALUE: ${end_value:,.2f}")
        print(f"PORTFOLIO CAGR:        {cagr:.2%}")


def run_portfolio(start, end):
    cerebro = bt.Cerebro()
    
    start_dt = datetime.datetime.strptime(start, "%Y-%m-%d")
    warmup_dt = start_dt - datetime.timedelta(days=450)
    warmup_start = warmup_dt.strftime("%Y-%m-%d")
    
    # The complete 40-stock universe
    tickers = [
        "AAPL", "MSFT", "NVDA", "GOOG", "META", 
        "XOM", "CVX", "SLB",                    
        "FCX", "NEM",                           
        "JPM", "V", "MA",                       
        "JNJ", "LLY", "UNH",                    
        "WMT", "COST", "HD", "PG"   
    ]
    


    print(f"Downloading SPY and {len(tickers)} stocks starting from {warmup_start}...")
    
    df_spy = yf.download("SPY", start=warmup_start, end=end, progress=False)
    if isinstance(df_spy.columns, pd.MultiIndex):
        df_spy.columns = df_spy.columns.get_level_values(0)
    cerebro.adddata(bt.feeds.PandasData(dataname=df_spy), name="SPY")

    for ticker in tickers:
        df = yf.download(ticker, start=warmup_start, end=end, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            cerebro.adddata(bt.feeds.PandasData(dataname=df), name=ticker)

    cerebro.addstrategy(TurtlePortfolioManager)
    cerebro.broker.setcash(100000.0) 
    cerebro.broker.setcommission(commission=0.001, leverage=2.0)

    print(f"\nIgniting Scanner Debugger for 2025. Stand by...")
    cerebro.run()

# --- CONFIGURATION ---
if __name__ == '__main__':
    run_portfolio(
        start="2008-01-01", 
        end="2026-01-01"
    )