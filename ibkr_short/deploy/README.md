# Dual-Strategy IBKR Bot & Phone App — PC / Ubuntu Setup Guide

This service runs **two independent, uncorrelated (`r ≈ 0.00`) trading bots** side-by-side next to Interactive Brokers Trader Workstation (**TWS**) on your Ubuntu PC/laptop, and serves a single installable phone web app (**PWA**) over Tailscale HTTPS:

1. **Strategy 1 — Small-Cap 100%+ Gap Short (`client_id = 17`):**
   - Scans NYSE / NYSE American / Nasdaq at **15:45 ET** for 100%+ gap/surge exhaustion (`S3a`, `S5b`, `I3b`), checks IBKR borrow availability and fee rate (`<= 300%/yr`), submits 3-leg OCA bracket orders (`LOC` entry + server-side `STP` + `LMT` target), sends Day-3 `MOC` exits, and reconciles at **16:15 ET**.
2. **Strategy 2 — Vol-Scaled 0DTE SPX Put Broken-Wing Butterfly (`0DTE Put BWB`, `client_id = 18`):**
   - At **10:30 AM ET** (post-initial-balance), checks the causal term-structure gate (`F1: VIX1D < VIX` and prior close `VIX1D_prev < VIX_prev`), constructs the volatility-scaled 4-leg `SPXW` (or `XSP`) Put BWB (`+1 K_hi Put, -2 K_mid Put, +1 K_lo Put`), sizes contracts via the **Earned-Money ("House-Money") Kelly Ramp (`7.5% -> 20.0%`)**, submits the Cboe `BAG` combo credit order, and reconciles European cash settlement at **16:15 ET**.

```
Phone (PWA) ──Tailscale HTTPS──> PC: tailscale serve ──> FastAPI on 127.0.0.1:8787
                                                            ├── Strategy 1: Gap Short   (TWS 127.0.0.1:7497, clientId 17)
                                                            └── Strategy 2: 0DTE Put BWB (TWS 127.0.0.1:7497, clientId 18)
```

---

## What You Need on the PC Side

| Item | Notes |
| :--- | :--- |
| **IBKR Margin Account** | Required for shorting equities and trading defined-risk index option spreads (`SPXW` / `XSP` Level 3 spreads). Your free **Paper Trading (`DU*`)** account includes this automatically. |
| **Real-Time Market Data** | In IBKR Client Portal, subscribe to:<br>1. **US Securities Snapshot and Futures Value Bundle** + **US Equity and Options Add-On Streaming Bundle** (real-time US stocks + OPRA options for `SPXW`/`XSP`)<br>2. **Cboe Global Indices** (for live `SPX`, `VIX`, `VIX1D`).<br>Then enable **Share real-time market data with Paper Trading account** under *Settings → Paper Trading Account*. |
| **Ubuntu PC / Laptop** | Ubuntu 22.04 or 24.04, plugged into AC power, online, and awake during US market hours (**10:20 AM – 4:25 PM ET** on trading days). |
| **IBKR TWS Stable for Linux** | Logged into **Paper Trading** (port `7497`) or **Live** (port `7496`). |
| **Android Phone + Tailscale** | Chrome installs the phone app over your private Tailscale HTTPS URL. |
| **Deployment Package** | `dist/gapshort-live-20261026.tar.gz` (and `dist/gapshort-live-20261026.tar.gz.sha256`). |

---

## 1. Prepare the Ubuntu PC / Laptop (Once)

```bash
sudo apt update
sudo apt install -y python3-venv curl
python3 --version        # Python 3.10 or newer

# Keep running when the laptop lid is closed, and disable all sleep/suspend targets
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' \
  | sudo tee /etc/systemd/logind.conf.d/gapshort.conf
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

timedatectl              # Verify "System clock synchronized: yes"
```

Also in Ubuntu Desktop Settings:
- **Settings → Users:** Turn on **Automatic Login** so the desktop (and TWS) comes back automatically after a power cut.
- **Settings → Power:** Turn off **Automatic Suspend**.
- Reboot once (`sudo reboot`).
- *Optional (HP BIOS, F10 at boot):* Set **After Power Loss → Power On**.

---

## 2. Configure IB Gateway (Recommended) or TWS on the PC (Once)

**IB Gateway is actually preferred over full TWS** for unattended bots: it speaks the exact same IBKR socket protocol, supports multiple simultaneous `clientId` connections (`17` and `18`), uses ~80% less RAM/CPU, and has no chart/order-ticket GUI popups.

### Option 2A: Using IB Gateway (Recommended)
1. Launch **IB Gateway**, select **IB API**, toggle **Paper Trading**, and sign in.
2. In the top menu, open **Configure → Settings**:

   | Menu Path | Setting | Required Value |
   | :--- | :--- | :--- |
   | **API → Settings** | Socket port | **`4002`** (Paper default) / **`4001`** (Live default) |
   | **API → Settings** | Read-Only API | **OFF** (unchecked) for `paper` and `live` |
   | **API → Settings** | Allow connections from localhost only | **ON** (checked) |
   | **API → Precautions** | Bypass Order Precautions for API Orders (+ Bond / Negative Yield / Price Cap) | **ON** *(check all bypass boxes so IB Gateway never holds an API order waiting for a click)* |
   | **Lock and Exit** | Auto restart | **ON**, set outside `10:00–16:30 ET` (e.g., **`11:45 PM`**) |

3. **Important (`config.toml` port):** Because IB Gateway defaults to port **`4002`** (Paper) / **`4001`** (Live) instead of TWS's `7497`/`7496`, set `tws_port = 4002` in `~/.config/gapshort/config.toml` (see Section 4 below).

### Option 2B: Using Full Trader Workstation (TWS)
1. Launch **Trader Workstation**, select **Paper Trading**, and sign in.
2. Open **File → Global Configuration**:

   | Menu Path | Setting | Required Value |
   | :--- | :--- | :--- |
   | **API → Settings** | Enable ActiveX and Socket Clients | **ON** |
   | **API → Settings** | Socket port | **`7497`** (Paper) / **`7496`** (Live) |
   | **API → Settings** | Allow connections from localhost only | **ON** |
   | **API → Settings** | Read-Only API | **ON** for `shadow` mode; **OFF** for `paper` and `live` |
   | **API → Settings** | Send market data in lots for US stocks for dual-mode API clients | **OFF** *(critical: if ON, stock volumes are 100× too small)* |
   | **API → Precautions** | Bypass Order Precautions for API Orders | **ON** *(prevents TWS from holding API orders for a manual click)* |
   | **Lock and Exit** | Auto restart | **ON**, set outside `10:00–16:30 ET` (e.g., **`23:45`**) |

---

## 3. Install the Dual-Strategy Service on the PC (Once)

Copy `gapshort-live-20261026.tar.gz` and `gapshort-live-20261026.tar.gz.sha256` to `~/Downloads` on your PC, then run:

```bash
cd ~/Downloads
sha256sum -c gapshort-live-*.tar.gz.sha256          # Must print: OK
mkdir -p ~/gapshort
tar -xzf gapshort-live-*.tar.gz -C ~/gapshort
cd ~/gapshort
python3 -m venv .venv
.venv/bin/pip install -r deploy/requirements-live.txt
mkdir -p ~/.config/gapshort
cp deploy/config.example.toml ~/.config/gapshort/config.toml
.venv/bin/python -m trading_system.live.main set-password --config ~/.config/gapshort/config.toml
```

- Your app password (`12+` characters) is hashed with `scrypt` and stored in `~/.config/gapshort/secrets.json` (`chmod 600`).
- With TWS running and logged in, test the TWS socket connection:

```bash
.venv/bin/python -m trading_system.live.main check --config ~/.config/gapshort/config.toml
```

Test a manual foreground run first:

```bash
.venv/bin/python -m trading_system.live.main run --config ~/.config/gapshort/config.toml
```

Open `http://localhost:8787` in your PC browser, sign in, and verify you see the top strategy bar (**`Both ($200k)`** | **`Gap Short ($100k)`** | **`0DTE BWB ($100k)`**). Press `Ctrl+C` to stop the manual run.

---

## 4. Configure Independent (`2 × $100k`) vs. Shared (`1 × $100k`) Capital in `config.toml`

Edit `~/.config/gapshort/config.toml`:

### Option A: Two Independent `$100,000` Paper Ledgers (`$200,000` Combined — Default for Paper Monitoring)
Each strategy tracks and compounds its own isolated `$100,000` ledger (`gapshort-paper.db` and `bwb-paper.db`), so you can evaluate both strategies independently side-by-side:

```toml
mode = "paper"
tws_port = 4002                  # 4002 for IB Gateway Paper (7497 for TWS Paper; 4001/7496 for Live)
initial_capital = 100000.0
isolated_capital = true

[sizing]
mode = "static"                  # "static" (3.5%/short) or "perbet_house" (1/6 -> 1/3 Kelly on YTD profit)
static_pct = 0.035

[bwb]
enabled = true
initial_capital = 100000.0
isolated_capital = true
delta_mid = 0.20                 # 0.20 (20-delta Put BWB) or 0.15 (15-delta Put BWB)
w1_sd = 0.32                     # 0.32 for 20-delta, 0.28 for 15-delta
w_risk_sd = 1.30
sizing_mode = "earned_ramp"      # 7.5% base collateral -> ramps to 20.0% on earned profit
base_collat_pct = 0.075
floor_collat_pct = 0.050
max_collat_pct = 0.200
profit_share = 0.50
symbol = "SPX"                   # "SPX" (SPXW) or "XSP" (Mini-SPX, 1/10th size)
entry_minutes_after_open = 60    # 10:30 AM ET entry
client_id_offset = 1             # Connects on client_id 18 alongside Gap Short on 17
```

### Option B: Shared `$100,000` Capital Pool (Return-Stacked on the Same `$100k` Account)
Because `0DTE Put BWB` only uses margin intraday (`10:30 AM – 4:00 PM ET`, `0%` overnight) while `Gap Short` enters at the close (`3:50–4:00 PM ET`) and holds overnight, both strategies can share the **exact same `$100,000` capital pool** with the **Yearly `Jan-1` House-Money Lock (`yearly_house`)** and the **`95%` Combined IBKR Margin Guard**:

```toml
mode = "paper"                   # or "live" (with allow_live = true and tws_port = 4001 / 7496)
tws_port = 4002                  # 4002 for IB Gateway Paper (7497 for TWS Paper)
initial_capital = 100000.0
isolated_capital = false

[sizing]
mode = "perbet_house"            # or "static" during initial paper/live rollout
kelly_mult = 0.1667              # 1/6 Kelly on Jan-1 capital
profit_kelly_mult = 0.3333       # 1/3 Kelly on this year's net profit
model_path = "~/gapshort/trading_system/live/model_perbet.json"

[bwb]
enabled = true
initial_capital = 100000.0
isolated_capital = false         # Share the same $100k pool & check Gap Short's active margin at 10:30 AM
delta_mid = 0.15                 # 0.15 (15-delta, w1_sd = 0.28) or 0.20 (20-delta, w1_sd = 0.32)
w1_sd = 0.28
w_risk_sd = 1.30
sizing_mode = "yearly_house"     # Locks in max($100k, Jan-1 equity) every year
base_collat_pct = 0.075
floor_collat_pct = 0.050
max_collat_pct = 0.200
profit_share = 0.50
max_combined_margin_pct = 0.95   # Ensures Gap Short FINRA 4210 margin + BWB margin never exceeds 95%
symbol = "SPX"
```

---

## 5. Run as a Background `systemd` Service on the PC (Once)

```bash
mkdir -p ~/.config/systemd/user
cp ~/gapshort/deploy/gapshort.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now gapshort
sudo loginctl enable-linger "$USER"     # Keeps service running when logged out
systemctl --user status gapshort        # Should show: active (running)
journalctl --user -u gapshort -f        # Follow live logs from both bots (Ctrl+C to exit)
```

Whenever you edit `~/.config/gapshort/config.toml`, restart the service:

```bash
systemctl --user restart gapshort
```

---

## 6. Publish the App to Your Phone via Tailscale HTTPS (Once)

On the Ubuntu PC:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                        # Authenticate in browser
```

In the Tailscale Admin Console (`login.tailscale.com/admin`):
1. Under **DNS**, enable **MagicDNS** and **HTTPS Certificates**.
2. Under **Machines**, open the PC's `⋯` menu and select **Disable key expiry**.

Expose port `8787` privately to your own Tailscale tailnet:

```bash
sudo tailscale serve --bg 8787
tailscale serve status                   # Prints your https://<pc-name>.<tailnet>.ts.net URL
```

*(Never use `tailscale funnel` — `serve` restricts access strictly to your own authenticated Tailscale devices.)*

On your Android phone:
1. Install **Tailscale**, sign into the same account, and toggle it ON.
2. Open `https://<pc-name>.<tailnet>.ts.net` in **Chrome** and sign in.
3. Tap Chrome menu `⋮` → **Install app** (or **Add to Home screen → Install**).

---

## 7. Daily Schedule on the PC (Automatic)

| Time (New York ET) | Bot | Action |
| :--- | :--- | :--- |
| **10:30 AM ET** | **Strategy 2 (`0DTE Put BWB`)** | Reads `SPX`, `VIX`, `VIX1D` from TWS (`clientId 18`), checks `F1: VIX1D < VIX`, sizes contracts via Earned-Money / Yearly House Kelly (`7.5% -> 20%`), and submits the 4-leg `SPXW`/`XSP` `BAG` credit spread. |
| **15:45 PM ET** | **Strategy 1 (`Gap Short`)** | Scans US stocks (`clientId 17`), filters 100%+ gap/surge candidates, checks IBKR short availability & fee rate (`<= 300%/yr`), submits 3-leg OCA short brackets, and sends Day-3 `MOC` exits. |
| **16:15 PM ET** | **Both Bots** | Reconciles fills, settles the 0DTE `SPXW` spread at 4:00 PM cash close, updates both SQLite ledgers (`gapshort-{mode}.db` and `bwb-{mode}.db`), updates the **Report** tab (`Actual vs Backtest Twin vs Expected Edge`), and sends your daily summary notification. |

### Resetting the House-Money Starting Point After Deposits / Withdrawals
If you deposit or withdraw capital mid-year (or switch to `perbet_house` / `yearly_house` mid-year), run this command after 16:15 ET so both bots lock in current equity as the year's principal baseline:

```bash
~/gapshort/.venv/bin/python -m trading_system.live.main reset-year-start --config ~/.config/gapshort/config.toml
```

---

## 8. Updating the PC to a New Package Version

When copying a new `gapshort-live-YYYYMMDD.tar.gz` to your PC:

```bash
cd ~/Downloads
sha256sum -c gapshort-live-*.tar.gz.sha256
systemctl --user stop gapshort
tar -xzf gapshort-live-*.tar.gz -C ~/gapshort
~/gapshort/.venv/bin/pip install -r ~/gapshort/deploy/requirements-live.txt
systemctl --user start gapshort
systemctl --user status gapshort
```

Your `~/.config/gapshort/config.toml`, `~/.config/gapshort/secrets.json`, and SQLite trade journals (`~/.local/share/gapshort/*.db`) live outside `~/gapshort`, so updates never overwrite your state or trade history.

---

## 9. Remote TWS Login from Your Phone (Weekly Sunday Relogin)

TWS requires a weekly login (usually Sunday). Because IBKR allows only one session per username, logging into IBKR Mobile with the same username will disconnect TWS on your PC. Instead, use **RustDesk over Tailscale**:

1. **Force Xorg on Ubuntu** (Wayland blocks unattended remote desktop input):
   ```bash
   sudo sed -i 's/^#\?WaylandEnable=.*/WaylandEnable=false/' /etc/gdm3/custom.conf
   sudo reboot
   ```
2. **Install RustDesk** on the PC (`.deb` from `github.com/rustdesk/rustdesk/releases`), set a ** permanent password**, and enable **Direct IP access**.
3. **Connect from your phone:** Open the RustDesk app on Android while connected to Tailscale and connect to your PC's Tailscale IP (`tailscale ip -4`).

---

## 10. Troubleshooting

| Symptom | Fix |
| :--- | :--- |
| `check` says it cannot reach TWS | Ensure TWS is open and logged in, and *API → Settings → Enable ActiveX and Socket Clients* is ON with port `7497`. |
| Stock volumes in `check` look 100× too small | Untick *Send market data in lots for US stocks for dual-mode API clients* in TWS *API → Settings*. |
| `0DTE BWB` shows `disconnected` while `Gap Short` is connected | Verify no other process is using TWS `clientId = 18` (`client_id + client_id_offset`). |
| `0DTE BWB` cannot qualify `SPX` / `VIX1D` / `SPXW` | Verify Cboe Global Indices and OPRA US Options subscriptions are active and shared with your paper account in IBKR Client Portal. |
| Paper orders pause in TWS waiting for confirmation | Enable *API → Precautions → Bypass Order Precautions for API Orders* in TWS. |
| Service logs / errors | Run `journalctl --user -u gapshort -n 100 --no-pager` on the PC. |
