import logging
import json
import os
import smtplib
import requests
import hashlib
import time
try:
    import google.generativeai as genai
except:
    import google.genai as genai
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler

# ============================================================
# CONFIG
# ============================================================
GEMINI_API_KEY  = "AIzaSyDNnGXQedB5JMMEifsuwzT52a39HibF8iY"
SENDER_EMAIL    = "srv19246@gmail.com"
SENDER_PASSWORD = "epsy okyw jyqr ztcs"
RECIPIENTS      = ["ranveersingh8823@gmail.com", "amitindia0001@yahoo.com", "hello@bxgo.ai"]
GNEWS_API_KEY   = "4d141e6ed9c1c94559d66c74380ba60f"

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# ============================================================
# ETF WATCHLIST
# ============================================================
INDIAN_ETFS = {
    "Nifty BeES":       "NIFTYBEES.NS",
    "Bank BeES":        "BANKBEES.NS",
    "Gold BeES":        "GOLDBEES.NS",
    "IT BeES":          "ITBEES.NS",
    "PSU Bank BeES":    "PSUBNKBEES.NS",
    "Midcap 150":       "MID150BEES.NS",
    "Pharma BeES":      "PHARMABEES.NS",
    "CPSE ETF":         "CPSEETF.NS",
    "Bharat Bond 2030": "EBBETF0430.NS",
    "Nifty Next 50":    "JUNIORBEES.NS",
}

INTL_ETFS = {
    "SPDR S&P 500 (SPY)":     "SPY",
    "Nasdaq 100 (QQQ)":       "QQQ",
    "Emerging Markets (EEM)": "EEM",
    "Vanguard EM (VWO)":      "VWO",
    "ARK Innovation (ARKK)":  "ARKK",
    "Gold ETF (GLD)":         "GLD",
    "20yr Treasury (TLT)":    "TLT",
    "Russell 2000 (IWM)":     "IWM",
    "Dow Jones (DIA)":        "DIA",
    "Financials (XLF)":       "XLF",
}

ALERTED_TODAY = {}

# ============================================================
# HELPERS
# ============================================================
def send_email(subject, html):
    try:
        msg            = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = ", ".join(RECIPIENTS)
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())
        logger.info(f"✅ Email sent: {subject[:60]}")
        return True
    except Exception as e:
        logger.error(f"❌ Email error: {e}")
        return False

def email_wrap(title, subtitle, color, body):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
body{{font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:20px}}
.c{{max-width:660px;margin:auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1)}}
.h{{background:linear-gradient(135deg,{color},{color}cc);color:white;padding:24px;text-align:center}}
.h h1{{margin:0;font-size:20px}}.h p{{margin:5px 0 0;opacity:.85;font-size:13px}}
.s{{padding:18px}}.st{{font-size:13px;font-weight:700;margin-bottom:10px;padding:8px 12px;border-radius:6px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#f8f9fa;padding:8px;text-align:left;font-size:11px;color:#666;border-bottom:2px solid #eee;text-transform:uppercase}}
td{{padding:9px 8px;border-bottom:0.5px solid #f0f0f0}}
.ft{{background:#f8f9fa;padding:14px;text-align:center;font-size:11px;color:#888;border-top:1px solid #eee}}
</style></head><body><div class="c">
<div class="h"><h1>{title}</h1><p>{subtitle}</p></div>
{body}
<div class="ft"><p>🤖 <b>AmitMarketBot</b> · {datetime.now().strftime('%d %b %Y %I:%M %p')} IST</p>
<p style="color:#aaa;margin-top:3px">Data: NSE via Gemini AI · Yahoo Finance · Coinbase</p></div>
</div></body></html>"""

# ============================================================
# GEMINI — FETCH NSE DATA
# ============================================================
def get_nse_active_stocks():
    """Use Gemini to get most active stocks from NSE"""
    try:
        prompt = """
        Go to https://www.nseindia.com/market-data/most-active-securities-market-wide
        and extract the top 10 most active stocks right now.
        
        Return ONLY a JSON array like this:
        [
          {"rank": 1, "symbol": "RELIANCE", "name": "Reliance Industries", "price": 2850.50, "change": 45.20, "pct": 1.61, "volume": "12.5M"},
          ...
        ]
        
        Use today's live data. Return only valid JSON, no other text.
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
        logger.info(f"✅ Gemini got {len(data)} active stocks")
        return data
    except Exception as e:
        logger.error(f"Gemini NSE error: {e}")
        return []

def get_nse_market_summary():
    """Use Gemini to get Sensex, Nifty, market summary"""
    try:
        prompt = """
        Get the current live market data from NSE India website (nseindia.com):
        - Nifty 50 current value and % change
        - Sensex current value and % change  
        - Market breadth (advances vs declines)
        - Top gainer and top loser stock today
        
        Return ONLY JSON like:
        {
          "nifty": {"value": 22500.50, "change": 120.30, "pct": 0.54},
          "sensex": {"value": 74200.00, "change": 350.50, "pct": 0.47},
          "advances": 1200,
          "declines": 800,
          "top_gainer": {"symbol": "TATAMOTORS", "pct": 3.2},
          "top_loser": {"symbol": "WIPRO", "pct": -2.1}
        }
        
        Return only valid JSON, no other text.
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
        logger.info("✅ Gemini got market summary")
        return data
    except Exception as e:
        logger.error(f"Gemini market summary error: {e}")
        return {}

# ============================================================
# YAHOO FINANCE — ETF DATA
# ============================================================
def fetch_etf_data(symbols_dict):
    results = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for name, symbol in symbols_dict.items():
        try:
            url  = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            res  = requests.get(url, headers=headers, timeout=10).json()
            chart_result = res.get("chart", {}).get("result")
            if not chart_result or not isinstance(chart_result, list) or len(chart_result) == 0:
                continue
            meta = chart_result[0].get("meta")
            if not meta:
                continue
            price    = meta.get("regularMarketPrice", 0)
            prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
            if not price or not prev:
                continue
            change   = round(price - prev, 2)
            pct      = round((change / prev) * 100, 2) if prev else 0
            currency = "₹" if ".NS" in symbol else "$"
            results.append({"name": name, "symbol": symbol, "price": price,
                            "change": change, "pct": pct, "currency": currency})
        except Exception as e:
            logger.error(f"ETF error {name}: {e}")
    results.sort(key=lambda x: x["pct"])
    return results

def get_gold_silver():
    try:
        r1   = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=XAU", timeout=10).json()
        r2   = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=XAG", timeout=10).json()
        # Handle both old and new API structure
        rates1 = r1.get("data", r1).get("rates", {})
        rates2 = r2.get("data", r2).get("rates", {})
        inr1   = float(rates1.get("INR", 0))
        inr2   = float(rates2.get("INR", 0))
        gold   = round(inr1 / 3.215, 2) if inr1 else 0
        silv   = round(inr2 * 32.15, 2) if inr2 else 0
        return gold, silv
    except Exception as e:
        logger.error(f"Gold/Silver error: {e}")
        return 0, 0

# ============================================================
# BUILD EMAIL SECTIONS
# ============================================================
def build_active_stocks_html(stocks):
    if not stocks:
        return "<p style='color:#888;padding:10px'>Data unavailable right now</p>"
    rows = ""
    for i, s in enumerate(stocks[:10]):
        if not s or not isinstance(s, dict):
            continue
        chg   = float(s.get('change') or 0)
        pct   = float(s.get('pct') or 0)
        price = float(s.get('price') or 0)
        rank  = s.get('rank', '')
        symbol = s.get('symbol', '')
        name = s.get('name', '')
        volume = s.get('volume', '')
        
        if not symbol:
            continue
            
        color = "#27ae60" if chg >= 0 else "#e74c3c"
        arrow = "▲" if chg >= 0 else "▼"
        bg    = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        rows += f"""<tr style="background:{bg}">
            <td style="padding:8px;color:#666">{rank}</td>
            <td style="padding:8px"><b>{symbol}</b><br>
            <span style="font-size:11px;color:#888">{name}</span></td>
            <td style="padding:8px;font-weight:600">₹{price:,.2f}</td>
            <td style="padding:8px;color:{color};font-weight:700">{arrow} {abs(pct)}%</td>
            <td style="padding:8px;color:#888;font-size:12px">{volume}</td>
        </tr>"""
    return f"""<table><thead><tr>
        <th>#</th><th>Stock</th><th>Price</th><th>Change</th><th>Volume</th>
    </tr></thead><tbody>{rows}</tbody></table>"""

def build_etf_html(etfs, flag="🇮🇳"):
    rows = ""
    for i, e in enumerate(etfs[:5], 1):
        color = "#e74c3c" if e['pct'] < 0 else "#27ae60"
        arrow = "▼" if e['pct'] < 0 else "▲"
        bg    = "#fff5f5" if i % 2 == 0 else "#ffffff"
        rows += f"""<tr style="background:{bg}">
            <td style="padding:8px">{i}</td>
            <td style="padding:8px"><b>{e['name']}</b><br>
            <span style="font-size:11px;color:#888">{e['symbol']}</span></td>
            <td style="padding:8px;font-weight:600">{e['currency']}{e['price']:,.2f}</td>
            <td style="padding:8px;color:{color};font-weight:700">{arrow} {abs(e['pct'])}%</td>
        </tr>"""
    return f"""<table><thead><tr>
        <th>#</th><th>{flag} ETF</th><th>Price</th><th>Change</th>
    </tr></thead><tbody>{rows}</tbody></table>"""

def build_market_summary_html(summary, gold, silver):
    if not summary:
        return ""
    nifty   = summary.get("nifty", {})
    sensex  = summary.get("sensex", {})
    nc      = "#27ae60" if nifty.get('change', 0) >= 0 else "#e74c3c"
    sc      = "#27ae60" if sensex.get('change', 0) >= 0 else "#e74c3c"
    na      = "▲" if nifty.get('change', 0) >= 0 else "▼"
    sa      = "▲" if sensex.get('change', 0) >= 0 else "▼"
    return f"""<table><tbody>
        <tr><td style="padding:9px"><b>Nifty 50</b></td>
            <td style="padding:9px;font-weight:600">{nifty.get('value',0):,.2f}</td>
            <td style="padding:9px;color:{nc};font-weight:700">{na} {abs(nifty.get('pct',0))}%</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:9px"><b>Sensex</b></td>
            <td style="padding:9px;font-weight:600">{sensex.get('value',0):,.2f}</td>
            <td style="padding:9px;color:{sc};font-weight:700">{sa} {abs(sensex.get('pct',0))}%</td></tr>
        <tr><td style="padding:9px"><b>Gold</b></td>
            <td style="padding:9px;font-weight:600">₹{gold:,}/10g</td>
            <td style="padding:9px;color:#888">Live</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:9px"><b>Silver</b></td>
            <td style="padding:9px;font-weight:600">₹{silver:,}/kg</td>
            <td style="padding:9px;color:#888">Live</td></tr>
        <tr><td style="padding:9px"><b>Advances</b></td>
            <td style="padding:9px;font-weight:600;color:#27ae60">{summary.get('advances',0)}</td>
            <td style="padding:9px;color:#e74c3c;font-weight:600">Declines: {summary.get('declines',0)}</td></tr>
    </tbody></table>"""

# ============================================================
# EMAIL 1 — 9:30 AM MARKET OPEN
# ============================================================
def send_market_open_email():
    logger.info("📧 Sending 9:30 AM market open email...")

    # Fetch all data
    stocks        = get_nse_active_stocks()
    summary       = get_nse_market_summary()
    indian_etfs   = fetch_etf_data(INDIAN_ETFS)
    intl_etfs     = fetch_etf_data(INTL_ETFS)
    gold, silver  = get_gold_silver()

    body = f"""
    <div class="s">
        <div class="st" style="background:#e8f8f0;color:#1e8449">💹 MARKET SUMMARY — OPEN</div>
        {build_market_summary_html(summary, gold, silver)}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#e8f4fd;color:#1a5276">🔥 TOP 10 MOST ACTIVE STOCKS — NSE</div>
        {build_active_stocks_html(stocks)}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#fff0f0;color:#c0392b">📉 TOP 5 MOST DOWN INDIAN ETFs</div>
        {build_etf_html(indian_etfs, "🇮🇳")}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#f0f4ff;color:#2c3e8c">🌍 TOP 5 MOST DOWN GLOBAL ETFs</div>
        {build_etf_html(intl_etfs, "🌍")}
    </div>"""

    html = email_wrap(
        "📈 Market Open — 9:30 AM",
        f"📅 {datetime.now().strftime('%d %b %Y')} · NSE Live Data · Most Active & Most Down",
        "#1e8449",
        body
    )
    send_email(f"📈 Market Open Report — {datetime.now().strftime('%d %b %Y')}", html)

# ============================================================
# EMAIL 2 — 3:00 PM MARKET CLOSE
# ============================================================
def send_market_close_email():
    logger.info("📧 Sending 3:00 PM market close email...")

    stocks       = get_nse_active_stocks()
    summary      = get_nse_market_summary()
    indian_etfs  = fetch_etf_data(INDIAN_ETFS)
    intl_etfs    = fetch_etf_data(INTL_ETFS)
    gold, silver = get_gold_silver()

    body = f"""
    <div class="s">
        <div class="st" style="background:#fff0f0;color:#c0392b">📊 MARKET SUMMARY — CLOSE</div>
        {build_market_summary_html(summary, gold, silver)}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#e8f4fd;color:#1a5276">🔥 TOP 10 MOST ACTIVE STOCKS — NSE</div>
        {build_active_stocks_html(stocks)}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#fff0f0;color:#c0392b">📉 TOP 5 MOST DOWN INDIAN ETFs TODAY</div>
        {build_etf_html(indian_etfs, "🇮🇳")}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#f0f4ff;color:#2c3e8c">🌍 TOP 5 MOST DOWN GLOBAL ETFs TODAY</div>
        {build_etf_html(intl_etfs, "🌍")}
    </div>"""

    html = email_wrap(
        "🔔 Market Close — 3:00 PM",
        f"📅 {datetime.now().strftime('%d %b %Y')} · End of Day Summary",
        "#c0392b",
        body
    )
    send_email(f"🔔 Market Close Report — {datetime.now().strftime('%d %b %Y')}", html)

# ============================================================
# EMAIL 3 — INSTANT ALERTS
# ============================================================
def check_instant_alerts():
    global ALERTED_TODAY
    today_key = datetime.now().strftime("%Y-%m-%d")
    alerts    = []
    headers   = {"User-Agent": "Mozilla/5.0"}

    all_etfs = {**INDIAN_ETFS, **INTL_ETFS}
    for name, symbol in all_etfs.items():
        try:
            url  = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            res  = requests.get(url, headers=headers, timeout=10).json()
            result = res.get("chart", {}).get("result")
            if not result or not isinstance(result, list) or len(result) == 0:
                continue
            meta = result[0].get("meta", {})
            if not meta:
                continue
            price    = float(meta.get("regularMarketPrice") or 0)
            prev     = float(meta.get("previousClose") or meta.get("chartPreviousClose") or price)
            pct      = round(((price - prev) / prev) * 100, 2) if prev and price else 0
            currency = "₹" if ".NS" in symbol else "$"
            flag     = "🇮🇳" if ".NS" in symbol else "🌍"
            key      = f"{symbol}_{today_key}"

            # Alert if drops 2%+ (not alerted today)
            if pct <= -2.0 and not ALERTED_TODAY.get(key):
                alerts.append({
                    "name": name, "symbol": symbol,
                    "price": price, "pct": pct,
                    "change": round(price - prev, 2),
                    "currency": currency, "flag": flag
                })
                ALERTED_TODAY[key] = True

        except Exception as e:
            logger.error(f"Alert check error {name}: {e}")

    if alerts:
        send_instant_alert_email(alerts)

def send_instant_alert_email(alerts):
    date = datetime.now().strftime("%d %b %Y %I:%M %p")

    rows = ""
    for i, e in enumerate(alerts, 1):
        bg = "#fff5f5" if i % 2 == 0 else "#ffffff"
        rows += f"""<tr style="background:{bg}">
            <td style="padding:10px;font-size:16px">{e['flag']}</td>
            <td style="padding:10px"><b>{e['name']}</b><br>
            <span style="font-size:11px;color:#888">{e['symbol']}</span></td>
            <td style="padding:10px;font-weight:600">{e['currency']}{e['price']:,.2f}</td>
            <td style="padding:10px;color:#e74c3c;font-weight:700;font-size:15px">▼ {abs(e['pct'])}%</td>
            <td style="padding:10px;color:#e74c3c">{e['currency']}{abs(e['change']):,.2f}</td>
        </tr>"""

    body = f"""
    <div class="s">
        <p style="color:#c0392b;font-weight:600;background:#fff5f5;padding:12px;border-radius:8px;margin-bottom:14px">
        ⚠️ The following ETFs have dropped 2% or more — immediate attention required</p>
        <table><thead><tr>
            <th></th><th>ETF Name</th><th>Price</th><th>Drop %</th><th>Drop Amount</th>
        </tr></thead><tbody>{rows}</tbody></table>
    </div>"""

    html = email_wrap(
        "🚨 ETF Drop Alert — 2% or More!",
        f"⏰ {date} IST · Real-time alert",
        "#c0392b", body
    )
    send_email(f"🚨 ETF Drop Alert (-2%+) — {date}", html)

# ============================================================
# MAIN
# ============================================================
def main():
    logger.info("✅ AmitMarketBot starting...")

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(send_market_open_email,  "cron",     hour=9,  minute=30)
    scheduler.add_job(send_market_close_email, "cron",     hour=15, minute=0)
    scheduler.add_job(check_instant_alerts,    "interval", minutes=5)
    scheduler.start()

    logger.info("✅ AmitMarketBot running!")
    logger.info("   📈 9:30 AM — Market open email")
    logger.info("   🔔 3:00 PM — Market close email")
    logger.info("   🚨 Every 5 mins — ETF 2% drop alert")

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
