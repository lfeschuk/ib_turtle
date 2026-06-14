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

def calculate_butterfly_premium(S, K, T_hours, vix, wing_width=10):
    T = (T_hours / 6.5) / 252.0
    r = 0.05
    sigma = vix / 100.0
    
    short_call = black_scholes_value(S, K, T, r, sigma, 'C')
    short_put = black_scholes_value(S, K, T, r, sigma, 'P')
    long_call = black_scholes_value(S, K + wing_width, T, r, sigma, 'C')
    long_put = black_scholes_value(S, K - wing_width, T, r, sigma, 'P')
    return (short_call + short_put) - (long_call + long_put)

def run_realistic_test(csv_path="spx_vix_hourly.csv", wing_width=10, slippage=0.10, strike_step=5):
    df = pd.read_csv(csv_path)
    
    # 1:30 PM entry
    time_str = "13:30:00"
    hours_left = 2.5
    
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    time_df = df[df['Time'] == time_str].copy()
    data = pd.merge(time_df, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    
    # We will test premium thresholds: 6.00, 6.50, 7.00, 7.50, 8.00
    thresholds = [6.00, 6.50, 7.00, 7.50, 8.00]
    results = []
    
    for thresh in thresholds:
        trades_count = 0
        wins = 0
        total_pnl = 0.0
        capital = 10000.0
        peak_capital = 10000.0
        max_drawdown = 0.0
        
        for idx, row in data.iterrows():
            spx_entry = row['SPX_Open']
            spx_close = row['Day_Close']
            vix_entry = row['VIX_Open']
            
            if pd.isna(spx_entry) or pd.isna(vix_entry) or pd.isna(spx_close):
                continue
                
            center_strike = round(spx_entry / strike_step) * strike_step
            
            theoretical_premium = calculate_butterfly_premium(spx_entry, center_strike, hours_left, vix_entry, wing_width)
            actual_premium = theoretical_premium - slippage
            
            # Check entry criteria
            if actual_premium >= thresh:
                trades_count += 1
                close_distance = abs(spx_close - center_strike)
                payout = actual_premium - min(wing_width, close_distance)
                pnl = payout * 100.0
                
                total_pnl += pnl
                capital += pnl
                if capital > peak_capital:
                    peak_capital = capital
                dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
                if dd > max_drawdown:
                    max_drawdown = dd
                    
                if pnl > 0:
                    wins += 1
                    
        win_rate = wins / trades_count if trades_count > 0 else 0.0
        results.append({
            "Min Premium": thresh,
            "Trades": trades_count,
            "Entry Rate (%)": (trades_count / len(data)) * 100,
            "Win Rate (%)": win_rate * 100,
            "Total PnL ($)": total_pnl,
            "Avg PnL / Trade ($)": total_pnl / trades_count if trades_count > 0 else 0,
            "Max Drawdown (%)": max_drawdown * 100
        })
        
    res_df = pd.DataFrame(results)
    print("\n" + "="*85)
    print("      REALISTIC PREMIUM TARGETS AT 1:30 PM (HOLD TO EXPIRATION)")
    print("="*85)
    print(res_df.to_string(index=False, formatters={
        "Min Premium": "${:,.2f}".format,
        "Trades": "{:d}".format,
        "Entry Rate (%)": "{:.1f}%".format,
        "Win Rate (%)": "{:.1f}%".format,
        "Total PnL ($)": "${:+,.2f}".format,
        "Avg PnL / Trade ($)": "${:+,.2f}".format,
        "Max Drawdown (%)": "{:.1f}%".format
    }))
    print("="*85 + "\n")

if __name__ == '__main__':
    run_realistic_test()
