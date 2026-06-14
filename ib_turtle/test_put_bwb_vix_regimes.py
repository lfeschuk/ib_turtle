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
    val_long_upper = black_scholes_value(S, K_short + upper_gap, T, r, sigma, 'P')
    val_short = black_scholes_value(S, K_short, T, r, sigma, 'P')
    val_long_lower = black_scholes_value(S, K_short - lower_gap, T, r, sigma, 'P')
    return (2 * val_short) - val_long_upper - val_long_lower

def run_vix_analysis(csv_path="spx_vix_hourly.csv", haircut=0.50, slippage=0.15, strike_step=5):
    df = pd.read_csv(csv_path)
    time_str = "13:30:00"
    hours_left = 2.5
    
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    time_df = df[df['Time'] == time_str].copy()
    data = pd.merge(time_df, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    
    upper_g, lower_g = 10, 20
    
    results = []
    
    for idx, row in data.iterrows():
        spx_entry = row['SPX_Open']
        spx_close = row['Day_Close']
        vix_entry = row['VIX_Open']
        
        if pd.isna(spx_entry) or pd.isna(vix_entry) or pd.isna(spx_close):
            continue
            
        k_short = round(spx_entry / strike_step) * strike_step
        raw_bwb = calculate_put_bwb_premium(spx_entry, k_short, hours_left, vix_entry, upper_g, lower_g)
        
        # Net premium after slippage and haircut
        net_premium = raw_bwb - slippage - haircut
        
        val_long_upper = max(0.0, (k_short + upper_g) - spx_close)
        val_shorts = 2 * max(0.0, k_short - spx_close)
        val_long_lower = max(0.0, (k_short - lower_g) - spx_close)
        
        final_value = val_long_upper - val_shorts + val_long_lower
        pnl = (net_premium + final_value) * 100.0
        
        results.append({
            "Date": row['Date'],
            "VIX": vix_entry,
            "PnL": pnl,
            "Premium": net_premium,
            "Win": 1 if pnl > 0 else 0
        })
        
    res_df = pd.DataFrame(results)
    
    # Split by VIX
    low_vix = res_df[res_df['VIX'] <= 20.0]
    high_vix = res_df[res_df['VIX'] > 20.0]
    
    print("="*115)
    print("        0 DTE SPX PUT BWB (+10/-20) PERFORMANCE BY VIX REGIME (WITH $0.50 SLIPPAGE HAIRCUT)")
    print("="*115)
    print(f"{'VIX Regime':<20} | {'Trades':<8} | {'Win Rate (%)':<12} | {'Total PnL ($)':<15} | {'Avg Premium ($)':<16} | {'Max DD ($)':<12}")
    print("-" * 115)
    
    for label, sub_df in [("All Days (Any VIX)", res_df), ("VIX <= 20 (Low Vol)", low_vix), ("VIX > 20 (High Vol)", high_vix)]:
        trades = len(sub_df)
        wins = sub_df['Win'].sum()
        win_rate = wins / trades if trades > 0 else 0.0
        total_pnl = sub_df['PnL'].sum()
        avg_prem = sub_df['Premium'].mean() if trades > 0 else 0.0
        
        # Drawdown calculation
        sub_df = sub_df.copy()
        sub_df['Cum_PnL'] = sub_df['PnL'].cumsum()
        sub_df['Peak'] = sub_df['Cum_PnL'].cummax()
        max_dd = (sub_df['Peak'] - sub_df['Cum_PnL']).max()
        
        print(f"{label:<20} | {trades:<8} | {win_rate*100:<11.1f}% | ${total_pnl:<+14,.2f} | ${avg_prem:<14.2f} | ${max_dd:,.2f}")
    print("="*115)

if __name__ == '__main__':
    run_vix_analysis()
