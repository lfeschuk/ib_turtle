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

def run_unfiltered_backtest(csv_path="spx_vix_hourly.csv", wing_width=10, slippage=0.10, strike_step=5):
    df = pd.read_csv(csv_path)
    
    time_str = "13:30:00"
    hours_left = 2.5
    
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    time_df = df[df['Time'] == time_str].copy()
    data = pd.merge(time_df, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    
    print("="*105)
    print("         1:30 PM SPX 10-WIDE BULL PUT SPREAD: VIX > 20 FILTER vs NO VIX FILTER (ALL DAYS)")
    print("="*105)
    print(f"{'VIX Filter':<15} | {'Trades':<8} | {'Win Rate (%)':<12} | {'Total PnL ($)':<14} | {'Avg Premium ($)':<16} | {'Max DD ($)':<10}")
    print("-" * 105)
    
    for filter_vix in [True, False]:
        trades = 0
        wins = 0
        total_pnl = 0.0
        sum_premium = 0.0
        capital = 10000.0
        peak_capital = 10000.0
        max_dd = 0.0
        
        for idx, row in data.iterrows():
            spx_entry = row['SPX_Open']
            spx_close = row['Day_Close']
            vix_entry = row['VIX_Open']
            
            if pd.isna(spx_entry) or pd.isna(vix_entry) or pd.isna(spx_close):
                continue
                
            # VIX > 20 Filter
            if filter_vix and vix_entry <= 20.0:
                continue
                
            k_short_put = round((spx_entry - 30) / strike_step) * strike_step
            raw_premium = calculate_spread_premium(spx_entry, k_short_put, hours_left, vix_entry, wing_width)
            actual_premium = raw_premium - slippage
            
            # If premium is negative or extremely low, we still enter if there's no VIX filter (representing raw execution)
            if actual_premium <= 0.00:
                actual_premium = 0.01
                
            trades += 1
            sum_premium += actual_premium
            
            loss = max(0.0, k_short_put - spx_close)
            payout = actual_premium - min(wing_width, loss)
            pnl = payout * 100.0
            
            total_pnl += pnl
            capital += pnl
            if capital > peak_capital:
                peak_capital = capital
            dd = peak_capital - capital
            if dd > max_dd:
                max_dd = dd
                
            if pnl > 0:
                wins += 1
                
        win_rate = wins / trades if trades > 0 else 0.0
        avg_prem = sum_premium / trades if trades > 0 else 0.0
        filter_label = "VIX > 20" if filter_vix else "No VIX Filter"
        print(f"{filter_label:<15} | {trades:<8} | {win_rate*100:<11.1f}% | ${total_pnl:<12,.2f} | ${avg_prem:<14.2f} | ${max_dd:.2f}")
    print("="*105)

if __name__ == '__main__':
    run_unfiltered_backtest()
