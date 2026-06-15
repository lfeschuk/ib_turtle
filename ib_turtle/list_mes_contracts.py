from ib_insync import *
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def main():
    ib = IB()
    port = 4002
    try:
        ib.connect('127.0.0.1', port, clientId=98)
    except:
        port = 7497
        try:
            ib.connect('127.0.0.1', port, clientId=98)
        except Exception as e:
            logger.error(f"Could not connect to TWS on ports 4002/7497: {e}")
            return

    logger.info(f"Connected on port {port}. Running MES diagnostics...")

    # Test 1: GLOBEX exchange (with multiplier)
    logger.info("Test 1: Querying MES on GLOBEX with multiplier...")
    c1 = Future('MES', multiplier='5', exchange='GLOBEX', currency='USD')
    try:
        details = ib.reqContractDetails(c1)
        logger.info(f"-> Test 1 resolved {len(details)} contracts.")
        for d in details[:3]:
            logger.info(f"   Symbol={d.contract.symbol}, Local={d.contract.localSymbol}, Expiry={d.contract.lastTradeDateOrContractMonth}, Exchange={d.contract.exchange}")
    except Exception as e:
        logger.error(f"-> Test 1 failed: {e}")

    # Test 2: CME exchange (with multiplier)
    logger.info("Test 2: Querying MES on CME with multiplier...")
    c2 = Future('MES', multiplier='5', exchange='CME', currency='USD')
    try:
        details = ib.reqContractDetails(c2)
        logger.info(f"-> Test 2 resolved {len(details)} contracts.")
        for d in details[:3]:
            logger.info(f"   Symbol={d.contract.symbol}, Local={d.contract.localSymbol}, Expiry={d.contract.lastTradeDateOrContractMonth}, Exchange={d.contract.exchange}")
    except Exception as e:
        logger.error(f"-> Test 2 failed: {e}")

    # Test 3: No exchange specified (with multiplier)
    logger.info("Test 3: Querying MES with NO exchange specified (Global Search)...")
    c3 = Future('MES', multiplier='5', currency='USD')
    try:
        details = ib.reqContractDetails(c3)
        logger.info(f"-> Test 3 resolved {len(details)} contracts.")
        for d in details[:3]:
            logger.info(f"   Symbol={d.contract.symbol}, Local={d.contract.localSymbol}, Expiry={d.contract.lastTradeDateOrContractMonth}, Exchange={d.contract.exchange}")
    except Exception as e:
        logger.error(f"-> Test 3 failed: {e}")

    # Test 4: Check if symbol is 'ES' instead of 'MES' (for control)
    logger.info("Test 4: Querying ES on GLOBEX (standard E-mini control test)...")
    c4 = Future('ES', multiplier='50', exchange='GLOBEX', currency='USD')
    try:
        details = ib.reqContractDetails(c4)
        logger.info(f"-> Test 4 resolved {len(details)} contracts.")
        for d in details[:3]:
            logger.info(f"   Symbol={d.contract.symbol}, Local={d.contract.localSymbol}, Expiry={d.contract.lastTradeDateOrContractMonth}, Exchange={d.contract.exchange}")
    except Exception as e:
        logger.error(f"-> Test 4 failed: {e}")

    ib.disconnect()
    logger.info("Diagnostics completed.")

if __name__ == '__main__':
    main()
