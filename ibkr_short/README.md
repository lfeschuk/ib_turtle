# Dual-Strategy IBKR Trading Bot — Complete Ubuntu PC Setup Guide
**(`Strategy 1: Small-Cap 100%+ Gap Short` + `Strategy 2: Vol-Scaled 0DTE SPX Put BWB`)**

This repository contains the complete, self-contained trading service that runs two uncorrelated (`r ≈ 0.00`) automated strategies side-by-side against **IB Gateway** (or **TWS**) on your Ubuntu PC, controlled from an installable phone web app (PWA) over Tailscale HTTPS:

1. **Strategy 1 — Small-Cap 100%+ Gap Short (`clientId = 17`):**
   - Scans at **15:45 ET** (15 min before the 16:00 ET close; 12:45 ET on half-days) for 100%+ small-cap gap/surge exhaustion (`S3a`, `S5b`, `I3b`).
   - Checks live IBKR short availability (`shortableShares`) and borrow fee rate (`<= 300%/yr`).
   - Submits 3-leg OCA short brackets (`LOC` entry + server-side `STP` loss cap + `LMT` profit target), sends Day-3 `MOC` exits, and reconciles at **16:15 ET**.
2. **Strategy 2 — Vol-Scaled 0DTE SPX Put BWB (`clientId = 18`):**
   - Checks the causal `F1: VIX1D < VIX` contango gate at **10:30 AM ET**.
   - Builds the volatility-scaled 4-leg `SPXW` (or `XSP`) Put Broken-Wing Butterfly (`+1 K_hi Put, -2 K_mid Put, +1 K_lo Put`), snapshots live IBKR/Cboe NBBO leg quotes (`Model Mid` vs `Live 10:30 Mid`), and enforces a pre-trade minimum net credit floor (`1.85%` of `W_risk` on `20Δ`, `1.50%` on `15Δ`) plus a hard `90s` timeout cancel so unfilled limits never hang open intraday.
   - Sizes contracts using the **Earned-Money / Yearly House-Money Kelly Ramp (`7.5% -> 20.0%`)**, submits the Cboe `BAG` combo credit order, reconciles 4:00 PM ET cash settlement at **16:15 ET**, and decomposes **Wrong Model Error vs Extra Slippage vs True Remaining Edge** live in the **Report** tab.

---

## One-Command Automated PC Installer (`install_pc.sh`) — Recommended

You do **not** need to run the installation steps manually. We included an all-in-one installer script (`install_pc.sh`) that does everything automatically, checks for any issues, and prints the exact next steps at the end:

1. **If you copied the `ibkr_short` folder to your Ubuntu PC:**
   ```bash
   cd /path/to/ibkr_short
   bash install_pc.sh
   ```
2. **Or if you copied `install_pc.sh` and `dist/gapshort-live-20261028.tar.gz` to `~/Downloads` on your PC:**
   ```bash
   cd ~/Downloads
   bash install_pc.sh
   ```

### What `bash install_pc.sh` Does Automatically:
- **Step 1**: Checks Python 3, installs `python3-venv` / `pip` / `curl` if missing, enables NTP clock sync, and prevents Ubuntu from sleeping/suspending during market hours.
- **Step 2**: Creates `~/gapshort` and unpacks/copies both bots (`Gap Short` + `0DTE SPX Put BWB`) into `~/gapshort`.
- **Step 3**: Creates `~/gapshort/.venv`, installs all Python dependencies (`numpy`, `pandas`, `ib_async`, `fastapi`, `uvicorn`), and runs a strategy math self-test.
- **Step 4**: Auto-detects whether **IB Gateway (`port 4002`)** or **TWS (`port 7497`)** is listening, asks whether you want **Independent (`2 × $100k`)** or **Shared (`1 × $100k` with Jan-1 lock & `95%` margin guard)** mode, and writes `~/.config/gapshort/config.toml`.
- **Step 5**: Prompts you to set your web/phone dashboard password (`~/.config/gapshort/secrets.json`).
- **Step 6**: Installs, enables, and starts the background `systemd` service (`gapshort.service`) and verifies `http://localhost:8787` is live.
- **Step 7**: Runs a live API diagnostic (`check`) against IB Gateway if open, checks Tailscale, and prints a color-coded **`[OK]` / `[WARN]` / `[FAIL]`** summary with the exact next steps required.

*(Non-interactive flags are also supported: `bash install_pc.sh --yes --port 4002` or `bash install_pc.sh --yes --port 4002 --shared-100k`.)*

---

## FAQ: What is `~/gapshort`? Do I Need to Install Anything First?

- **No — you do NOT need to install any external `gapshort` package first.**
- **`~/gapshort` is simply the folder name on your Ubuntu PC where you unpack this bot.**
  - All the bot code is packaged inside `dist/gapshort-live-20261028.tar.gz` (located at `~/work_files/ibkr_short/dist/gapshort-live-20261028.tar.gz` on your work machine).
  - When you run `mkdir -p ~/gapshort` and `tar -xzf gapshort-live-20261028.tar.gz -C ~/gapshort` on your Ubuntu PC (shown in Step 3 below), that creates the `~/gapshort` folder and puts the entire bot inside it.
  - **What if you copied the whole `ibkr_short` folder directly to your PC?** If you copied `~/work_files/ibkr_short` to your PC (e.g. to `~/ibkr_short`), it is already the exact same code — just rename or symlink it to `~/gapshort` (`mv ~/ibkr_short ~/gapshort` or `ln -s ~/ibkr_short ~/gapshort`) so the `systemd` service file (`deploy/gapshort.service`) finds `~/gapshort` automatically.

---

## Required IBKR Market Data Subscriptions (Account Management / Client Portal)

In **IBKR Client Portal** (*Settings → User Settings → Market Data Subscriptions*), verify these subscriptions are active on your main account and that **Share real-time market data with Paper Trading account** is turned **ON**:

1. **US Securities Snapshot and Futures Value Bundle** (`$10/mo`, waived at `$30/mo` commissions) — required for US equities (`Strategy 1: Gap Short`).
2. **US Equity and Options Add-On Streaming Bundle (OPRA)** (`$4.50/mo`) — required for real-time `SPXW` / `XSP` 0DTE option chains and quotes (`Strategy 2: 0DTE Put BWB`).
3. **Cboe One / Cboe Global Indices** (`~$2.50/mo`) — required for real-time `SPX`, `VIX`, and `VIX1D` index ticks at `10:30 AM ET`.

---

## Step 1. Prepare the Ubuntu PC (Run Once on the PC)

Open a terminal on your Ubuntu PC and install the standard Python virtualenv tools, keep the clock synced with NTP, and prevent the PC from sleeping when the screen locks or lid closes:

```bash
# 1. Install Python venv, pip, and curl
sudo apt update && sudo apt install -y python3-venv python3-pip curl

# 2. Keep the system clock synced with NTP (options & MOC cutoffs are exact to the second)
sudo timedatectl set-ntp true
timedatectl              # Verify it prints: "System clock synchronized: yes"

# 3. Prevent the PC from suspending when idle or when the laptop lid is closed
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' \
  | sudo tee /etc/systemd/logind.conf.d/gapshort.conf
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

Also in Ubuntu Desktop Settings:
- **Settings → Users:** Turn on **Automatic Login** so the desktop (and IB Gateway) comes back automatically after a power cut.
- **Settings → Power:** Turn off **Automatic Suspend**.

---

## Step 2. Configure IB Gateway (Recommended) or TWS on the PC (Once)

**IB Gateway is preferred over full TWS** for unattended bots: it speaks the exact same IBKR API socket protocol, supports multiple simultaneous `clientId` connections (`17` and `18`), uses ~80% less RAM/CPU, and has no chart/order-ticket GUI popups.

### Option 2A: Using IB Gateway (Recommended)
1. Launch **IB Gateway** on your PC, select **IB API**, toggle **Paper Trading**, and log in.
2. In the top menu bar of IB Gateway, open **Configure → Settings**:

   | Menu Path in IB Gateway | Setting | Required Value |
   | :--- | :--- | :--- |
   | **API → Settings** | Socket port | **`4002`** (Paper default) / **`4001`** (Live default) |
   | **API → Settings** | Read-Only API | **OFF** (unchecked) for `paper` and `live` |
   | **API → Settings** | Allow connections from localhost only | **ON** (checked) |
   | **API → Precautions** | Bypass Order Precautions for API Orders (+ Bond / Negative Yield / Price Cap) | **ON** *(check all 4 bypass boxes so IB Gateway never holds an API order waiting for a click)* |
   | **Lock and Exit** | Auto restart | **ON**, set outside `10:00–16:30 ET` (e.g., **`11:45 PM`**) |

3. Click **Apply** and **OK**.
4. **Port Note:** Because IB Gateway uses port **`4002`** (Paper) / **`4001`** (Live), make sure `tws_port = 4002` in `~/.config/gapshort/config.toml` (Step 4 below).

### Option 2B: Using Full Trader Workstation (TWS)
If you use full TWS instead of IB Gateway, open **File → Global Configuration**:

| Menu Path in TWS | Setting | Required Value |
| :--- | :--- | :--- |
| **API → Settings** | Enable ActiveX and Socket Clients | **ON** |
| **API → Settings** | Socket port | **`7497`** (Paper) / **`7496`** (Live) |
| **API → Settings** | Allow connections from localhost only | **ON** |
| **API → Settings** | Read-Only API | **OFF** for `paper` and `live` |
| **API → Settings** | Send market data in lots for US stocks for dual-mode API clients | **OFF** *(critical: if ON, stock volumes are 100× too small)* |
| **API → Precautions** | Bypass Order Precautions for API Orders | **ON** |
| **Lock and Exit** | Auto restart | **ON**, set to **`23:45`** (`11:45 PM`) |

---

## Step 3. Unpack and Install the Bot into `~/gapshort` on the PC (Once)

Copy `dist/gapshort-live-20261028.tar.gz` and `dist/gapshort-live-20261028.tar.gz.sha256` from your work machine (`~/work_files/ibkr_short/dist/`) into `~/Downloads` on your Ubuntu PC.

Then run these commands on your Ubuntu PC to create `~/gapshort`, set up its isolated Python `.venv`, create `~/.config/gapshort/config.toml`, and set your phone web-app password:

```bash
# 1. Verify the archive checksum
cd ~/Downloads
sha256sum -c gapshort-live-20261028.tar.gz.sha256    # Must print: OK

# 2. Create ~/gapshort and unpack the bot into it
mkdir -p ~/gapshort
tar -xzf gapshort-live-20261028.tar.gz -C ~/gapshort

# 3. Create the Python virtual environment inside ~/gapshort/.venv and install dependencies
cd ~/gapshort
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r deploy/requirements-live.txt

# 4. Copy the example config to ~/.config/gapshort/config.toml
mkdir -p ~/.config/gapshort
cp deploy/config.example.toml ~/.config/gapshort/config.toml

# 5. Set the password (12+ characters) for the phone/browser web dashboard
.venv/bin/python -m trading_system.live.main set-password --config ~/.config/gapshort/config.toml
```

*(Note: If instead of copying the `.tar.gz` to `~/Downloads`, you copied the entire `ibkr_short` folder directly to your PC, just run `cp -r /path/to/ibkr_short ~/gapshort` and start from step `# 3` above (`cd ~/gapshort`).)*

---

## Step 4. Configure `config.toml` (Port + Independent vs. Shared `$100k` Capital)

Open `~/.config/gapshort/config.toml` in a text editor (`nano ~/.config/gapshort/config.toml`) and choose **Option A** or **Option B** below.

> **Important for IB Gateway users:** Make sure `tws_port = 4002` (for IB Gateway Paper) or `tws_port = 4001` (for IB Gateway Live). If using full TWS, use `7497` (Paper) / `7496` (Live).

### Option A: Two Independent `$100,000` Paper Ledgers (`$200,000` Total — Default for Paper Monitoring)
Each strategy tracks and compounds its own isolated `$100,000` ledger (`gapshort-paper.db` and `bwb-paper.db`) so you can monitor both strategies completely independently side-by-side:

```toml
mode = "paper"
tws_host = "127.0.0.1"
tws_port = 4002                  # 4002 for IB Gateway Paper (7497 for TWS Paper)
client_id = 17
allow_live = false

initial_capital = 100000.0
isolated_capital = true

http_host = "127.0.0.1"
http_port = 8787
data_dir = "~/.local/share/gapshort"
secrets_path = "~/.config/gapshort/secrets.json"

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
sizing_mode = "earned_ramp"      # "earned_ramp" or "yearly_house" (7.5% -> 20.0% on earned profit)
base_collat_pct = 0.075
floor_collat_pct = 0.050
max_collat_pct = 0.200
profit_share = 0.50
symbol = "SPX"                   # "SPX" (SPXW) or "XSP" (Mini-SPX, 1/10th size)
entry_minutes_after_open = 60    # 10:30 AM ET entry
client_id_offset = 1             # Connects on client_id 18 alongside Gap Short on 17
```

### Option B: Shared `$100,000` Capital Pool (`1 × $100k` Return-Stacked with `yearly_house` & `95%` Margin Guard)
Because `0DTE Put BWB` only uses margin intraday (`10:30 AM – 4:00 PM ET`, `0%` overnight) while `Gap Short` enters at the close (`3:50–4:00 PM ET`) and holds overnight, both strategies can share the **exact same `$100,000` capital pool** with the **Yearly `Jan-1` House-Money Lock (`yearly_house`)** and the **`95%` Combined IBKR Margin Guard**:

```toml
mode = "paper"                   # or "live" (with allow_live = true and tws_port = 4001)
tws_host = "127.0.0.1"
tws_port = 4002                  # 4002 for IB Gateway Paper (4001 for IB Gateway Live)
client_id = 17
allow_live = false

initial_capital = 100000.0
isolated_capital = false         # Share the same $100k account equity

http_host = "127.0.0.1"
http_port = 8787
data_dir = "~/.local/share/gapshort"
secrets_path = "~/.config/gapshort/secrets.json"

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
entry_minutes_after_open = 60
client_id_offset = 1
```

---

## Step 5. Test the IB Gateway Connection & Start the Background Service

1. **With IB Gateway open and logged into Paper Trading (port `4002`), test the connection:**

   ```bash
   ~/gapshort/.venv/bin/python -m trading_system.live.main check --config ~/.config/gapshort/config.toml
   ```

   This verifies:
   - `Gap Short` connects on `clientId = 17`, reads account NetLiquidation, and fetches US stock bars.
   - `0DTE SPX Put BWB` connects on `clientId = 18`, qualifies `SPX`, `VIX`, `VIX1D`, and builds a live `SPXW` BWB candidate.

2. **Test a manual foreground run in your browser:**

   ```bash
   ~/gapshort/.venv/bin/python -m trading_system.live.main run --config ~/.config/gapshort/config.toml
   ```

   Open `http://localhost:8787` in your PC browser, log in with the password you set in Step 3, and verify you see the top strategy selector (**`Both`** | **`Gap Short`** | **`0DTE BWB`**). Press `Ctrl+C` in the terminal to stop the manual run.

3. **Enable the `systemd` background service so it runs 24/7 automatically:**

   ```bash
   mkdir -p ~/.config/systemd/user
   cp ~/gapshort/deploy/gapshort.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now gapshort
   sudo loginctl enable-linger "$USER"     # Keeps service running even when logged out
   systemctl --user status gapshort        # Should show: active (running)
   ```

   To watch live logs from both strategies at any time:
   ```bash
   journalctl --user -u gapshort -f        # Press Ctrl+C to stop watching logs
   ```

   Whenever you edit `~/.config/gapshort/config.toml`, restart the service:
   ```bash
   systemctl --user restart gapshort
   ```

---

## Step 6. Publish the Web App Privately to Your Phone via Tailscale HTTPS (Once)

On the Ubuntu PC:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                        # Authenticate in browser
```

In the Tailscale Admin Console (`login.tailscale.com/admin`):
1. Under **DNS**, enable **MagicDNS** and **HTTPS Certificates**.
2. Under **Machines**, open your PC's `⋯` menu and select **Disable key expiry**.

Expose port `8787` privately to your own Tailscale tailnet:

```bash
sudo tailscale serve --bg 8787
tailscale serve status                   # Prints your https://<pc-name>.<tailnet>.ts.net URL
```

*(Never use `tailscale funnel` — `serve` restricts access strictly to your own authenticated Tailscale devices.)*

On your phone:
1. Install **Tailscale**, sign into the same account, and toggle it ON.
2. Open `https://<pc-name>.<tailnet>.ts.net` in **Chrome** (or Safari on iOS) and sign in.
3. Tap Chrome menu `⋮` → **Install app** (or **Add to Home screen → Install**).

---

## Step 7. Daily Automatic Schedule & CLI Commands

| Time (New York ET) | Bot | Action |
| :--- | :--- | :--- |
| **10:30 AM ET** | **Strategy 2 (`0DTE Put BWB`)** | Reads `SPX`, `VIX`, `VIX1D` from IB Gateway (`clientId 18`), checks `F1: VIX1D < VIX`, sizes contracts via Earned-Money / Yearly House Kelly (`7.5% -> 20%`), checks the `95%` combined margin guard, and submits the 4-leg `SPXW`/`XSP` `BAG` credit spread. |
| **15:45 PM ET** | **Strategy 1 (`Gap Short`)** | Scans US stocks (`clientId 17`), filters 100%+ gap/surge candidates, checks IBKR short availability & fee rate (`<= 300%/yr`), submits 3-leg OCA short brackets, and sends Day-3 `MOC` exits. |
| **16:15 PM ET** | **Both Bots** | Reconciles fills, settles the 0DTE `SPXW` spread at 4:00 PM cash close, updates both SQLite ledgers (`gapshort-{mode}.db` and `bwb-{mode}.db`), updates the **Report** tab (`Actual vs Backtest Twin vs Expected Edge`), and sends your daily summary notification. |

### Handy Manual CLI Commands
```bash
# Check live status & JSON snapshot of both bots
~/gapshort/.venv/bin/python -m trading_system.live.main status --config ~/.config/gapshort/config.toml

# Trigger an on-demand 0DTE BWB scan right now
~/gapshort/.venv/bin/python -m trading_system.live.main bwb-scan-now --config ~/.config/gapshort/config.toml

# Trigger an on-demand Gap Short scan right now
~/gapshort/.venv/bin/python -m trading_system.live.main scan-now --config ~/.config/gapshort/config.toml

# Reset the Jan-1 House-Money anchor to current equity (e.g., after a capital deposit/withdrawal)
~/gapshort/.venv/bin/python -m trading_system.live.main reset-year-start --config ~/.config/gapshort/config.toml
```

---

## Step 8. Updating the PC to a New Package Version

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

Your `~/.config/gapshort/config.toml`, `~/.config/gapshort/secrets.json`, and SQLite trade journals (`~/.local/share/gapshort/*.db`) live outside `~/gapshort`, so updates never overwrite your settings or trade history.

---

## Step 9. Remote IB Gateway Login from Your Phone (Weekly Sunday Relogin)

IB Gateway requires a weekly 2FA login (usually Sunday). Because IBKR allows only one session per username, logging into IBKR Mobile with the same username will disconnect IB Gateway on your PC. Instead, use **RustDesk over Tailscale**:

1. **Force Xorg on Ubuntu** (Wayland blocks unattended remote desktop input):
   ```bash
   sudo sed -i 's/^#\?WaylandEnable=.*/WaylandEnable=false/' /etc/gdm3/custom.conf
   sudo reboot
   ```
2. **Install RustDesk** on the PC (`.deb` from `github.com/rustdesk/rustdesk/releases`), set a **permanent password**, and enable **Direct IP access**.
3. **Connect from your phone:** Open the RustDesk app on your phone while connected to Tailscale and connect to your PC's Tailscale IP (`tailscale ip -4`).

---

## Step 10. Troubleshooting

| Symptom | Fix |
| :--- | :--- |
| `check` says it cannot reach IB Gateway / TWS | Ensure IB Gateway is open and logged in, and that `tws_port = 4002` in `~/.config/gapshort/config.toml` matches *Configure → Settings → API → Settings → Socket port* in IB Gateway (or `7497` if using full TWS). |
| Stock volumes in `check` look 100× too small (TWS only) | Untick *Send market data in lots for US stocks for dual-mode API clients* in TWS *API → Settings*. |
| `0DTE BWB` shows `disconnected` while `Gap Short` is connected | Verify no other process is using `clientId = 18` (`client_id + client_id_offset`). |
| `0DTE BWB` cannot qualify `SPX` / `VIX1D` / `SPXW` | Verify Cboe Global Indices and OPRA US Options subscriptions are active and shared with your paper account in IBKR Client Portal. |
| Paper orders pause in IB Gateway waiting for confirmation | Enable all 4 bypass checkboxes under *Configure → Settings → API → Precautions* in IB Gateway. |
| View service logs / errors | Run `journalctl --user -u gapshort -n 100 --no-pager` on the PC. |
