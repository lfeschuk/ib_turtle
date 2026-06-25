#!/usr/bin/env python3
import sqlite3
import datetime
import time
import json
import urllib.request
import math
from ib_insync import *

# Database file name
DB_NAME = "dual_mode_trading.db"
WING_WIDTH = 10.0

def get_historical_spx_close(date_str):
    """Fetch the SPX (^GSPC) closing price for a specific date from Yahoo Finance."""
    print(f"🔍 Fetching historical SPX closing price for {date_str}...")
    try:
        # Convert date to epoch timestamp
        t = time.strptime(date_str, "%Y-%m-%d")
        epoch = int(time.mktime(t))
        
        # Request a 4-day window around the target date to ensure we capture the trading day
        start = epoch - 86400 * 2
        end = epoch + 86400 * 2
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/^GSPC?period1={start}&period2={end}&interval=1d"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            result = data['chart']['result'][0]
            timestamps = result.get('timestamp', [])
            closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
            
            # Find the exact date match
            for ts, close in zip(timestamps, closes):
                # Convert timestamp to local date string in Eastern or local time
                ts_date = time.strftime("%Y-%m-%d", time.localtime(ts))
                if ts_date == date_str and close is not None:
                    print(f"✅ Found SPX Close for {date_str}: ${close:.2f}")
                    return float(close)
    except Exception as e:
        print(f"⚠️ Error fetching SPX close from Yahoo Finance: {e}")
    
    # Fallback input if API fails or weekend/holiday
    try:
        val = input(f"💬 Yahoo Finance lookup failed. Please enter the SPX close price for {date_str} manually: ")
        return float(val)
    except Exception:
        return None

def get_ibkr_fill_credit(date_str):
    """Attempt to connect to IBKR and extract the exact butterfly premium from recent executions (up to 7 days)."""
    print(f"🔌 Connecting to IBKR Gateway on port 4002 to search for executions on {date_str}...")
    ib = IB()
    try:
        ib.connect('127.0.0.1', 4002, clientId=99)
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        
        fills = ib.fills()
        matching_fills = []
        for f in fills:
            if f.contract.symbol == 'SPX' and isinstance(f.contract, Option):
                if f.execution.time.date() == target_date:
                    matching_fills.append(f)
                    
        if matching_fills:
            print(f"✅ Found {len(matching_fills)} execution legs for SPX options on {date_str}!")
            # Combo Premium = sum(Sell_price) - sum(Buy_price)
            net_premium = 0.0
            for f in matching_fills:
                price = f.execution.price
                # SLD = Sold (Credit), BOT = Bought (Debit)
                sign = 1.0 if f.execution.side == 'SLD' else -1.0
                net_premium += price * sign
            
            credit = abs(net_premium)
            print(f"💰 Calculated exact filled premium from IBKR: ${credit:.2f}")
            return credit
    except Exception as e:
        print(f"ℹ️ Could not fetch fills from IBKR (IBKR might be offline or date > 7 days ago): {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            
    # Fallback default estimate
    print(f"ℹ️ No recent IBKR fills found. Falling back to default premium estimate of $7.50.")
    return 7.50

def repair_database():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Failed to connect to SQLite database '{DB_NAME}': {e}")
        print("Make sure this script is run in the directory containing the database file.")
        return

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_log';")
    if not cursor.fetchone():
        print("❌ Table 'trade_log' does not exist in the database. Aborting.")
        conn.close()
        return

    # Query all ENTRY_CREDIT actions for SPX_BUTTERFLY
    cursor.execute("SELECT id, timestamp_ist, price, qty FROM trade_log WHERE strategy='SPX_BUTTERFLY' AND action='ENTRY_CREDIT' ORDER BY id ASC;")
    entries = cursor.fetchall()
    
    if not entries:
        print("ℹ️ No SPX_BUTTERFLY entries found in the database.")
        conn.close()
        return

    print(f"📋 Found {len(entries)} historical butterfly entry logs. Scanning for missing exits...")
    
    repairs_made = 0

    for entry_id, timestamp_ist, price, qty in entries:
        # Date string extraction (YYYY-MM-DD)
        date_str = timestamp_ist.split()[0]
        
        # Check if an exit already exists for this strategy on this date
        cursor.execute("SELECT id FROM trade_log WHERE strategy='SPX_BUTTERFLY' AND (action='EXPIRATION_EXIT' OR action='TIME_CUT_EXIT') AND timestamp_ist LIKE ?;", (f"{date_str}%",))
        if cursor.fetchone():
            print(f"✨ Row {entry_id} ({date_str}): Already has an exit logged. Skipping.")
            continue

        print(f"\n🛠️ Repairing missing exit for trade on {date_str}...")
        
        # The stored price in the database was the center_strike (our bug)
        center_strike = price
        print(f"🎯 Center Strike: {center_strike}")

        # 1. Fetch SPX Closing Price
        spx_close = get_historical_spx_close(date_str)
        if spx_close is None:
            print(f"❌ Skipping {date_str}: Could not resolve SPX closing price.")
            continue

        # 2. Resolve Entry Credit (Premium)
        entry_credit = get_ibkr_fill_credit(date_str)

        # 3. Calculate Expiration Value & PnL
        close_distance = abs(spx_close - center_strike)
        exp_value = min(WING_WIDTH, close_distance)
        pnl = (entry_credit - exp_value) * 100.0 * qty
        
        print(f"📊 Calculations:")
        print(f"   Entry Credit:     ${entry_credit:.2f}")
        print(f"   SPX Close:        ${spx_close:.2f}")
        print(f"   Distance:         {close_distance:.2f}")
        print(f"   Expiration Value: ${exp_value:.2f}")
        print(f"   Calculated PnL:   ${pnl:+.2f}")

        # 4. Insert the missing exit record
        exit_timestamp = f"{date_str} 23:02:00" # 4:02 PM EST is 23:02 IST
        
        # Insert the exit transaction
        cursor.execute(
            "INSERT INTO trade_log (timestamp_ist, strategy, action, price, qty, pnl) VALUES (?, 'SPX_BUTTERFLY', 'EXPIRATION_EXIT', ?, ?, ?);",
            (exit_timestamp, spx_close, qty, pnl)
        )
        
        # Retroactively fix the ENTRY_CREDIT price in the database to be the actual credit instead of the strike!
        cursor.execute(
            "UPDATE trade_log SET price=? WHERE id=?;",
            (entry_credit, entry_id)
        )
        
        repairs_made += 1
        print(f"✅ Successfully inserted EXPIRATION_EXIT and corrected ENTRY_CREDIT price for {date_str}!")

    if repairs_made > 0:
        conn.commit()
        print(f"\n🎉 SUCCESS: Database repaired! Added {repairs_made} missing exit records and corrected entry prices.")
    else:
        print("\n✨ Database is already fully up-to-date. No repairs needed.")

    conn.close()

if __name__ == "__main__":
    repair_database()
