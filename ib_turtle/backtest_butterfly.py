import pandas as pd
import numpy as np
import math
import datetime

# --- Black-Scholes Model Helpers ---
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def black_scholes_value(S, K, T, r, sigma, option_type):
    if T <= 0:
        if option_type == 'C':
            return max(0.0, S - K)
        else:
            return max(0.0, K - S)
            
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == 'C':
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def calculate_butterfly_premium(S, K, T, r, sigma, wing_width=10):
    short_call = black_scholes_value(S, K, T, r, sigma, 'C')
    short_put = black_scholes_value(S, K, T, r, sigma, 'P')
    long_call = black_scholes_value(S, K + wing_width, T, r, sigma, 'C')
    long_put = black_scholes_value(S, K - wing_width, T, r, sigma, 'P')
    
    premium = (short_call + short_put) - (long_call + long_put)
    return premium

def run_backtest(csv_path="spx_vix_historical.csv", 
                 wing_width=10, 
                 min_premium=8.00, 
                 take_profit_pct=0.50,
                 slippage=0.10, 
                 strike_step=5, 
                 initial_capital=10000.0):
    
    df = pd.read_csv(csv_path)
    df = df.sort_values('Date').reset_index(drop=True)
    
    trades = []
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown = 0.0
    
    # Options parameters
    # 0 DTE entered at open, expires at close (6.5 hours = 6.5 / (252 * 6.5) = 1/252 of a year)
    T = 1.0 / 252.0 
    r = 0.05 # 5% risk free rate
    
    for idx, row in df.iterrows():
        date_str = row['Date']
        spx_open = row['SPX_Open']
        spx_high = row['SPX_High']
        spx_low = row['SPX_Low']
        spx_close = row['SPX_Close']
        vix_open = row['VIX_Open']
        
        if pd.isna(spx_open) or pd.isna(vix_open) or pd.isna(spx_close):
            continue
            
        # Determine center strike (ATM, rounded to nearest strike_step)
        center_strike = round(spx_open / strike_step) * strike_step
        
        # Volatility index as implied volatility
        sigma = vix_open / 100.0
        
        # Calculate theoretical butterfly premium at the open
        theoretical_premium = calculate_butterfly_premium(
            S=spx_open, 
            K=center_strike, 
            T=T, 
            r=r, 
            sigma=sigma, 
            wing_width=wing_width
        )
        
        # Check if the premium meets the minimum threshold
        # Slippage reduces the premium collected at entry
        actual_premium_collected = theoretical_premium - slippage
        
        trade_entered = actual_premium_collected >= min_premium
        
        if trade_entered:
            # Distance from center strike at close
            close_distance = abs(spx_close - center_strike)
            
            # Take Profit target is hit if the butterfly price drops to 50% of premium
            # Which occurs if the closing value of the butterfly is <= (Premium * (1 - TP%))
            # Since final value is close_distance, we hit TP if close_distance <= Premium * TP%
            tp_threshold = actual_premium_collected * take_profit_pct
            
            if close_distance <= tp_threshold:
                # We bought back the butterfly for (Premium * (1 - TP%))
                # Profit is Premium * TP%
                pnl = (actual_premium_collected * take_profit_pct) * 100.0
                exit_type = "TP"
            else:
                # Expired at close
                payout_at_expiry = actual_premium_collected - min(wing_width, close_distance)
                pnl = payout_at_expiry * 100.0
                exit_type = "EXPIRY"
            
            # Update capital
            capital += pnl
            if capital > peak_capital:
                peak_capital = capital
            
            dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd
                
            trades.append({
                "Date": date_str,
                "SPX_Open": spx_open,
                "SPX_Close": spx_close,
                "VIX_Open": vix_open,
                "Strike": center_strike,
                "Theo_Premium": theoretical_premium,
                "Net_Premium": actual_premium_collected,
                "SPX_Move": spx_close - center_strike,
                "Exit_Type": exit_type,
                "PnL": pnl,
                "Capital": capital
            })
            
    trade_df = pd.DataFrame(trades)
    
    # Print results summary
    total_days = len(df)
    trades_count = len(trade_df)
    
    print("\n" + "="*50)
    print("      0 DTE IRON BUTTERFLY STRATEGY BACKTEST")
    print("="*50)
    print(f"Backtest Period:      {df['Date'].iloc[0]} to {df['Date'].iloc[-1]}")
    print(f"Total Trading Days:   {total_days}")
    print(f"Trades Entered:       {trades_count} ({trades_count/total_days*100:.1f}% entry rate)")
    
    if trades_count > 0:
        wins = trade_df[trade_df['PnL'] > 0]
        losses = trade_df[trade_df['PnL'] <= 0]
        win_rate = len(wins) / trades_count
        total_pnl = trade_df['PnL'].sum()
        avg_pnl = trade_df['PnL'].mean()
        max_win = trade_df['PnL'].max()
        max_loss = trade_df['PnL'].min()
        
        print(f"Win Rate:             {win_rate:.2%}")
        print(f"Wins:                 {len(wins)}")
        print(f"Losses:               {len(losses)}")
        print(f"Total Net PnL:        ${total_pnl:+,.2f}")
        print(f"Avg PnL per Trade:    ${avg_pnl:+,.2f}")
        print(f"Max Win:              ${max_win:+,.2f}")
        print(f"Max Loss:             ${max_loss:+,.2f}")
        print(f"Max Capital Drawdown: {max_drawdown:.2%}")
        print(f"Final Capital:        ${capital:,.2f} (from ${initial_capital:,.2f})")
    else:
        print("No trades were entered under these parameters (Premium threshold too high or VIX too low).")
    print("="*50 + "\n")
    
    if trades_count > 0:
        trade_df.to_csv("butterfly_backtest_results.csv", index=False)
        print("Detailed trade log saved to butterfly_backtest_results.csv")

if __name__ == '__main__':
    # Run strategy with user's parameters (Minimum Premium: $8.00, Take Profit: 50%)
    run_backtest(
        wing_width=10, 
        min_premium=8.00, 
        take_profit_pct=0.50,
        slippage=0.10, 
        strike_step=5, 
        initial_capital=10000.0
    )
