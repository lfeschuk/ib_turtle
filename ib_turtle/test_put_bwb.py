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

def calculate_put_bwb_premium(S, K_short, T_hours, vix, upper_gap=10, lower_gap=20):
    T = (T_hours / 6.5) / 252.0
    r = 0.05
    sigma = vix / 100.0
    
    # Put BWB legs:
    # Buy 1 Put at K_short + upper_gap (ITM)
    # Sell 2 Puts at K_short (ATM)
    # Buy 1 Put at K_short - lower_gap (OTM)
    val_long_upper = black_scholes_value(S, K_short + upper_gap, T, r, sigma, 'P')
    val_short = black_scholes_value(S, K_short, T, r, sigma, 'P')
    val_long_lower = black_scholes_value(S, K_short - lower_gap, T, r, sigma, 'P')
    
    # Net Credit (Short value * 2 - Longs)
    # Note: If this is negative, it's a debit. We want a credit!
    return (2 * val_short) - val_long_upper - val_long_lower

def run_bwb_backtest(csv_path="spx_vix_hourly.csv", slippage=0.15, strike_step=5):
    df = pd.read_csv(csv_path)
    
    time_str = "13:30:00"
    hours_left = 2.5
    
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    time_df = df[df['Time'] == time_str].copy()
    data = pd.merge(time_df, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    
    # Filter for VIX <= 20
    data = data[data['VIX_Open'] <= 20.0].copy()
    
    # We will test two BWB configurations:
    # 1. 10/20 BWB: Upper gap = 10, Lower gap = 20
    # 2. 15/30 BWB: Upper gap = 15, Lower gap = 30
    
    print("="*115)
    print("          0 DTE SPX PUT BROKEN WING BUTTERFLY BACKTEST (VIX <= 20, 1:30 PM EST ENTRY, 1 CONTRACT)")
    print("="*115)
    print(f"{'BWB Config':<15} | {'Trades':<8} | {'Win Rate (%)':<12} | {'Total Net PnL':<15} | {'Avg Premium':<12} | {'Max DD ($)':<12}")
    print("-" * 115)
    
    for upper_g, lower_g in [(10, 20), (15, 30)]:
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
            
            # Net premium after slippage
            net_premium = raw_bwb - slippage
            
            trades += 1
            sum_prem += net_premium
            
            # Payout logic:
            # Let loss_upper = max(0, spx_close - (k_short + upper_g))  # No loss on upside since it's a Put BWB
            # The value of Put BWB at expiration is:
            # val = Max(0, (k_short + upper_g) - SPX) - 2 * Max(0, k_short - SPX) + Max(0, (k_short - lower_g) - SPX)
            val_long_upper = max(0.0, (k_short + upper_g) - spx_close)
            val_shorts = 2 * max(0.0, k_short - spx_close)
            val_long_lower = max(0.0, (k_short - lower_g) - spx_close)
            
            final_value = val_long_upper - val_shorts + val_long_lower
            
            # PnL = (Final Value - Initial Net Premium) * 100
            # Wait, since we SOLD the BWB to collect premium, our PnL is:
            # PnL = (Initial Net Premium - Final Value) * 100
            # Let's verify this:
            # If SPX stays high (e.g. > k_short + upper_g), final_value = 0. We keep the credit!
            # If SPX closes exactly at k_short: final_value = upper_g.
            # We get to buy it back at upper_g, so PnL = (net_premium - upper_g) * 100?
            # Wait, no! We BOUGHT the upper wing (long put) and SOLD the center.
            # If SPX closes at k_short, the upper put is worth upper_g, shorts are worth 0, lower put is worth 0.
            # So the butterfly is worth upper_g. Since we collected net_premium at entry, our net cash flow is:
            # net_premium + upper_g?
            # No:
            # If we enter a credit BWB: we receive cash = credit.
            # At expiry:
            # - If SPX > K_short + upper_g: all puts are worthless. PnL = credit * 100.
            # - If SPX = K_short: Upper long put is worth upper_g. Shorts/lower are 0. We exercise upper put for +upper_g.
            #   So PnL = (credit + upper_g) * 100!
            # - If SPX < K_short - lower_g:
            #   Upper put is worth (K_short + upper_g - SPX)
            #   Short puts are worth -2 * (K_short - SPX)
            #   Lower put is worth (K_short - lower_g - SPX)
            #   Sum = (K_short + upper_g - SPX) - 2*K_short + 2*SPX + K_short - lower_g - SPX = upper_g - lower_g.
            #   Since lower_g > upper_g, this sum is negative, representing a net liability of (upper_g - lower_g) = -10 (for 10/20 BWB).
            #   So we have to pay 10.00 to settle. PnL = (credit - 10.00) * 100.
            # This is the exact math of a Put BWB!
            
            payout = net_premium + final_value
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
        avg_prem = sum_prem / trades if trades > 0 else 0.0
        config_label = f"+{upper_g}/-{lower_g} BWB"
        print(f"{config_label:<15} | {trades:<8} | {win_rate*100:<11.1f}% | ${total_pnl:<+13,.2f} | ${avg_prem:<10.2f} | ${max_dd:,.2f}")
    print("="*115)

if __name__ == '__main__':
    run_bwb_backtest()
