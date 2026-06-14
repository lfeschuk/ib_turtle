import yfinance as yf
import pandas as pd
import pytz

def download_hourly_data():
    print("Downloading historical hourly data for SPX and VIX (last 730 days)...")
    
    spx = yf.download("^SPX", period="730d", interval="1h", progress=False)
    vix = yf.download("^VIX", period="730d", interval="1h", progress=False)
    
    if spx.empty or vix.empty:
        print("Error: Could not retrieve data.")
        return
        
    if isinstance(spx.columns, pd.MultiIndex):
        spx.columns = spx.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
        
    # Convert timezone to Eastern Time and sort indices
    spx.index = spx.index.tz_convert('US/Eastern')
    vix.index = vix.index.tz_convert('US/Eastern')
    
    # Convert indices to columns and sort for merge_asof
    spx = spx.reset_index().sort_values('Datetime')
    vix = vix.reset_index().sort_values('Datetime')
    
    # Keep and rename columns
    spx = spx[['Datetime', 'Open', 'High', 'Low', 'Close']].copy()
    spx.columns = ['Datetime', 'SPX_Open', 'SPX_High', 'SPX_Low', 'SPX_Close']
    
    vix = vix[['Datetime', 'Open', 'High', 'Low', 'Close']].copy()
    vix.columns = ['Datetime', 'VIX_Open', 'VIX_High', 'VIX_Low', 'VIX_Close']
    
    # Merge using merge_asof
    merged = pd.merge_asof(spx, vix, on='Datetime', direction='backward')
    
    # Extract string representation of Date and Time from Datetime column
    merged['Date'] = merged['Datetime'].dt.strftime('%Y-%m-%d')
    merged['Time'] = merged['Datetime'].dt.strftime('%H:%M:%S')
    
    # Rearrange columns
    merged = merged[['Date', 'Time', 'SPX_Open', 'SPX_High', 'SPX_Low', 'SPX_Close', 'VIX_Open', 'VIX_High', 'VIX_Low', 'VIX_Close']]
    
    output_file = "spx_vix_hourly.csv"
    merged.to_csv(output_file, index=False)
    print(f"Successfully downloaded and saved {len(merged)} hourly rows to {output_file}")

if __name__ == '__main__':
    download_hourly_data()
