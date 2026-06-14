import pandas as pd
import numpy as np

def run_orb_backtest(csv_path="spx_vix_hourly.csv"):
    df = pd.read_csv(csv_path)
    
    # We need to pivot or group the hourly bars by date
    # Let's see what hours we have for each date
    dates = df['Date'].unique()
    
    results = []
    
    for dt in dates:
        day_df = df[df['Date'] == dt].sort_values('Time').copy()
        
        # We need a full day of data to backtest:
        # Must have 09:30:00 (which represents the first hour close 10:30 in some systems, or the start)
        # Let's inspect the times: usually we have 09:30:00, 10:30:00, 11:30:00, 12:30:00, 13:30:00, 14:30:00, 15:30:00.
        # The 09:30:00 bar represents the open print or the 9:30-10:30 period depending on formatting.
        # Let's assume:
        # - Opening Range is defined by the 09:30:00 bar's High and Low.
        # - The VIX is measured at 09:30:00.
        # - Breakout entry is checked on subsequent bars (10:30:00, 11:30:00, 12:30:00, 13:30:00, 14:30:00).
        # - Exit is at the close of the 15:30:00 bar (representing 4:00 PM close).
        
        if len(day_df) < 5:
            continue
            
        bar_0930 = day_df[day_df['Time'] == '09:30:00']
        bar_1530 = day_df[day_df['Time'] == '15:30:00']
        
        if bar_0930.empty or bar_1530.empty:
            continue
            
        vix_entry = bar_0930['VIX_Open'].values[0]
        spx_open = bar_0930['SPX_Open'].values[0]
        
        # Define the 9:30 AM to 10:30 AM range:
        # In our dataset, the 09:30:00 bar has SPX_High and SPX_Low
        range_high = bar_0930['SPX_High'].values[0]
        range_low = bar_0930['SPX_Low'].values[0]
        
        day_close = bar_1530['SPX_Close'].values[0]
        
        # Check subsequent bars for breakouts
        subsequent_bars = day_df[~day_df['Time'].isin(['09:30:00', '15:30:00'])]
        
        triggered = False
        position = 0 # +1 for Long, -1 for Short
        entry_price = 0.0
        pnl = 0.0
        
        for idx, bar in subsequent_bars.iterrows():
            high_val = bar['SPX_High']
            low_val = bar['SPX_Low']
            
            # Check Long Breakout
            if not triggered and high_val > range_high:
                triggered = True
                position = 1
                entry_price = range_high
                break
                
            # Check Short Breakout
            elif not triggered and low_val < range_low:
                triggered = True
                position = -1
                entry_price = range_low
                break
                
        if triggered:
            # PnL calculation: close price minus entry price (adjusted for short/long)
            # We subtract a small slippage of 0.50 points on SPX (representing index execution friction)
            slip = 0.50
            if position == 1:
                # Long
                pnl = (day_close - entry_price - slip)
                # Check if we hit the Stop Loss (SPX touched or fell below range_low)
                # For simplicity in hourly data, if any bar low is below range_low, we assume stopped out at range_low
                for idx, bar in subsequent_bars.iterrows():
                    if bar['SPX_Low'] <= range_low:
                        pnl = (range_low - entry_price - slip)
                        break
            else:
                # Short
                pnl = (entry_price - day_close - slip)
                # Check if stopped out (SPX touched or rose above range_high)
                for idx, bar in subsequent_bars.iterrows():
                    if bar['SPX_High'] >= range_high:
                        pnl = (entry_price - range_high - slip)
                        break
                        
        results.append({
            "Date": dt,
            "VIX": vix_entry,
            "Triggered": triggered,
            "PnL_Points": pnl,
            "Position": position
        })
        
    res_df = pd.DataFrame(results)
    
    # Split by VIX
    low_vix = res_df[res_df['VIX'] <= 20.0]
    high_vix = res_df[res_df['VIX'] > 20.0]
    
    print("="*85)
    print("            SPX OPENING RANGE BREAKOUT (ORB) STRATEGY PERFORMANCE")
    print("="*85)
    print(f"{'VIX Regime':<20} | {'Trades':<8} | {'Win Rate (%)':<12} | {'Total Points PnL':<18} | {'Avg Pts/Trade':<12}")
    print("-" * 85)
    
    for label, sub_df in [("All Days", res_df), ("VIX <= 20 (Low Vol)", low_vix), ("VIX > 20 (High Vol)", high_vix)]:
        tr_df = sub_df[sub_df['Triggered'] == True]
        trades = len(tr_df)
        wins = len(tr_df[tr_df['PnL_Points'] > 0])
        win_rate = wins / trades if trades > 0 else 0.0
        total_pnl = tr_df['PnL_Points'].sum()
        avg_pnl = tr_df['PnL_Points'].mean() if trades > 0 else 0.0
        
        print(f"{label:<20} | {trades:<8} | {win_rate*100:<11.1f}% | {total_pnl:<+17.2f} | {avg_pnl:<+12.2f}")
    print("="*85)

if __name__ == '__main__':
    run_orb_backtest()
