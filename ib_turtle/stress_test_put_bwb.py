import pandas as pd
import numpy as np
import math

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

def calculate_put_bwb_premium(S, K_short, T_hours, vix, upper_gap=10, lower_gap=20):
    T = (T_hours / 6.5) / 252.0
    r = 0.05
    sigma = vix / 100.0
    val_long_upper = black_scholes_value(S, K_short + upper_g, T, r, sigma, 'P')
    val_short = black_scholes_value(S, K_short, T, r, sigma, 'P')
    val_long_lower = black_scholes_value(S, K_short - lower_g, T, r, sigma, 'P')
    return (2 * val_short) - val_long_upper - val_long_lower

if __name__ == '__main__':
    df = pd.read_csv("spx_vix_hourly.csv")
    time_str = "13:30:00"
    hours_left = 2.5
    
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    time_df = df[df['Time'] == time_str].copy()
    data = pd.merge(time_df, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    data = data[data['VIX_Open'] <= 20.0].copy()
    
    upper_g, lower_g = 10, 20
    strike_step = 5
    
    print("="*115)
    print("        STRESS TESTING 0 DTE SPX PUT BWB (+10/-20): P&L WITH PREMIUM HAIRCUTS (VIX <= 20)")
    print("="*115)
    print(f"{'Premium Haircut':<18} | {'Realized Premium':<18} | {'Trades':<8} | {'Win Rate':<10} | {'Total Net PnL':<15} | {'Max DD ($)':<12}")
    print("-" * 115)
    
    for haircut in [0.00, 0.50, 1.00, 1.25, 1.50]:
        trades = 0
        wins = 0
        total_pnl = 0.0
        max_dd = 0.0
        capital = 10000.0
        peak_capital = 10000.0
        sum_prem = 0.0
        
        for idx, row in data.iterrows():
            spx_entry = row['SPX_Open']
            spx_close = row['Day_Close']
            vix_entry = row['VIX_Open']
            
            if pd.isna(spx_entry) or pd.isna(vix_entry) or pd.isna(spx_close):
                continue
                
            k_short = round(spx_entry / strike_step) * strike_step
            raw_bwb = calculate_put_bwb_premium(spx_entry, k_short, hours_left, vix_entry, upper_g, lower_g)
            
            # Net premium after slippage and haircut
            net_premium = raw_bwb - 0.15 - haircut
            
            trades += 1
            sum_prem += net_premium
            
            val_long_upper = max(0.0, (k_short + upper_g) - spx_close)
            val_shorts = 2 * max(0.0, k_short - spx_close)
            val_long_lower = max(0.0, (k_short - lower_g) - spx_close)
            
            final_value = val_long_upper - val_shorts + val_long_lower
            pnl = (net_premium + final_value) * 100.0
            
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
        avg_prem = sum_prem / trades if trades > 0 else 0.0
        haircut_label = f"${haircut:.2f} Haircut"
        realized_label = f"${avg_prem:.2f}"
        print(f"{haircut_label:<18} | {realized_label:<18} | {trades:<8} | {win_rate*100:<8.1f}% | ${total_pnl:<+13,.2f} | ${max_dd:,.2f}")
    print("="*115)
