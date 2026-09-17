# RQFC Runner (VM side)

Everything that runs on the Oracle VM. It connects **market data → student
strategies → the existing Railway backend**. Nothing here changes the backend,
the `app/` dashboard, or manual use of the `rqfc` package.

```
runner/
  docker-compose.yml     bus + hub (this phase)
  .env.example           copy to .env
  hub/                   marketdata-hub: Alpaca IEX websocket -> NATS
  sandbox/               per-pod strategy container image
  examples/              sample strategies
```

## Phase status

| Phase | Component | State |
|---|---|---|
| 1 | NATS bus, marketdata-hub, `Strategy` API, sandbox image, in-sandbox runtime | **this drop** |
| 2 | `rqfc deploy` server side, `strategies` router + migration, supervisor | next |
| 3 | fills-listener (`on_fill`, `/internal/fills`), portfolio-sync | next |
| 4 | sandbox hardening: egress allowlist, cgroups, timeouts, read-only rootfs | next |

## Message subjects

| Subject | Payload |
|---|---|
| `md.trade.<SYM>` | `{symbol, price, size, timestamp}` |
| `md.quote.<SYM>` | `{symbol, bid_price, bid_size, ask_price, ask_size, timestamp}` |
| `md.bar.<SYM>` | `{symbol, open, high, low, close, volume, timestamp}` |
| `exec.fill.<POD_ID>` | `{order_id, symbol, side, qty, price, filled_qty, status, timestamp}` (phase 3) |
| `hub.control` | `{action: "subscribe"|"unsubscribe", symbols: [...]}` (honored in phase 2) |

---

## One-time: provision the Oracle VM

1. Sign up at cloud.oracle.com. **Home region: US East (Ashburn)** — permanent,
   and closest to Alpaca's infrastructure.
2. **Billing → Upgrade to Pay As You Go**, add a card. You are not charged while
   you stay within Always Free limits; this removes idle-reclamation and usually
   clears ARM capacity errors.
3. **Compute → Instances → Create instance**
   - Shape: `VM.Standard.A1.Flex`, **2 OCPU / 12 GB** (Always Free allows up to 4/24)
   - Image: **Ubuntu 22.04 (aarch64)**
   - Boot volume: 60 GB
   - Add your SSH public key
   - "Out of host capacity" is common on free ARM — retry / change availability domain.
4. **Networking:** the default VCN is created for you. In the subnet's Security
   List add **one ingress rule: TCP 22 from your IP only.** Do not open any other
   inbound ports — the VM only makes outbound connections. Leave egress at default.

## One-time: prepare the box

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"      # then log out and back in
```

Oracle's Ubuntu image ships a restrictive `iptables`. Keep the rules that allow
established/related traffic and port 22; outbound is already permitted.

## Run the stack

```bash
git clone https://github.com/jamesyazici/fund.git
cd fund/runner
cp .env.example .env
#   set HUB_ALPACA_KEY / HUB_ALPACA_SECRET  (free Alpaca data account = IEX)
#   set HUB_SYMBOLS to every symbol your strategies need
#   set RAILWAY_BACKEND_URL and generate INTERNAL_SHARED_SECRET
docker compose up -d --build
docker compose logs -f hub
```

`restart: unless-stopped` brings services back after a reboot. Optionally add a
`@reboot` cron running `docker compose -f /home/ubuntu/fund/runner/docker-compose.yml up -d`.

---

## Local test (no VM needed)

From the repo root:

```bash
pip install -e ".[runtime]"

# 1. bus
docker run --rm -p 4222:4222 nats:2.10-alpine

# 2. hub  (in another shell)
HUB_ALPACA_KEY=... HUB_ALPACA_SECRET=... \
HUB_SYMBOLS=AAPL,MSFT,NVDA,GOOGL,META,AMZN,TSLA,JPM,V,MA,SPY \
NATS_URL=nats://localhost:4222 \
python runner/hub/hub.py

# 3. a strategy  (in another shell) — needs a real pod UUID + an rqfc_ API key
RQFC_BACKEND_URL=http://localhost:8000 \
RQFC_STRATEGY_TOKEN=rqfc_your_key \
RQFC_POD_ID=00000000-0000-0000-0000-000000000000 \
RQFC_STRATEGY_FILE=runner/examples/momentum_strategy.py \
NATS_URL=nats://localhost:4222 \
python -m rqfc._runtime
```

During market hours you'll see `md.bar.*` events reach the strategy and, once
warmed up, orders posted to the backend `/orders` endpoint. `on_fill` stays
silent until phase 3.
