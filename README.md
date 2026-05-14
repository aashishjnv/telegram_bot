# 🤖 Telegram Referral & Gmail Bot

A production-ready Telegram bot with referral system, Gmail account requests, withdrawals, admin panel, and force-join — built with **aiogram 3** and **MongoDB (Motor)**.

---

## 📁 Project Structure

```
telegram_bot/
├── main.py                  # Entry point
├── requirements.txt
├── Procfile                 # Railway/Heroku process file
├── railway.json             # Railway config
├── .env.example             # Environment variables template
│
├── config/
│   ├── __init__.py
│   └── settings.py          # ENV loader & settings dataclass
│
├── database/
│   ├── __init__.py
│   └── mongo.py             # Async MongoDB wrapper (Motor)
│
├── handlers/
│   ├── __init__.py
│   ├── start.py             # /start, force-join, main menu
│   ├── profile.py           # Profile, referral, rewards, help
│   ├── gmail.py             # Gmail request FSM flow
│   ├── withdraw.py          # Withdrawal FSM flow
│   └── admin.py             # Full admin panel
│
├── keyboards/
│   └── __init__.py          # All InlineKeyboard builders
│
├── middlewares/
│   └── __init__.py          # AntiSpam + BanCheck middleware
│
├── states/
│   └── __init__.py          # FSM state groups
│
└── utils/
    └── __init__.py          # Membership check + message formatters
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `FORCE_CHANNEL` | Channel username (without @) or numeric ID |
| `ADMIN_IDS` | Comma-separated Telegram user IDs |
| `BOT_USERNAME` | Your bot's username (without @) |
| `DATABASE_URL` | MongoDB connection string |

---

## 🗄️ MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `users` | All users, balances, points, referral data |
| `referrals` | Successful referral pairs |
| `gmail_requests` | Gmail account creation requests |
| `withdrawals` | Withdrawal requests |
| `admin_logs` | Audit trail of admin actions |
| `bans` | Banned user records |

---

## 🚀 Local Development

```bash
# 1. Clone / unzip project
cd telegram_bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill env file
cp .env.example .env
# Edit .env with your values

# 5. Run
python main.py
```

> Requires Python 3.11+ and a running MongoDB instance (local or Atlas).

---

## 🚂 Railway Deployment

### Step 1 — Create Railway project
1. Go to [railway.app](https://railway.app) and log in.
2. Click **New Project → Deploy from GitHub repo** (or use the Railway CLI).

### Step 2 — Add MongoDB
1. In your Railway project, click **+ New** → **Database** → **MongoDB**.
2. Railway auto-sets `MONGO_URL`. Copy it and set as `DATABASE_URL` in variables.

### Step 3 — Set Environment Variables
In the Railway dashboard → **Variables**, add:
```
BOT_TOKEN=your_token
FORCE_CHANNEL=your_channel
ADMIN_IDS=your_id
BOT_USERNAME=YourBotUsername
DATABASE_URL=<from MongoDB plugin>
```

### Step 4 — Deploy
Push to GitHub or click **Deploy**. Railway uses `Procfile` to start `python main.py`.

### Step 5 — Monitor
View logs in Railway dashboard → **Deployments → View Logs**.

---

## 📋 Admin Commands Reference

| Command | Usage | Description |
|---------|-------|-------------|
| `/admin` | `/admin` | Open admin panel |
| `/adminhelp` | `/adminhelp` | Show all admin commands |
| `/stats` | `/stats` | Bot statistics |
| `/broadcast` | `/broadcast` | Broadcast to all users |
| `/userinfo` | `/userinfo <user_id>` | View user details |
| `/addpoints` | `/addpoints <uid> <pts>` | Add points to user |
| `/removepoints` | `/removepoints <uid> <pts>` | Remove points |
| `/addbalance` | `/addbalance <uid> inr 100` | Add balance |
| `/removebalance` | `/removebalance <uid> usd 5` | Remove balance |
| `/ban` | `/ban <uid> <reason>` | Ban user |
| `/unban` | `/unban <uid>` | Unban user |
| `/requests` | `/requests` | View pending Gmail requests |

---

## 🔄 User Flow

```
/start
  └── Force-join check
        ├── Not joined → Show join button
        └── Joined →
              ├── New user registered (referral credited if valid)
              └── Main Menu
                    ├── 👤 Profile → View stats + history
                    ├── 📧 Create Gmail → 4-step wizard (costs 4 pts)
                    ├── 💰 Withdraw → UPI / PayPal / Crypto
                    ├── 🎁 Rewards → View balances
                    ├── 👥 Referral → Share link
                    └── ℹ️ Help → Guide
```

---

## 🔐 Security Features

- **Anti-spam middleware** — rate-limits to 1 action per 2 seconds
- **Ban middleware** — blocked users can't access any feature
- **Self-referral prevention** — enforced at DB level
- **Duplicate referral prevention** — unique index on `referred_id`
- **Points gate** — Gmail requests require exactly 4 points (atomic check + deduct)
- **Input validation** — all user inputs sanitized
- **Admin-only commands** — checked against `ADMIN_IDS` env list
- **Password auto-delete** — password messages deleted from chat immediately

---

## 📦 Dependencies

```
aiogram==3.13.1       # Telegram Bot framework
motor==3.6.0          # Async MongoDB driver
pymongo==4.10.1       # MongoDB utilities
python-dotenv==1.0.1  # .env file loader
aiohttp==3.10.10      # HTTP client (used by aiogram)
certifi==2024.8.30    # SSL certificates
```
