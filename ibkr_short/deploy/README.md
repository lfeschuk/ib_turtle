# Gap Short: setup on your Ubuntu laptop

The service runs next to TWS on the laptop. It places the shorts at the close, sends the day-3 exits, checks every position after the close and pushes alerts. The phone app is an installable web app that the laptop serves. Nothing comes from an app store.

```
Phone (app) ──Tailscale HTTPS──> laptop: tailscale serve ──> Gap Short service on 127.0.0.1:8787 ──> TWS on 127.0.0.1:7497
```

## What you need

| Item | Notes |
| :--- | :--- |
| IBKR **margin** account | Shorting needs margin. The **paper account** (free) comes with it. |
| Real-time US stock data | NYSE, NYSE American and Nasdaq, shared with the paper account (step 2). Delayed data would make the 15:45 scan wrong. |
| IBKR Mobile with IB Key | For logins to the live account. |
| The laptop | Ubuntu 22.04 or newer, plugged in, online, awake at 15:45–16:20 New York time on trading days. |
| Android phone with Chrome | The app installs from Chrome. |
| Free Tailscale account | Sign in with Google, Microsoft or GitHub. Use the same account on laptop and phone. |
| Optional | ntfy app (alerts), free healthchecks.io account (alerts you if the laptop goes quiet). |
| This package | `gapshort-live-YYYYMMDD.tar.gz` (and its `.sha256`). |

## 1. Prepare the laptop (once)

```bash
sudo apt update
sudo apt install -y python3-venv curl
python3 --version        # 3.10 or newer

# keep running with the lid closed, and never suspend
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' \
  | sudo tee /etc/systemd/logind.conf.d/gapshort.conf
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

timedatectl              # "System clock synchronized: yes"
```

Also:
- In Settings → Users, turn on **Automatic Login**, so the desktop (and TWS) comes back after a power cut.
- In Settings → Power, turn off **Automatic Suspend**.
- Then reboot once.
- Optional: in the HP BIOS (F10 at boot), set "After Power Loss" to **Power On**.

## 2. TWS (once)

1. **Download.** Get **TWS Stable for Linux** from interactivebrokers.com (Trading → Trader Workstation → Download). Then install it:

   ```bash
   cd ~/Downloads
   chmod +x tws-stable-standalone-linux-x64.sh
   ./tws-stable-standalone-linux-x64.sh
   ```

2. **Log in.** Start **Trader Workstation** from the app menu, choose **Paper Trading** in the login window, and log in.
3. **Settings** (File → Global Configuration):

   | Where | Setting | Value |
   | :--- | :--- | :--- |
   | API → Settings | Enable ActiveX and Socket Clients | on |
   | API → Settings | Socket port | 7497 |
   | API → Settings | Allow connections from localhost only | on |
   | API → Settings | Read-Only API | **on** for shadow, **off** for paper and live |
   | API → Settings | Send market data in lots for US stocks for dual-mode API clients | **off** (otherwise volumes come in 100× too small) |
   | API → Precautions | Bypass Order Precautions for API Orders | on (otherwise TWS can hold the bot's orders for a click) |
   | Lock and Exit | Auto restart | on, at a time outside 15:30–16:30 New York time (e.g. 23:45) |

4. **Market data.** In Client Portal, subscribe to real-time US stock data: the "US Securities Snapshot and Futures Value Bundle" plus the "US Equity and Options Add-On Streaming Bundle". Then go to Settings → Paper Trading Account and turn on sharing real-time market data with the paper account. This can take a day to apply.

## 3. Install the Gap Short service (once)

```bash
cd ~/Downloads
sha256sum -c gapshort-live-*.tar.gz.sha256          # must say OK
mkdir -p ~/gapshort
tar -xzf gapshort-live-*.tar.gz -C ~/gapshort
cd ~/gapshort
python3 -m venv .venv
.venv/bin/pip install -r deploy/requirements-live.txt
mkdir -p ~/.config/gapshort
cp deploy/config.example.toml ~/.config/gapshort/config.toml
.venv/bin/python -m trading_system.live.main set-password --config ~/.config/gapshort/config.toml
```

The app password (12+ characters) is stored only as a scrypt hash in `~/.config/gapshort/secrets.json`, which only you can read. The config starts in `mode = "shadow"` with static 3.5% sizing.

With TWS running and logged in, check the connection:

```bash
.venv/bin/python -m trading_system.live.main check --config ~/.config/gapshort/config.toml
```

It should print the account (masked), three days of AAPL bars with volumes in the tens of millions, the scanner's symbols, and a borrow line. If the volumes are about 100× too small, turn off the "lots" setting in step 2.

Try one run by hand:

```bash
.venv/bin/python -m trading_system.live.main run --config ~/.config/gapshort/config.toml
```

Open http://localhost:8787 in the laptop's browser and sign in. Stop the run with Ctrl+C.

## 4. Run it as a service (once)

```bash
mkdir -p ~/.config/systemd/user
cp ~/gapshort/deploy/gapshort.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now gapshort
sudo loginctl enable-linger "$USER"     # keeps it running when you are logged out
systemctl --user status gapshort        # should say active (running)
journalctl --user -u gapshort -f        # live log (Ctrl+C to leave)
```

## 5. Put the app on your phone (once)

On the laptop:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                        # opens a sign-in link
```

In the Tailscale admin console (login.tailscale.com/admin):
- Under **DNS**, turn on MagicDNS and **HTTPS Certificates**.
- Under **Machines**, open the laptop's ⋯ menu and choose **Disable key expiry**. Otherwise the phone loses access after six months.

Then publish the app to your own devices:

```bash
sudo tailscale serve --bg 8787
tailscale serve status                   # shows https://<laptop>.<tailnet>.ts.net
```

Do not use `tailscale funnel`: it would publish the app to the whole internet.

On the phone:
1. Install **Tailscale** from the Play Store, sign in with the same account, and connect.
2. In **Chrome**, open `https://<laptop>.<tailnet>.ts.net` and sign in with the app password.
3. Chrome menu ⋮ → **Install app** (or Add to Home screen → Install). Gap Short now has its own icon.

## 6. Phone alerts (optional, recommended)

- **ntfy:** install the ntfy app, subscribe to a long random topic name, and set `ntfy_url = "https://ntfy.sh/<topic>"` in `~/.config/gapshort/config.toml`.
- **Laptop-down alert:** create a check on healthchecks.io (period 10 minutes, grace 10 minutes). Add its ping URL to `~/.config/gapshort/secrets.json` so the file looks like `{"password_hash": "...", "healthchecks_url": "https://hc-ping.com/..."}`, then run `chmod 600 ~/.config/gapshort/secrets.json`.
- **Telegram (instead of ntfy):** add `"telegram_token"` to `secrets.json` and set `telegram_chat_id` in the config.

Then run `systemctl --user restart gapshort`.

## 7. Stages

| Stage | Config | What happens |
| :--- | :--- | :--- |
| Shadow (2 weeks) | `mode = "shadow"`, TWS Read-Only API on | Nothing is sent. The bot keeps a virtual book of the shorts it *would* hold (same slots, cooldown and exits as the backtest), and the Report tab tracks it. |
| Paper (2–3 months) | `mode = "paper"`, Read-Only API off | Real orders in the paper account. The service refuses to run unless the account id starts with `DU`. |
| Live | `mode = "live"`, `allow_live = true`, `tws_port = 7496`, TWS logged into live | Start at a small size. |

After changing the config: `systemctl --user restart gapshort`.

**Sizing at full size.** Keep `[sizing] mode = "static"` (3.5% per short) through shadow, paper and the first live months. Then switch to house-money Kelly:

```toml
[sizing]
mode = "perbet_house"
kelly_mult = 0.1667          # the money the year started with: 1/6 of each short's Kelly size
profit_kelly_mult = 0.3333   # this year's profit (net of the tax owed): 1/3 of the Kelly size
```

Bets grow as the year's profit grows and fall back to 1/6 Kelly, never lower, as profit is given back. The 10% cap per short, the 1%-of-volume cap and the margin check still apply. The Now tab shows "Profit this year" and "Kelly × 1/6, profit × 1/3".

The year's starting point is the first equity the bot records each January. Reset it when you switch modes in the middle of a year, and after any deposit or withdrawal (the evening after, once the bot has recorded the new equity), so that only trading profit counts:

```bash
~/gapshort/.venv/bin/python -m trading_system.live.main reset-year-start --config ~/.config/gapshort/config.toml
```

## 8. Daily and weekly routine

- **Daily:** nothing to do. After 16:15 New York time, glance at the daily push or the Report tab.
- **Weekly:** TWS asks for a fresh login, usually on Sunday. Log in again at the laptop. Until you do, the bot cannot trade, and you get a "TWS disconnected" alert.
- **After a reboot or power cut:** log into TWS again. The service starts on its own and reconnects.
- Stops and targets sit on IBKR's servers, so they work even if the laptop is off. Day-3 exits are sent by the laptop at 15:45 New York time, so keep it running.

### Logging into TWS from your phone

IBKR Mobile can't do it. TWS on the laptop is a separate login, and IBKR allows one session per username, so logging into IBKR Mobile with the bot's username logs TWS out. Use a remote desktop over Tailscale instead:

1. **Switch to Xorg** (Ubuntu 22.04/24.04). Remote control of the desktop doesn't work under Wayland:

   ```bash
   sudo sed -i 's/^#\?WaylandEnable=.*/WaylandEnable=false/' /etc/gdm3/custom.conf
   sudo reboot
   ```

2. **Install RustDesk.** Download the x86_64 `.deb` from github.com/rustdesk/rustdesk/releases, then run `sudo apt install ./rustdesk-*-x86_64.deb`.
3. **Set up RustDesk on the laptop.** In Settings → Security, set a strong **permanent password** and turn on **Enable direct IP access**. Optionally, turn on IP whitelisting with only your phone's Tailscale IP.
4. **Connect from the phone.** Install RustDesk from the Play Store. With Tailscale on, connect to the laptop's Tailscale IP (`tailscale ip -4` on the laptop) and enter the permanent password. You see the TWS window and log in as usual.

When you go live, create a second IBKR username for your phone (Client Portal → Settings → Users & Access Rights), so checking your account on IBKR Mobile never logs the bot out. Approving IB Key notifications on the phone is fine either way.

## 9. What the buttons do

- **Pause new shorts:** no new entries. Open shorts keep their stop, target and day-3 exit. Signals are still checked and tracked (not traded), so the edge check keeps learning while paused.
- **Close (one short):** cancels its stop and target, then buys it back. During market hours that is a market order; otherwise it buys at the next open.
- **Close all:** the same for every short, then pauses the bot.

Closing asks for the password again.

## 10. The Report tab (end of day)

After each close (16:15 ET) the bot compares three things for the shorts it holds:

- **Actual:** what the account made (real fills, commissions, estimated borrow).
- **Backtest:** what the backtest would have made on the same shorts: entry at the official close, the backtest's slippage and borrow, and its stop, target and day-3 exit on real daily bars.
- **Expected:** the average edge the model expects for those shorts (it rises with the setup score).

Actual minus backtest is what execution costs you (entry, exit, borrow and commissions are shown separately). Backtest minus expected is luck, or a fading edge if it keeps drifting down.

- The **edge check** ranks every closed trade against the backtest's outcomes. It raises an alarm when recent trades look more like no edge than like the backtest (about 20:1 odds), and clears by itself once results recover.
- The **execution check** turns red when fills cost more than 1.5% per trade beyond the backtest's assumptions.

Both send a phone alert when they turn red. The daily summary includes the day's actual, backtest and expected numbers.

## 11. Updating to a new version

```bash
systemctl --user stop gapshort
tar -xzf ~/Downloads/gapshort-live-NEW.tar.gz -C ~/gapshort
~/gapshort/.venv/bin/pip install -r ~/gapshort/deploy/requirements-live.txt
systemctl --user start gapshort
```

The config, password and trade journal live outside `~/gapshort`, so updates keep them.

## 12. Security notes

- The service listens on 127.0.0.1 only. Tailscale decides which devices can reach it.
- **Login:**
  - The password is checked against a scrypt hash, with at most 5 wrong tries per 15 minutes.
  - The session is an HttpOnly, Secure, SameSite=Strict cookie (14 days, 3 days idle).
  - Every change needs a CSRF token, and closing positions asks for the password again.
- The app runs no third-party scripts and uses a strict Content-Security-Policy. API responses are never cached.

## 13. Troubleshooting

| Symptom | Check |
| :--- | :--- |
| `check` says it cannot reach TWS | TWS is running and logged in; API enabled on port 7497 (step 2) |
| "paper mode, but TWS is logged into a live account" | Log TWS into Paper Trading, or change `mode` |
| Phone: "Cannot reach the laptop" | Tailscale is on for both devices; `tailscale serve status`; `systemctl --user status gapshort` |
| Chrome offers no "Install app" | Use the `https://…ts.net` address, not an IP address |
| Red dot / "Offline" in the app | TWS logged out (weekly login, reboot) or its API is off |
| No signals ever | `check` shows realistic volumes and scanner symbols; market data is shared with the paper account |
| Paper orders never appear | Read-Only API off; Bypass Order Precautions on; `mode = "paper"` |
| "Check positions" alert | A short is missing its stop or target, or IBKR holds a position the bot didn't open; fix it in TWS |
| Service not running | `journalctl --user -u gapshort -n 50` shows the error |
