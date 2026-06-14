import pandas as pd
import numpy as np

def analyze_market_movements(csv_path="spx_vix_hourly.csv"):
    df = pd.read_csv(csv_path)
    
    # 1:30 PM EST is 20:30 IST. Close is 23:00 IST (the 15:30:00 bar close or 16:00:00 close).
    # Let's align by Date
    close_df = df[df['Time'] == '15:30:00'][['Date', 'SPX_Close']].copy()
    close_df.columns = ['Date', 'Day_Close']
    
    entry_df = df[df['Time'] == '13:30:00'][['Date', 'SPX_Open', 'VIX_Open']].copy()
    entry_df.columns = ['Date', 'SPX_1330', 'VIX_1330']
    
    data = pd.merge(entry_df, close_df, on='Date', how='inner')
    data = data.sort_values('Date').reset_index(drop=True)
    
    # Calculate absolute and raw SPX move from 1:30 PM to Close
    data['SPX_Move'] = data['Day_Close'] - data['SPX_1330']
    data['Abs_SPX_Move'] = data['SPX_Move'].abs()
    
    # Split into low/high VIX groups
    low_vix = data[data['VIX_1330'] <= 20.0]
    high_vix = data[data['VIX_1330'] > 20.0]
    
    print("="*65)
    print("             INTRADAY SPX MOVEMENT ANALYSIS (1:30 PM TO CLOSE)")
    print("="*65)
    print(f"Total Trading Days: {len(data)}")
    print(f"Low Volatility Days (VIX <= 20): {len(low_vix)} ({len(low_vix)/len(data)*100:.1f}%)")
    print(f"High Volatility Days (VIX > 20):  {len(high_vix)} ({len(high_vix)/len(data)*100:.1f}%)")
    print("-" * 65)
    
    print(f"ALL DAYS:")
    print(f"  Average Absolute Move: {data['Abs_SPX_Move'].mean():.2f} points")
    print(f"  Standard Deviation:   {data['SPX_Move'].std():.2f} points")
    print(f"  Max Absolute Move:    {data['Abs_SPX_Move'].max():.2f} points")
    print(f"  Percentage of days move > 10 pts: {len(data[data['Abs_SPX_Move'] > 10]) / len(data) * 100:.1f}%")
    print(f"  Percentage of days move > 20 pts: {len(data[data['Abs_SPX_Move'] > 20]) / len(data) * 100:.1f}%")
    print("-" * 65)
    
    if len(low_vix) > 0:
        print(f"LOW VOLATILITY DAYS (VIX <= 20):")
        print(f"  Average Absolute Move: {low_vix['Abs_SPX_Move'].mean():.2f} points")
        print(f"  Standard Deviation:   {low_vix['SPX_Move'].std():.2f} points")
        print(f"  Max Absolute Move:    {low_vix['Abs_SPX_Move'].max():.2f} points")
        print(f"  Percentage of days move > 10 pts: {len(low_vix[low_vix['Abs_SPX_Move'] > 10]) / len(low_vix) * 100:.1f}%")
        print(f"  Percentage of days move > 20 pts: {len(low_vix[low_vix['Abs_SPX_Move'] > 20]) / len(low_vix) * 100:.1f}%")
        print("-" * 65)
        
    if len(high_vix) > 0:
        print(f"HIGH VOLATILITY DAYS (VIX > 20):")
        print(f"  Average Absolute Move: {high_vix['Abs_SPX_Move'].mean():.2f} points")
        print(f"  Standard Deviation:   {high_vix['SPX_Move'].std():.2f} points")
        print(f"  Max Absolute Move:    {high_vix['Abs_SPX_Move'].max():.2f} points")
        print(f"  Percentage of days move > 10 pts: {len(high_vix[high_vix['Abs_SPX_Move'] > 10]) / len(high_vix) * 100:.1f}%")
        print(f"  Percentage of days move > 20 pts: {len(high_vix[high_vix['Abs_SPX_Move'] > 20]) / len(high_vix) * 100:.1f}%")
        print(f"  Percentage of days move > 30 pts: {len(high_vix[high_vix['Abs_SPX_Move'] > 30]) / len(high_vix) * 100:.1f}%")
        print("="*65)
        
if __name__ == '__main__':
    analyze_market_movements()
