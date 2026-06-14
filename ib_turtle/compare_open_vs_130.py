import pandas as pd
import numpy as np
import math

# --- Black-Scholes Model Helpers ---
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def black_scholes_value(S, K, T, r, sigma, option_type):
    if T <= 0:
        return max(0.0, S - K) if option_type == 'C' else max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == 'C':
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def calculate_spread_premium(S, K_short, T_hours, vix, wing_width=10):
    T = (T_hours / 6.5) / 252.0
    r = 0.05
    sigma = vix / 100.0
    short_val = black_scholes_value(S, K_short, T, r, sigma, 'P')
    long_val = black_scholes_value(S, K_short - wing_width, T, r, sigma, 'P')
    return short_val - long_val

def run_comparison(csv_path="spx_vix_hourly.csv", wing_width=10, slippage=0.10, strike_step=5):
    df = pd.read_csv(csv_path)
    
    # Close is 15:30:00 bar close
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    # 9:30 AM EST Entry (6.5 hours left)
    open_df = df[df['Time'] == '09:30:00'][['Date', 'SPX_Open', 'VIX_Open']].copy()
    open_df.columns = ['Date', 'SPX_0930', 'VIX_0930']
    
    # 1:30 PM EST Entry (2.5 hours left)
    mid_df = df[df['Time'] == '13:30:00'][['Date', 'SPX_Open', 'VIX_Open']].copy()
    mid_df.columns = ['Date', 'SPX_1330', 'VIX_1330']
    
    # Merge all
    m1 = pd.merge(open_df, mid_df, on='Date', how='inner')
    data = pd.merge(m1, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    
    print("="*115)
    print("      BULL PUT SPREAD COMPARISON: 9:30 AM EST OPEN vs 1:30 PM EST ENTRY (HIGH VIX DAYS: VIX > 20)")
    print("="*115)
    print(f"{'Entry Time':<10} | {'Offset (pts)':<12} | {'Trades':<6} | {'Win Rate (%)':<12} | {'Total PnL ($)':<14} | {'Avg Premium ($)':<16} | {'Max DD ($)':<10}")
    print("-" * 115)
    
    for offset in [20, 25, 30, 35, 40]:
        # --- 9:30 AM EST OPEN ENTRY ---
        trades_open = 0
        wins_open = 0
        pnl_open = 0.0
        prem_open = 0.0
        cap_open = 10000.0
        peak_open = 10000.0
        dd_open = 0.0
        
        for idx, row in data.iterrows():
            if row['VIX_0930'] <= 20.0:
                continue
                
            spx_entry = row['SPX_0930']
            spx_close = row['Day_Close']
            vix_entry = row['VIX_0930']
            
            if pd.isna(spx_entry) or pd.isna(vix_entry) or pd.isna(spx_close):
                continue
                
            k_short = round((spx_entry - offset) / strike_step) * strike_step
            raw_premium = calculate_spread_premium(spx_entry, k_short, 6.5, vix_entry, wing_width)
            actual_premium = raw_premium - slippage
            
            if actual_premium <= 0.05:
                continue
                
            trades_open += 1
            prem_open += actual_premium
            
            loss = max(0.0, k_short - spx_close)
            payout = actual_premium - min(wing_width, loss)
            trade_pnl = payout * 100.0
            
            pnl_open += trade_pnl
            cap_open += trade_pnl
            if cap_open > peak_open:
                peak_open = cap_open
            dd = peak_open - cap_open
            if dd > dd_open:
                dd_open = dd
                
            if trade_pnl > 0:
                wins_open += 1
                
        win_rate_open = wins_open / trades_open if trades_open > 0 else 0.0
        avg_prem_open = prem_open / trades_open if trades_open > 0 else 0.0
        
        # --- 1:30 PM EST ENTRY ---
        trades_1330 = 0
        wins_1330 = 0
        pnl_1330 = 0.0
        prem_1330 = 0.0
        cap_1330 = 10000.0
        peak_1330 = 10000.0
        dd_1330 = 0.0
        
        for idx, row in data.iterrows():
            if row['VIX_1330'] <= 20.0:
                continue
                
            spx_entry = row['SPX_1330']
            spx_close = row['Day_Close']
            vix_entry = row['VIX_1330']
            
            if pd.isna(spx_entry) or pd.isna(vix_entry) or pd.isna(spx_close):
                continue
                
            k_short = round((spx_entry - offset) / strike_step) * strike_step
            raw_premium = calculate_spread_premium(spx_entry, k_short, 2.5, vix_entry, wing_width)
            actual_premium = raw_premium - slippage
            
            if actual_premium <= 0.05:
                continue
                
            trades_1330 += 1
            prem_1330 += actual_premium
            
            loss = max(0.0, k_short - spx_close)
            payout = actual_premium - min(wing_width, loss)
            trade_pnl = payout * 100.0
            
            pnl_1330 += trade_pnl
            cap_1330 += trade_pnl
            if cap_1330 > peak_1330:
                peak_1330 = cap_1330
            dd = peak_1330 - cap_1330
            if dd > dd_1330:
                dd_1330 = dd
                
            if trade_pnl > 0:
                wins_1330 += 1
                
        win_rate_1330 = wins_1330 / trades_1330 if trades_1330 > 0 else 0.0
        avg_prem_1330 = prem_1330 / trades_1330 if trades_1330 > 0 else 0.0
        
        # Print side-by-side comparison for this offset
        print(f"{'9:30 AM':<10} | {offset:<12} | {trades_open:<6} | {win_rate_open*100:<11.1f}% | ${pnl_open:<12,.2f} | ${avg_prem_open:<14.2f} | ${dd_open:.2f}")
        print(f"{'1:30 PM':<10} | {offset:<12} | {trades_1330:<6} | {win_rate_1330*100:<11.1f}% | ${pnl_1330:<12,.2f} | ${avg_prem_1330:<14.2f} | ${dd_1330:.2f}")
        print("-" * 115)

if __name__ == '__main__':
    run_comparison()
