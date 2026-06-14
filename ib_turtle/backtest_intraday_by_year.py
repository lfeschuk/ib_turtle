import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import os

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

def run_yearly_backtest(csv_path="spx_vix_hourly.csv", 
                        wing_width=10, 
                        min_premium=8.00, 
                        slippage=0.10, 
                        strike_step=5,
                        initial_capital=10000.0,
                        output_image_path="/Users/lfesch/.gemini/jetski/brain/6b0a51b5-c6f9-4d47-9951-0f68db940326/cumulative_returns.png"):
    
    df = pd.read_csv(csv_path)
    
    # 1:30 PM entry has 2.5 hours left
    time_str = "13:30:00"
    hours_left = 2.5
    
    # Day close is the close of the 15:30:00 bar
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    time_df = df[df['Time'] == time_str].copy()
    data = pd.merge(time_df, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    
    trades = []
    
    for idx, row in data.iterrows():
        date_str = row['Date']
        spx_entry = row['SPX_Open']
        spx_close = row['Day_Close']
        vix_entry = row['VIX_Open']
        
        if pd.isna(spx_entry) or pd.isna(vix_entry) or pd.isna(spx_close):
            continue
            
        center_strike = round(spx_entry / strike_step) * strike_step
        theoretical_premium = calculate_butterfly_premium(spx_entry, center_strike, hours_left, vix_entry, wing_width)
        actual_premium = theoretical_premium - slippage
        
        if actual_premium >= min_premium:
            close_distance = abs(spx_close - center_strike)
            payout = actual_premium - min(wing_width, close_distance)
            pnl = payout * 100.0
            
            trades.append({
                "Date": date_str,
                "Year": pd.to_datetime(date_str).year,
                "SPX_Open": spx_entry,
                "SPX_Close": spx_close,
                "VIX_Open": vix_entry,
                "Strike": center_strike,
                "Net_Premium": actual_premium,
                "SPX_Move": spx_close - center_strike,
                "PnL": pnl
            })
            
    trade_df = pd.DataFrame(trades)
    
    if trade_df.empty:
        print("No trades found matching entry criteria.")
        return
        
    # Calculate cumulative PnL
    trade_df['Cum_PnL'] = trade_df['PnL'].cumsum()
    trade_df['Capital'] = initial_capital + trade_df['Cum_PnL']
    
    # Calculate drawdowns by year and overall
    trade_df['Peak_Capital'] = trade_df['Capital'].cummax()
    trade_df['Drawdown'] = (trade_df['Peak_Capital'] - trade_df['Capital']) / trade_df['Peak_Capital']
    
    # Group stats by Year
    yearly_stats = []
    years = sorted(trade_df['Year'].unique())
    
    for yr in years:
        yr_df = trade_df[trade_df['Year'] == yr].copy()
        yr_trades = len(yr_df)
        wins = yr_df[yr_df['PnL'] > 0]
        win_rate = len(wins) / yr_trades if yr_trades > 0 else 0
        total_pnl = yr_df['PnL'].sum()
        avg_pnl = yr_df['PnL'].mean()
        
        # Drawdown specific to this year's index
        yr_df['Yr_Cum_PnL'] = yr_df['PnL'].cumsum()
        yr_df['Yr_Capital'] = initial_capital + yr_df['Yr_Cum_PnL']
        yr_df['Yr_Peak'] = yr_df['Yr_Capital'].cummax()
        yr_df['Yr_Drawdown'] = (yr_df['Yr_Peak'] - yr_df['Yr_Capital']) / yr_df['Yr_Peak']
        max_yr_dd = yr_df['Yr_Drawdown'].max()
        
        yearly_stats.append({
            "Year": yr,
            "Trades": yr_trades,
            "Win Rate (%)": win_rate * 100,
            "Total PnL ($)": total_pnl,
            "Avg PnL / Trade ($)": avg_pnl,
            "Max Drawdown (%)": max_yr_dd * 100
        })
        
    stats_df = pd.DataFrame(yearly_stats)
    
    print("\n" + "="*85)
    print("                 YEARLY BREAKDOWN: SPX 0 DTE 10-WIDE BUTTERFLY (1:30 PM ENTRY)")
    print("="*85)
    print(stats_df.to_string(index=False, formatters={
        "Win Rate (%)": "{:.1f}%".format,
        "Total PnL ($)": "${:+,.2f}".format,
        "Avg PnL / Trade ($)": "${:+,.2f}".format,
        "Max Drawdown (%)": "{:.1f}%".format
    }))
    print("="*85 + "\n")
    
    # Plotting the chart
    plt.figure(figsize=(10, 6))
    plt.plot(pd.to_datetime(trade_df['Date']), trade_df['Cum_PnL'], label='Cumulative PnL ($)', color='#1f77b4', linewidth=2)
    plt.title('SPX 0 DTE 10-Wide Iron Butterfly Cumulative Returns (1:30 PM Entry)', fontsize=14, pad=15)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Net Profit ($)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Format with nice dollar tick values
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    
    # Highlight years
    for yr in years:
        yr_dates = trade_df[trade_df['Year'] == yr]['Date']
        if not yr_dates.empty:
            first_date = pd.to_datetime(yr_dates.iloc[0])
            plt.axvline(x=first_date, color='grey', linestyle=':', alpha=0.7)
            plt.text(first_date, plt.gca().get_ylim()[0] + 5000, f" {yr} Start", color='grey', fontsize=10)
            
    plt.legend(loc='upper left')
    plt.tight_layout()
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    plt.savefig(output_image_path, dpi=300)
    plt.close()
    print(f"Cumulative return chart saved to {output_image_path}")

if __name__ == '__main__':
    run_yearly_backtest()
