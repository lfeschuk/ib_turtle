import pandas as pd
import numpy as np
import sys
import os

def run_orb_backtest(csv_path="spx_vix_hourly_2020_2023.csv"):
    if not os.path.exists(csv_path):
        print(f"❌ Error: Data file '{csv_path}' not found.")
        print("Please run 'python3 download_historical_ib.py' first to download the historical data from IBKR.")
        return
        
    print(f"📖 Loading hourly historical dataset from '{csv_path}'...")
    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    dates = df['Date'].unique()
    results = []
    
    print("⏳ Running 2-Hour Opening Range Breakout simulation across all dates...")
    for dt in dates:
        day_df = df[df['Date'] == dt].sort_values('Time').copy()
        if len(day_df) < 5:
            continue
            
        bar_0930 = day_df[day_df['Time'] == '09:30:00']
        bar_1030 = day_df[day_df['Time'] == '10:30:00']
        bar_1530 = day_df[day_df['Time'] == '15:30:00']
        
        if bar_0930.empty or bar_1030.empty or bar_1530.empty:
            continue
            
        vix_entry = bar_0930['VIX_Open'].values[0]
        
        # 2-hour range high and low (9:30 to 11:30 AM EST)
        range_high = max(bar_0930['SPX_High'].values[0], bar_1030['SPX_High'].values[0])
        range_low = min(bar_0930['SPX_Low'].values[0], bar_1030['SPX_Low'].values[0])
        
        day_close = bar_1530['SPX_Close'].values[0]
        subsequent_bars = day_df[~day_df['Time'].isin(['09:30:00', '10:30:00', '15:30:00'])]
        
        triggered = False
        position = 0
        entry_price = 0.0
        
        for idx, bar in subsequent_bars.iterrows():
            high_val = bar['SPX_High']
            low_val = bar['SPX_Low']
            
            if high_val > range_high:
                triggered = True
                position = 1
                entry_price = range_high
                break
            elif low_val < range_low:
                triggered = True
                position = -1
                entry_price = range_low
                break
                
        if triggered:
            # Stop loss is the opposite side of the range
            stop_level = range_low if position == 1 else range_high
            pnl = 0.0
            exited = False
            
            for idx, bar in subsequent_bars.iterrows():
                high_val = bar['SPX_High']
                low_val = bar['SPX_Low']
                
                if position == 1:
                    if low_val <= stop_level:
                        pnl = stop_level - entry_price
                        exited = True
                        break
                else: # Short
                    if high_val >= stop_level:
                        pnl = entry_price - stop_level
                        exited = True
                        break
                        
            if not exited:
                pnl = (day_close - entry_price) if position == 1 else (entry_price - day_close)
                
            pnl -= 0.50 # index slippage
            
            results.append({
                "Date": dt,
                "Year": pd.to_datetime(dt).year,
                "VIX": vix_entry,
                "Triggered": True,
                "PnL": pnl,
                "Win": 1 if pnl > 0 else 0
            })
            
    if not results:
        print("❌ No valid trades were triggered in this dataset.")
        return
        
    res_df = pd.DataFrame(results)
    
    # 1. Split by VIX Regime
    low_vix = res_df[res_df['VIX'] <= 20.0]
    high_vix = res_df[res_df['VIX'] > 20.0]
    
    print("\n" + "="*105)
    print("        2-HOUR SPX ORB STRATEGY PERFORMANCE BY VIX REGIME (STOP: OPPOSITE RANGE, TARGET: CLOSE)")
    print("="*105)
    print(f"{'VIX Regime':<20} | {'Trades':<8} | {'Win Rate (%)':<12} | {'Total Pts PnL':<15} | {'Avg Pts/Trade':<14} | {'Max DD (pts)':<12}")
    print("-" * 105)
    
    for label, sub_df in [("All Days (Any VIX)", res_df), ("VIX <= 20 (Low Vol)", low_vix), ("VIX > 20 (High Vol)", high_vix)]:
        trades = len(sub_df)
        if trades == 0:
            continue
        wins = sub_df['Win'].sum()
        win_rate = wins / trades
        total_pnl = sub_df['PnL'].sum()
        avg_pnl = sub_df['PnL'].mean()
        
        # Drawdown in points
        sub_df = sub_df.copy()
        sub_df['Cum_PnL'] = sub_df['PnL'].cumsum()
        sub_df['Peak'] = sub_df['Cum_PnL'].cummax()
        max_dd = (sub_df['Peak'] - sub_df['Cum_PnL']).max()
        
        print(f"{label:<20} | {trades:<8} | {win_rate*100:<11.1f}% | {total_pnl:<+14.2f} | {avg_pnl:<+13.2f} | {max_dd:.2f}")
    print("="*105)
    
    # 2. Yearly Breakdown for High VIX days (VIX > 20)
    high_vix_copy = high_vix.copy()
    if len(high_vix_copy) > 0:
        print("\n" + "="*105)
        print("         YEARLY BREAKDOWN: 2-HOUR SPX ORB PERFORMANCE ON HIGH VIX DAYS (VIX > 20)")
        print("="*105)
        print(f"{'Year':<6} | {'Trades':<8} | {'Win Rate (%)':<12} | {'Total Pts PnL':<15} | {'Avg Pts/Trade':<14} | {'Max DD (pts)':<12}")
        print("-" * 105)
        
        years = sorted(high_vix_copy['Year'].unique())
        for yr in years:
            yr_df = high_vix_copy[high_vix_copy['Year'] == yr].copy()
            trades = len(yr_df)
            if trades == 0:
                continue
            wins = yr_df['Win'].sum()
            win_rate = wins / trades
            total_pnl = yr_df['PnL'].sum()
            avg_pnl = yr_df['PnL'].mean()
            
            yr_df['Cum_PnL'] = yr_df['PnL'].cumsum()
            yr_df['Peak'] = yr_df['Cum_PnL'].cummax()
            max_dd = (yr_df['Peak'] - yr_df['Cum_PnL']).max()
            
            print(f"{yr:<6} | {trades:<8} | {win_rate*100:<11.1f}% | {total_pnl:<+14.2f} | {avg_pnl:<+13.2f} | {max_dd:.2f}")
        
        # Print Overall Row
        trades = len(high_vix_copy)
        wins = high_vix_copy['Win'].sum()
        win_rate = wins / trades
        total_pnl = high_vix_copy['PnL'].sum()
        avg_pnl = high_vix_copy['PnL'].mean()
        
        high_vix_copy['Cum_PnL'] = high_vix_copy['PnL'].cumsum()
        high_vix_copy['Peak'] = high_vix_copy['Cum_PnL'].cummax()
        max_dd = (high_vix_copy['Peak'] - high_vix_copy['Cum_PnL']).max()
        
        print("-" * 105)
        print(f"{'OVERALL':<6} | {trades:<8} | {win_rate*100:<11.1f}% | {total_pnl:<+14.2f} | {avg_pnl:<+13.2f} | {max_dd:.2f}")
        print("="*105)

if __name__ == '__main__':
    file_arg = sys.argv[1] if len(sys.argv) > 1 else "spx_vix_hourly_2020_2023.csv"
    run_orb_backtest(file_arg)
