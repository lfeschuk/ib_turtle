"""Command line for the live service.

  python -m trading_system.live.main set-password     --config ~/.config/gapshort/config.toml
  python -m trading_system.live.main check            --config ~/.config/gapshort/config.toml
  python -m trading_system.live.main run              --config ~/.config/gapshort/config.toml
  python -m trading_system.live.main reset-year-start --config ~/.config/gapshort/config.toml
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import sys

from .auth import MIN_PASSWORD_LEN, hash_password
from .config import LiveConfig, load_config, load_secrets, save_secrets
from .journal import Journal

log = logging.getLogger("gapshort")


def _journal(cfg: LiveConfig) -> Journal:
    return Journal(cfg.data_path / f"gapshort-{cfg.mode}.db")


def cmd_reset_year_start(cfg: LiveConfig) -> int:
    """Make the last recorded equity this year's starting point for the house-money sizing.

    Use it after a deposit or withdrawal (once the bot has recorded the new equity after the close), or when
    switching to "perbet_house" in the middle of a year, so that only trading profit counts as house money.
    """
    journal = _journal(cfg)
    last = journal.last_equity_before("9999-12-31")
    if not last:
        print("No equity recorded yet. The bot records it after each close; try again tomorrow.")
        return 1
    journal.set("year_start_day", last["day"])
    journal.set("year_start_adj", repr(float(last["adj"])))
    print(f"House-money starting point set to ${last['adj']:,.0f} (equity of {last['day']}, net of tax owed). "
          f"It applies until the end of {last['day'][:4]}.")
    return 0


def cmd_set_password(cfg: LiveConfig) -> int:
    pw = getpass.getpass("New app password (12+ characters): ")
    if len(pw) < MIN_PASSWORD_LEN or len(pw) > 256:
        print(f"Use {MIN_PASSWORD_LEN} to 256 characters.")
        return 1
    if getpass.getpass("Repeat it: ") != pw:
        print("The two entries differ.")
        return 1
    secrets = load_secrets(cfg) if cfg.secrets_file.exists() else {}
    secrets["password_hash"] = hash_password(pw)
    save_secrets(cfg, secrets)
    for db in cfg.data_path.glob("gapshort-*.db"):
        Journal(db).delete_all_sessions()  # a new password signs out every phone
    print(f"Saved to {cfg.secrets_file} (readable only by you). All app sessions were signed out.")
    return 0


async def _check(cfg: LiveConfig, symbol: str) -> int:
    from .borrow import BorrowTable
    from .broker import IBKRBroker

    broker = IBKRBroker(cfg, readonly=True, borrow=BorrowTable(cfg.data_path / "ibkr_usa.txt"))
    try:
        await broker.connect()
    except (OSError, asyncio.TimeoutError) as exc:
        print(f"Cannot reach TWS on {cfg.tws_host}:{cfg.tws_port} ({type(exc).__name__}). Is TWS running and logged in, "
              f"with 'Enable ActiveX and Socket Clients' on and socket port {cfg.tws_port}?")
        return 2
    except RuntimeError as exc:
        print(f"Connected, but: {exc}")
        return 2
    try:
        acct = await broker.account()
        print(f"Connected. Account {acct.account_id[:2]}****{acct.account_id[-3:]}, "
              f"net liquidation ${acct.net_liquidation:,.0f}")
        bars = await broker.daily_bars(symbol, days=3)
        for b in bars:
            print(f"  {symbol} {b.day}: close {b.close:.2f}, volume {b.volume:,.0f}")
        print("  If these volumes look 100x too small, untick 'Send market data in lots for US stocks' in TWS API "
              "settings.")
        movers = await broker.movers()
        print(f"Scanner returned {len(movers)} symbols, e.g. {', '.join(movers[:8])}")
        q = await broker.borrow_check(symbol, bars)
        print(f"{symbol}: {q['available']:,.0f} shares available to short, fee {q['fee']}")
    finally:
        await broker.disconnect()
    return 0


async def _run(cfg: LiveConfig) -> int:
    import uvicorn

    from .auth import AuthStore
    from .borrow import BorrowTable
    from .broker import IBKRBroker, SimBroker
    from .bwb_broker import IBKRBwbBroker, SimBwbBroker
    from .bwb_service import BwbBotService
    from .live_strategy import PerBetModel
    from .notify import Notifier
    from .service import BotService
    from .web_server import create_app

    secrets = load_secrets(cfg)
    if not secrets.get("password_hash"):
        print("Set an app password first: python -m trading_system.live.main set-password --config <file>")
        return 1
    journal = _journal(cfg)
    model = PerBetModel(cfg.sizing.model_path) if cfg.sizing.mode != "static" else None
    if cfg.mode == "demo":
        try:
            broker = SimBroker(cfg)
        except ImportError:
            print("Demo mode needs the research code and price data, which are not part of the laptop package. "
                  "Use mode = \"shadow\" on the laptop.")
            return 1
    else:
        broker = IBKRBroker(cfg, readonly=(cfg.mode == "shadow"), borrow=BorrowTable(cfg.data_path / "ibkr_usa.txt"))
    notifier = Notifier(cfg, secrets)
    service = BotService(cfg, broker, journal, notifier, model)

    bwb_service = None
    bwb_broker = None
    if cfg.bwb.enabled:
        bwb_journal = Journal(cfg.data_path / f"bwb-{cfg.mode}.db")
        if cfg.mode == "demo":
            bwb_broker = SimBwbBroker(cfg)
        else:
            bwb_broker = IBKRBwbBroker(cfg, readonly=(cfg.mode == "shadow"))
        bwb_service = BwbBotService(cfg, bwb_broker, bwb_journal, notifier)

    app = create_app(service, cfg, AuthStore(journal, secrets["password_hash"]), bwb_service=bwb_service)
    server = uvicorn.Server(uvicorn.Config(app, host=cfg.http_host, port=cfg.http_port, log_level="info",
                                           access_log=False, server_header=False, proxy_headers=False))
    log.info("app on http://%s:%s (mode %s, bwb_enabled=%s)", cfg.http_host, cfg.http_port, cfg.mode, cfg.bwb.enabled)
    tasks = [asyncio.create_task(server.serve()), asyncio.create_task(service.run())]
    if bwb_service is not None:
        tasks.append(asyncio.create_task(bwb_service.run()))
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    service.stop()
    if bwb_service is not None:
        bwb_service.stop()
    server.should_exit = True
    for t in pending:
        try:
            await asyncio.wait_for(t, timeout=10)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            t.cancel()
    await broker.disconnect()
    if bwb_broker is not None:
        await bwb_broker.disconnect()
    for t in done:
        if t.exception():
            raise t.exception()
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="gapshort")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("run", "set-password", "check", "reset-year-start"):
        sp = sub.add_parser(name)
        sp.add_argument("--config", required=True)
        if name == "check":
            sp.add_argument("--symbol", default="AAPL")
    args = p.parse_args(argv)
    cfg = load_config(args.config)
    if args.cmd == "set-password":
        return cmd_set_password(cfg)
    if args.cmd == "reset-year-start":
        return cmd_reset_year_start(cfg)
    if args.cmd == "check":
        return asyncio.run(_check(cfg, args.symbol))
    return asyncio.run(_run(cfg))


if __name__ == "__main__":
    sys.exit(main())
