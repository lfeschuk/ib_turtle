import pandas as pd
import numpy as np

def load_and_preprocess_data(csv_path="spx_vix_hourly.csv"):
    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date'])
    return df

def run_orb_simulation(df, range_duration_hours, stop_loss_type, profit_target_mult, vix_threshold=20.0):
    # In our hourly data:
    # - range_duration_hours = 1: Range is defined by the 09:30:00 bar (representing 9:30-10:30)
    # - range_duration_hours = 2: Range is defined by the 09:30:00 and 10:30:00 bars (representing 9:30-11:30)
    
    dates = df['Date'].unique()
    trades_executed = []
    
    for dt in dates:
        day_df = df[df['Date'] == dt].sort_values('Time').copy()
        if len(day_df) < 5:
            continue
            
        bar_0930 = day_df[day_df['Time'] == '09:30:00']
        bar_1530 = day_df[day_df['Time'] == '15:30:00']
        
        if bar_0930.empty or bar_1530.empty:
            continue
            
        vix_entry = bar_0930['VIX_Open'].values[0]
        if vix_entry <= vix_threshold:
            continue
            
        # Define range high and low
        if range_duration_hours == 1:
            range_high = bar_0930['SPX_High'].values[0]
            range_low = bar_0930['SPX_Low'].values[0]
            subsequent_bars = day_df[~day_df['Time'].isin(['09:30:00', '15:30:00'])]
        else: # 2 hours
            bar_1030 = day_df[day_df['Time'] == '10:30:00']
            if bar_1030.empty:
                continue
            range_high = max(bar_0930['SPX_High'].values[0], bar_1030['SPX_High'].values[0])
            range_low = min(bar_0930['SPX_Low'].values[0], bar_1030['SPX_Low'].values[0])
            subsequent_bars = day_df[~day_df['Time'].isin(['09:30:00', '10:30:00', '15:30:00'])]
            
        range_size = range_high - range_low
        if range_size <= 0:
            continue
            
        day_close = bar_1530['SPX_Close'].values[0]
        
        triggered = False
        position = 0 # +1 for Long, -1 for Short
        entry_price = 0.0
        
        for idx, bar in subsequent_bars.iterrows():
            high_val = bar['SPX_High']
            low_val = bar['SPX_Low']
            
            # Check Long Breakout
            if high_val > range_high:
                triggered = True
                position = 1
                entry_price = range_high
                break
            # Check Short Breakout
            elif low_val < range_low:
                triggered = True
                position = -1
                entry_price = range_low
                break
                
        if triggered:
            # Set target and stop loss levels
            # Profit Target
            if profit_target_mult > 0:
                target_level = entry_price + (range_size * profit_target_mult * position)
            else:
                target_level = None
                
            # Stop Loss Level
            if stop_loss_type == 'opposite_range':
                stop_level = range_low if position == 1 else range_high
            elif stop_loss_type == 'half_range':
                stop_level = entry_price - (range_size * 0.5 * position)
            else: # 0.5% Fixed
                stop_level = entry_price * (1.0 - 0.005 * position)
                
            pnl = 0.0
            exited = False
            
            # Walk through subsequent bars to check for stop loss or target hits
            for idx, bar in subsequent_bars.iterrows():
                high_val = bar['SPX_High']
                low_val = bar['SPX_Low']
                
                # Check Stop Loss First (Conservative)
                if position == 1:
                    if low_val <= stop_level:
                        pnl = stop_level - entry_price
                        exited = True
                        break
                    if target_level and high_val >= target_level:
                        pnl = target_level - entry_price
                        exited = True
                        break
                else: # Short
                    if high_val >= stop_level:
                        pnl = entry_price - stop_level
                        exited = True
                        break
                    if target_level and low_val <= target_level:
                        pnl = entry_price - target_level
                        exited = True
                        break
            
            # If not exited during the day, exit at close
            if not exited:
                pnl = (day_close - entry_price) if position == 1 else (entry_price - day_close)
                
            # Subtract 0.50 points index slippage per trade
            pnl -= 0.50
            
            trades_executed.append({
                "Date": dt,
                "PnL": pnl,
                "Win": 1 if pnl > 0 else 0
            })
            
    if not trades_executed:
        return 0, 0.0, 0.0, 0.0
        
    trade_df = pd.DataFrame(trades_executed)
    total_trades = len(trade_df)
    win_rate = trade_df['Win'].sum() / total_trades
    total_pnl = trade_df['PnL'].sum()
    avg_pnl = trade_df['PnL'].mean()
    
    # Calculate Max Drawdown in points
    trade_df['Cum_PnL'] = trade_df['PnL'].cumsum()
    trade_df['Peak'] = trade_df['Cum_PnL'].cummax()
    max_dd = (trade_df['Peak'] - trade_df['Cum_PnL']).max()
    
    return total_trades, win_rate, total_pnl, max_dd

def run_optimization():
    df = load_and_preprocess_data()
    
    print("="*105)
    print("                 SPX OPENING RANGE BREAKOUT (ORB) STRATEGY OPTIMIZATION (VIX > 20)")
    print("="*105)
    print(f"{'Range (h)':<10} | {'Stop Loss Type':<18} | {'Profit Target':<15} | {'Trades':<8} | {'Win Rate':<10} | {'Total Pts':<12} | {'Max DD (pts)':<12}")
    print("-" * 105)
    
    # Grid Search
    for range_h in [1, 2]:
        for stop_type in ['opposite_range', 'half_range']:
            for target_mult in [0.0, 1.0, 1.5, 2.0, 3.0]:
                trades, win_rate, total_pnl, max_dd = run_orb_simulation(df, range_h, stop_type, target_mult)
                if trades > 0:
                    target_label = "Hold to Close" if target_mult == 0.0 else f"{target_mult}x Range"
                    print(f"{range_h:<10} | {stop_type:<18} | {target_label:<15} | {trades:<8} | {win_rate*100:<8.1f}% | {total_pnl:<+10.2f} | {max_dd:<12.2f}")
    print("="*105)

if __name__ == '__main__':
    run_optimization()
