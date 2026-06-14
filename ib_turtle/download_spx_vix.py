import yfinance as yf
import pandas as pd
import datetime

def download_backtest_data():
    print("Downloading historical data for SPX and VIX...")
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    # Let's get 5 years of historical daily data
    start_date = (datetime.datetime.now() - datetime.timedelta(days=5*365)).strftime('%Y-%m-%d')
    
    spx = yf.download("^SPX", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    if isinstance(spx.columns, pd.MultiIndex):
        spx.columns = spx.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
        
    # Rename columns to avoid collision
    spx = spx[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    spx.columns = ['SPX_Open', 'SPX_High', 'SPX_Low', 'SPX_Close', 'SPX_Volume']
    
    vix = vix[['Open', 'High', 'Low', 'Close']].copy()
    vix.columns = ['VIX_Open', 'VIX_High', 'VIX_Low', 'VIX_Close']
    
    # Merge on index
    merged = pd.merge(spx, vix, left_index=True, right_index=True, how='inner')
    merged.index = pd.to_datetime(merged.index).strftime('%Y-%m-%d')
    
    merged_file = "spx_vix_historical.csv"
    merged.to_csv(merged_file)
    print(f"Successfully downloaded and saved {len(merged)} days of data to {merged_file}")

if __name__ == '__main__':
    download_backtest_data()
