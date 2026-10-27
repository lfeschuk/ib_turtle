# Dual-Strategy IBKR Trading Service (`Small-Cap Gap Short` + `0DTE SPX Put BWB`)

Runs two uncorrelated (`r ≈ 0.00`) automated strategies side-by-side against Interactive Brokers TWS/Gateway on your Ubuntu PC, controlled from an installable phone web app (PWA) over Tailscale HTTPS:

1. **Strategy 1 — Small-Cap 100%+ Gap Short (`clientId = 17`):** Scans at **15:45 ET** for 100%+ small-cap gap/surge exhaustion (`S3a`, `S5b`, `I3b`), verifies IBKR short availability and borrow rate (`<= 300%/yr`), places 3-leg OCA short bracket orders (`LOC` entry + server-side `STP` + `LMT` target), manages 3-day `MOC` exits, and reconciles at **16:15 ET**.
2. **Strategy 2 — Vol-Scaled 0DTE SPX Put BWB (`clientId = 18`):** Checks the causal `F1: VIX1D < VIX` contango gate at **10:30 AM ET**, constructs the volatility-scaled 4-leg `SPXW` / `XSP` Put Broken-Wing Butterfly (`+1 K_hi Put, -2 K_mid Put, +1 K_lo Put`), sizes contracts using the **Earned-Money / Yearly House-Money Kelly Ramp (`7.5% -> 20.0%`)**, places the Cboe `BAG` combo credit order, and reconciles cash settlement at **16:15 ET**.

---

## Repository Layout

- **`dist/gapshort-live-20261027.tar.gz`** & **`.sha256`**: Self-contained standalone package to copy to your Ubuntu PC (no corp paths, no research dependencies).
- **`deploy/README.md`**: Full step-by-step Ubuntu PC setup guide (identical copy below).
- **`deploy/config.example.toml`**: Annotated configuration file supporting both **2 Independent `$100k` Paper Ledgers (`$200k` total)** and **Shared `$100k` Capital (`isolated_capital = false` with `yearly_house` Jan-1 lock & `95%` combined margin guard)**.
- **`deploy/gapshort.service`**: `systemd` user service unit for unattended background operation.
- **`deploy/requirements-live.txt`**: Minimal Python dependencies for the PC (`numpy`, `pandas`, `ib_async`, `fastapi`, `uvicorn`).
- **`trading_system/`**: Full Python source code for both bots and the PWA web server.

---

## Quick PC Installation Summary

Copy `dist/gapshort-live-20261027.tar.gz` and `dist/gapshort-live-20261027.tar.gz.sha256` to `~/Downloads` on your Ubuntu PC and run:

```bash
cd ~/Downloads
sha256sum -c gapshort-live-20261027.tar.gz.sha256    # Must say OK
mkdir -p ~/gapshort
tar -xzf gapshort-live-20261027.tar.gz -C ~/gapshort
cd ~/gapshort
python3 -m venv .venv
.venv/bin/pip install -r deploy/requirements-live.txt
mkdir -p ~/.config/gapshort
cp deploy/config.example.toml ~/.config/gapshort/config.toml
.venv/bin/python -m trading_system.live.main set-password --config ~/.config/gapshort/config.toml
```

### Verify TWS Connection & Start the Background Service

```bash
# 1. Verify TWS API connection (with TWS open & logged into Paper Trading on port 7497)
~/gapshort/.venv/bin/python -m trading_system.live.main check --config ~/.config/gapshort/config.toml

# 2. Install & start the systemd background service
mkdir -p ~/.config/systemd/user
cp ~/gapshort/deploy/gapshort.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now gapshort
sudo loginctl enable-linger "$USER"

# 3. Publish the web app privately to your phone over Tailscale HTTPS
sudo tailscale serve --bg 8787
tailscale serve status
```

For full PC preparation, TWS settings, market data subscriptions, Independent (`$200k`) vs. Shared (`$100k`) capital configuration, and troubleshooting, see **[deploy/README.md](deploy/README.md)**.
