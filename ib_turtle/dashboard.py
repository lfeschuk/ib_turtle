import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Fund Dashboard", layout="wide")

st.title("🐢 Quantitative Turtle Fund")

# Connect to the bot's memory
conn = sqlite3.connect("trading_state.db")

# 1. Show Capital
cap_df = pd.read_sql("SELECT virtual_capital FROM bot_state WHERE ticker='MASTER_ACCOUNT'", conn)
if not cap_df.empty:
    current_cap = cap_df.iloc[0]['virtual_capital']
    st.metric(label="Virtual Capital Available", value=f"${current_cap:,.2f}")

# 2. Show the Trade Log
st.subheader("Recent Activity Log")
log_df = pd.read_sql("SELECT date, ticker, action, price FROM trade_log ORDER BY id DESC LIMIT 15", conn)

if log_df.empty:
    st.info("No trades logged yet. Run the engine to start tracking!")
else:
    st.dataframe(log_df, use_container_width=True)

# 3. Show System States
st.subheader("Internal System State (S1 vs S2)")
state_df = pd.read_sql("SELECT ticker, last_trade_won FROM bot_state WHERE ticker != 'MASTER_ACCOUNT'", conn)
if not state_df.empty:
    state_df['Active System'] = state_df['last_trade_won'].apply(lambda x: "System 2 (55-Day)" if x else "System 1 (20-Day)")
    st.dataframe(state_df[['ticker', 'Active System']], use_container_width=True)