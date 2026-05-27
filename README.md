# AmitMarketBot 🤖

Automated market data email bot that sends scheduled reports about Indian and global markets.

## Features

📧 **Scheduled Emails:**
- **9:30 AM** — Most Active Stocks, Top 5 Down Indian ETFs, Top 5 Down Global ETFs
- **3:00 PM** — Most Active Stocks, Top 5 Down Indian ETFs, Top 5 Down Global ETFs

🚨 **Real-Time Alerts:**
- Any ETF drops 2%+ → Email immediately
- Any Stock drops 5%+ → Email immediately
- Checks every 5 minutes

## Tech Stack

- **Python** — Core application
- **Requests** — Fetch market data from Yahoo Finance
- **Google Generative AI** — Future AI features (optional)
- **APScheduler** — Schedule email jobs
- **Gmail SMTP** — Send emails

## Setup

### 1. Clone & Install Dependencies

```bash
git clone <your-repo-url>
cd AmitBot
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_api_key
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_1=email1@example.com
RECIPIENT_2=email2@example.com
RECIPIENT_3=email3@example.com
```

### 3. Get Gmail App Password

1. Enable 2FA on your Gmail account
2. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Generate an app-specific password for "Mail"
4. Use this password in `.env` as `SENDER_PASSWORD`

### 4. Run Locally

```bash
python market_bot.py
```

## Deploy on Railway

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-github-repo>
git push -u origin main
```

### 2. Connect Railway to GitHub

1. Go to [Railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repo
4. Railway will auto-detect Python project

### 3. Add Environment Variables

In Railway dashboard:
1. Go to Variables tab
2. Add all variables from `.env`:
   - `GEMINI_API_KEY`
   - `SENDER_EMAIL`
   - `SENDER_PASSWORD`
   - `RECIPIENT_1`, `RECIPIENT_2`, `RECIPIENT_3`

### 4. Deploy

- Push code to GitHub → Railway auto-deploys
- Monitor logs in Railway dashboard

## Files Included

- `market_bot.py` — Main application
- `requirements.txt` — Python dependencies
- `Procfile` — Railway/Heroku process definition
- `runtime.txt` — Python version
- `.env.example` — Environment variables template
- `.gitignore` — Git ignore rules
- `README.md` — This file

## Monitoring

Check logs on Railway dashboard:
```
2026-05-27 09:30:00 - 📧 Sending 9:30 AM market open email...
2026-05-27 09:30:15 - ✅ Got 8 NSE stocks
2026-05-27 09:30:25 - ✅ Email sent: 📈 Market Open — 27 May 2026
```

## Troubleshooting

**Email not sending?**
- Check SENDER_EMAIL and SENDER_PASSWORD in Railway variables
- Verify app password from Gmail
- Check Railway logs

**No market data?**
- Yahoo Finance API might be rate-limited
- Check internet connectivity on Railway
- Wait a few minutes and retry

**Alerts not firing?**
- Check that alerts trigger conditions are met (2%+ for ETF, 5%+ for stocks)
- Each alert fires only once per day per symbol

## Cost

- **Railway** — Free tier (~$5 credits/month)
- **Gmail SMTP** — Free (500 emails/day)
- **Yahoo Finance** — Free unlimited
- **Gemini API** — Free tier (1500 requests/day)

**Total: ~₹0/month** ✅

## License

MIT

## Support

For issues, create a GitHub issue or contact the author.

---

🚀 **Happy tracking!**
