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

def run_intraday_analysis(csv_path="spx_vix_hourly.csv", 
                          wing_width=10, 
                          min_premium=8.00, 
                          take_profit_pct=0.50,
                          slippage=0.10, 
                          strike_step=5):
    
    df = pd.read_csv(csv_path)
    
    # Find the closing price for each day (close price of the 15:30:00 bar)
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    # Map entry times to remaining hours
    entry_times = {
        '09:30:00': 6.5,
        '10:30:00': 5.5,
        '11:30:00': 4.5,
        '12:30:00': 3.5,
        '13:30:00': 2.5,
        '14:30:00': 1.5,
        '15:30:00': 0.5
    }
    
    results = []
    
    # Run the backtest for each entry hour
    for time_str, hours_left in entry_times.items():
        time_df = df[df['Time'] == time_str].copy()
        
        # Merge with the day's close price
        data = pd.merge(time_df, close_df, on='Date', how='inner')
        data = data.sort_values('Date').reset_index(drop=True)
        
        for tp_mode in [False, True]:
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
                
                theoretical_premium = calculate_butterfly_premium(
                    S=spx_entry, 
                    K=center_strike, 
                    T_hours=hours_left, 
                    vix=vix_entry, 
                    wing_width=wing_width
                )
                
                actual_premium = theoretical_premium - slippage
                
                if actual_premium >= min_premium:
                    trades_count += 1
                    close_distance = abs(spx_close - center_strike)
                    
                    if tp_mode:
                        tp_threshold = actual_premium * take_profit_pct
                        if close_distance <= tp_threshold:
                            pnl = (actual_premium * take_profit_pct) * 100.0
                            wins += 1
                        else:
                            payout = actual_premium - min(wing_width, close_distance)
                            pnl = payout * 100.0
                            if pnl > 0:
                                wins += 1
                    else:
                        payout = actual_premium - min(wing_width, close_distance)
                        pnl = payout * 100.0
                        if pnl > 0:
                            wins += 1
                            
                    total_pnl += pnl
                    capital += pnl
                    if capital > peak_capital:
                        peak_capital = capital
                    dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
                    if dd > max_drawdown:
                        max_drawdown = dd
            
            win_rate = wins / trades_count if trades_count > 0 else 0.0
            results.append({
                "Entry Time": time_str,
                "Hours Left": hours_left,
                "TP Active": "Yes" if tp_mode else "No",
                "Trades": trades_count,
                "Entry Rate (%)": (trades_count / len(data)) * 100 if len(data) > 0 else 0,
                "Win Rate (%)": win_rate * 100,
                "Total PnL ($)": total_pnl,
                "Avg PnL / Trade ($)": total_pnl / trades_count if trades_count > 0 else 0,
                "Max Drawdown (%)": max_drawdown * 100
            })
            
    res_df = pd.DataFrame(results)
    print("\n" + "="*95)
    print(f"      INTRADAY ENTRY TIME COMPARISON (SPX 0 DTE 10-WIDE BUTTERFLY, MIN PREMIUM: ${min_premium:.2f})")
    print("="*95)
    print(res_df.to_string(index=False, formatters={
        "Entry Rate (%)": "{:.1f}%".format,
        "Win Rate (%)": "{:.1f}%".format,
        "Total PnL ($)": "${:+,.2f}".format,
        "Avg PnL / Trade ($)": "${:+,.2f}".format,
        "Max Drawdown (%)": "{:.1f}%".format
    }))
    print("="*95 + "\n")

if __name__ == '__main__':
    run_intraday_analysis()
