"""Live trading service for the small-cap gap-short system, with a phone control app.

Modes:
  demo    replays recent history through the mock broker, no TWS needed (for trying the app)
  shadow  connects to TWS read-only and logs the orders it would send
  paper   sends real orders to an IBKR paper account (account id must start with "DU")
  live    sends real orders to a live account (requires allow_live = true)
"""
