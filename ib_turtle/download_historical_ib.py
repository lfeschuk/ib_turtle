import sqlite3
import pandas as pd
import numpy as np
import logging
import datetime
import pytz
import time
from ib_insync import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

def download_historical_chunk(ib, contract, end_date_str, duration_str):
    print(f"Requesting {duration_str} hourly data ending at {end_date_str} for {contract.symbol}...")
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=end_date_str,
        durationStr=duration_str,
        barSizeSetting='1 hour',
        whatToShow='TRADES',
        useRTH=True,
        keepUpToDate=False
    )
    if not bars:
        print(f"Warning: No bars returned for {contract.symbol} ending {end_date_str}")
        return pd.DataFrame()
        
    records = []
    for b in bars:
        # Convert date to EST string
        dt = b.date
        if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
            # Convert date to datetime
            dt = datetime.datetime.combine(dt, datetime.time(9, 30))
        # Ensure it is timezone aware or local
        records.append({
            "Datetime": dt,
            "Open": b.open,
            "High": b.high,
            "Low": b.low,
            "Close": b.close
        })
    df = pd.DataFrame(records)
    return df

def main():
    ib = IB()
    port = 4002
    try:
        ib.connect('127.0.0.1', port, clientId=99)
        print(f"Connected on port {port}")
    except Exception:
        port = 7497
        try:
            ib.connect('127.0.0.1', port, clientId=99)
            print(f"Connected on port {port}")
        except Exception as e:
            print(f"Could not connect to TWS on ports 4002/7497: {e}")
            print("Please ensure IBKR TWS or Gateway is running and API connections are enabled.")
            return

    spx = Index('SPX', 'CBOE')
    vix = Index('VIX', 'CBOE')
    ib.qualifyContracts(spx, vix)

    # We want 2020-01-01 to 2023-07-18 (which connects to the start of our other data)
    # We will download in 1-year chunks:
    # 1. 2021-01-01 (covers 2020)
    # 2. 2022-01-01 (covers 2021)
    # 3. 2023-01-01 (covers 2022)
    # 4. 2023-07-19 (covers early 2023)
    
    chunks = [
        ('20210101 23:59:59', '1 Y'),
        ('20220101 23:59:59', '1 Y'),
        ('20230101 23:59:59', '1 Y'),
        ('20230719 23:59:59', '7 M')
    ]
    
    spx_dfs = []
    vix_dfs = []
    
    for end_date, dur in chunks:
        spx_chunk = download_historical_chunk(ib, spx, end_date, dur)
        if not spx_chunk.empty:
            spx_dfs.append(spx_chunk)
            
        vix_chunk = download_historical_chunk(ib, vix, end_date, dur)
        if not vix_chunk.empty:
            vix_dfs.append(vix_chunk)
            
        ib.sleep(2.0)
        
    ib.disconnect()
    
    if not spx_dfs or not vix_dfs:
        print("Failed to download SPX or VIX data.")
        return
        
    spx_all = pd.concat(spx_dfs).drop_duplicates(subset=['Datetime']).sort_values('Datetime').reset_index(drop=True)
    vix_all = pd.concat(vix_dfs).drop_duplicates(subset=['Datetime']).sort_values('Datetime').reset_index(drop=True)
    
    print(f"Total SPX rows: {len(spx_all)} | Total VIX rows: {len(vix_all)}")
    
    # Align datetimes to string format for merging
    # Let's convert datetime object to timezone-naive Eastern Time strings
    est = pytz.timezone('US/Eastern')
    
    def process_datetime(df, prefix):
        df = df.copy()
        processed = []
        for idx, row in df.iterrows():
            dt = row['Datetime']
            # If timezone aware, convert to EST and make naive
            if dt.tzinfo is not None:
                dt_est = dt.astimezone(est).replace(tzinfo=None)
            else:
                dt_est = dt
            processed.append({
                "Date": dt_est.strftime('%Y-%m-%d'),
                "Time": dt_est.strftime('%H:%M:%S'),
                f"{prefix}_Open": row['Open'],
                f"{prefix}_High": row['High'],
                f"{prefix}_Low": row['Low'],
                f"{prefix}_Close": row['Close']
            })
        return pd.DataFrame(processed)
        
    spx_clean = process_datetime(spx_all, "SPX")
    vix_clean = process_datetime(vix_all, "VIX")
    
    # Merge on Date and Time
    merged = pd.merge(spx_clean, vix_clean, on=['Date', 'Time'], how='inner')
    merged = merged.sort_values(['Date', 'Time']).reset_index(drop=True)
    
    output_file = "spx_vix_hourly_2020_2023.csv"
    merged.to_csv(output_file, index=False)
    print(f"Successfully saved merged 2020-2023 hourly data ({len(merged)} rows) to {output_file}")

if __name__ == '__main__':
    main()
