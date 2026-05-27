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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# CONFIG
# ============================================================
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
SENDER_EMAIL    = os.getenv("SENDER_EMAIL", "srv19246@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "epsy okyw jyqr ztcs")
RECIPIENTS      = [
    os.getenv("RECIPIENT_1", "ranveersingh8823@gmail.com"),
    os.getenv("RECIPIENT_2", "amitindia0001@yahoo.com"),
    os.getenv("RECIPIENT_3", "hello@bxgo.ai")
]
GNEWS_API_KEY   = os.getenv("GNEWS_API_KEY", "")

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
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
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
# YAHOO FINANCE — FETCH NSE DATA
# ============================================================
def get_nse_active_stocks():
    """Fetch most active NSE stocks by volume"""
    try:
        # Top NSE stocks by volume
        stocks_symbols = [
            ("RELIANCE", "Reliance Industries"),
            ("TCS", "Tata Consultancy Services"),
            ("HDFCBANK", "HDFC Bank"),
            ("INFY", "Infosys"),
            ("WIPRO", "Wipro"),
            ("HEROMOTOCORP", "Hero MotoCorp"),
            ("BAJAJFINSV", "Bajaj Finserv"),
            ("AXISBANK", "Axis Bank"),
            ("BHARATIARTL", "Bharati Airtel"),
            ("SBIN", "State Bank of India"),
        ]
        
        results = []
        headers = {"User-Agent": "Mozilla/5.0"}
        
        for symbol, name in stocks_symbols:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1d&range=1d"
                res = requests.get(url, headers=headers, timeout=10).json()
                meta = res["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice", 0)
                prev = meta.get("previousClose") or meta.get("chartPreviousClose", price)
                change = round(price - prev, 2)
                pct = round((change / prev) * 100, 2) if prev else 0
                volume = meta.get("regularMarketVolume", 0)
                
                # Format volume
                if volume >= 1000000:
                    vol_str = f"{volume/1000000:.1f}M"
                elif volume >= 1000:
                    vol_str = f"{volume/1000:.1f}K"
                else:
                    vol_str = str(volume)
                
                results.append({
                    "rank": len(results) + 1,
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                    "change": change,
                    "pct": pct,
                    "volume": vol_str
                })
            except Exception as e:
                logger.error(f"Stock {symbol} error: {e}")
                continue
        
        logger.info(f"✅ Got {len(results)} NSE stocks")
        return results
    except Exception as e:
        logger.error(f"NSE stocks error: {e}")
        return []

def get_nse_market_summary():
    """Fetch Sensex, Nifty, and market summary from Yahoo Finance"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # Fetch Nifty
        nifty_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1d"
        nifty_res = requests.get(nifty_url, headers=headers, timeout=10).json()
        nifty_meta = nifty_res["chart"]["result"][0]["meta"]
        nifty_value = nifty_meta.get("regularMarketPrice", 0)
        nifty_prev = nifty_meta.get("previousClose") or nifty_meta.get("chartPreviousClose", nifty_value)
        nifty_change = round(nifty_value - nifty_prev, 2)
        nifty_pct = round((nifty_change / nifty_prev) * 100, 2) if nifty_prev else 0
        
        # Fetch Sensex
        sensex_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EBSESN?interval=1d&range=1d"
        sensex_res = requests.get(sensex_url, headers=headers, timeout=10).json()
        sensex_meta = sensex_res["chart"]["result"][0]["meta"]
        sensex_value = sensex_meta.get("regularMarketPrice", 0)
        sensex_prev = sensex_meta.get("previousClose") or sensex_meta.get("chartPreviousClose", sensex_value)
        sensex_change = round(sensex_value - sensex_prev, 2)
        sensex_pct = round((sensex_change / sensex_prev) * 100, 2) if sensex_prev else 0
        
        summary = {
            "nifty": {
                "value": nifty_value,
                "change": nifty_change,
                "pct": nifty_pct
            },
            "sensex": {
                "value": sensex_value,
                "change": sensex_change,
                "pct": sensex_pct
            },
            "advances": 1200,  # Placeholder (Yahoo Finance doesn't provide market breadth)
            "declines": 800,   # Placeholder
            "top_gainer": {"symbol": "N/A", "pct": 0},
            "top_loser": {"symbol": "N/A", "pct": 0}
        }
        
        logger.info("✅ Got market summary from Yahoo Finance")
        return summary
    except Exception as e:
        logger.error(f"Market summary error: {e}")
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
            meta = res["chart"]["result"][0]["meta"]
            price    = meta.get("regularMarketPrice", 0)
            prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
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
    for s in stocks[:10]:
        chg   = s.get('change', 0) or 0
        pct   = s.get('pct', 0) or 0
        color = "#27ae60" if chg >= 0 else "#e74c3c"
        arrow = "▲" if chg >= 0 else "▼"
        bg    = "#f9f9f9" if stocks.index(s) % 2 == 0 else "#ffffff"
        rows += f"""<tr style="background:{bg}">
            <td style="padding:8px;color:#666">{s.get('rank','')}</td>
            <td style="padding:8px"><b>{s.get('symbol','')}</b><br>
            <span style="font-size:11px;color:#888">{s.get('name','')}</span></td>
            <td style="padding:8px;font-weight:600">₹{s.get('price',0):,.2f}</td>
            <td style="padding:8px;color:{color};font-weight:700">{arrow} {abs(pct)}%</td>
            <td style="padding:8px;color:#888;font-size:12px">{s.get('volume','')}</td>
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
    indian_etfs   = fetch_etf_data(INDIAN_ETFS)
    intl_etfs     = fetch_etf_data(INTL_ETFS)

    body = f"""
    <div class="s">
        <div class="st" style="background:#e8f4fd;color:#1a5276">🔥 MOST ACTIVE STOCKS — NSE</div>
        {build_active_stocks_html(stocks)}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#fff0f0;color:#c0392b">📉 MOST DOWN INDIAN ETFs</div>
        {build_etf_html(indian_etfs, "🇮🇳")}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#f0f4ff;color:#2c3e8c">🌍 MOST DOWN GLOBAL ETFs</div>
        {build_etf_html(intl_etfs, "🌍")}
    </div>"""

    html = email_wrap(
        "📈 Market Open — 9:30 AM",
        f"📅 {datetime.now().strftime('%d %b %Y')} · NSE Market Data",
        "#1e8449",
        body
    )
    send_email(f"📈 Market Open — {datetime.now().strftime('%d %b %Y')}", html)

# ============================================================
# EMAIL 2 — 3:00 PM MARKET CLOSE
# ============================================================
def send_market_close_email():
    logger.info("📧 Sending 3:00 PM market close email...")

    stocks       = get_nse_active_stocks()
    indian_etfs  = fetch_etf_data(INDIAN_ETFS)
    intl_etfs    = fetch_etf_data(INTL_ETFS)

    body = f"""
    <div class="s">
        <div class="st" style="background:#e8f4fd;color:#1a5276">🔥 MOST ACTIVE STOCKS — NSE</div>
        {build_active_stocks_html(stocks)}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#fff0f0;color:#c0392b">📉 MOST DOWN INDIAN ETFs</div>
        {build_etf_html(indian_etfs, "🇮🇳")}
    </div>
    <div class="s" style="padding-top:0">
        <div class="st" style="background:#f0f4ff;color:#2c3e8c">🌍 MOST DOWN GLOBAL ETFs</div>
        {build_etf_html(intl_etfs, "🌍")}
    </div>"""

    html = email_wrap(
        "🔔 Market Close — 3:00 PM",
        f"📅 {datetime.now().strftime('%d %b %Y')} · End of Day Summary",
        "#c0392b",
        body
    )
    send_email(f"🔔 Market Close — {datetime.now().strftime('%d %b %Y')}", html)

# ============================================================
# EMAIL 3 — INSTANT ALERTS (ETF 2%+ & STOCKS 5%+)
# ============================================================
def check_instant_alerts():
    global ALERTED_TODAY
    today_key = datetime.now().strftime("%Y-%m-%d")
    etf_alerts = []
    stock_alerts = []
    headers = {"User-Agent": "Mozilla/5.0"}

    # Check ETF drops (2%+)
    all_etfs = {**INDIAN_ETFS, **INTL_ETFS}
    for name, symbol in all_etfs.items():
        try:
            url  = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            res  = requests.get(url, headers=headers, timeout=10).json()
            meta = res["chart"]["result"][0]["meta"]
            price    = meta.get("regularMarketPrice", 0)
            prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
            pct      = round(((price - prev) / prev) * 100, 2) if prev else 0
            currency = "₹" if ".NS" in symbol else "$"
            flag     = "🇮🇳" if ".NS" in symbol else "🌍"
            key      = f"etf_{symbol}_{today_key}"

            # Alert if drops 2%+ (not alerted today)
            if pct <= -2.0 and not ALERTED_TODAY.get(key):
                etf_alerts.append({
                    "name": name, "symbol": symbol,
                    "price": price, "pct": pct,
                    "change": round(price - prev, 2),
                    "currency": currency, "flag": flag
                })
                ALERTED_TODAY[key] = True
        except Exception as e:
            logger.error(f"ETF alert check error {name}: {e}")

    # Check Stock drops (5%+)
    stocks_symbols = [
        ("RELIANCE", "Reliance Industries"),
        ("TCS", "Tata Consultancy Services"),
        ("HDFCBANK", "HDFC Bank"),
        ("INFY", "Infosys"),
        ("WIPRO", "Wipro"),
        ("HEROMOTOCORP", "Hero MotoCorp"),
        ("BAJAJFINSV", "Bajaj Finserv"),
        ("AXISBANK", "Axis Bank"),
        ("BHARATIARTL", "Bharati Airtel"),
        ("SBIN", "State Bank of India"),
    ]
    
    for symbol, name in stocks_symbols:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1d&range=1d"
            res = requests.get(url, headers=headers, timeout=10).json()
            meta = res["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev = meta.get("previousClose") or meta.get("chartPreviousClose", price)
            pct = round(((price - prev) / prev) * 100, 2) if prev else 0
            key = f"stock_{symbol}_{today_key}"

            # Alert if drops 5%+ (not alerted today)
            if pct <= -5.0 and not ALERTED_TODAY.get(key):
                stock_alerts.append({
                    "symbol": symbol, "name": name,
                    "price": price, "pct": pct,
                    "change": round(price - prev, 2)
                })
                ALERTED_TODAY[key] = True
        except Exception as e:
            logger.error(f"Stock alert check error {symbol}: {e}")

    if etf_alerts or stock_alerts:
        send_instant_alert_email(etf_alerts, stock_alerts)

def send_instant_alert_email(etf_alerts, stock_alerts):
    date = datetime.now().strftime("%d %b %Y %I:%M %p")

    # ETF Alert Rows
    etf_rows = ""
    for i, e in enumerate(etf_alerts, 1):
        bg = "#fff5f5" if i % 2 == 0 else "#ffffff"
        etf_rows += f"""<tr style="background:{bg}">
            <td style="padding:10px;font-size:16px">{e['flag']}</td>
            <td style="padding:10px"><b>{e['name']}</b><br>
            <span style="font-size:11px;color:#888">{e['symbol']}</span></td>
            <td style="padding:10px;font-weight:600">{e['currency']}{e['price']:,.2f}</td>
            <td style="padding:10px;color:#e74c3c;font-weight:700;font-size:15px">▼ {abs(e['pct'])}%</td>
            <td style="padding:10px;color:#e74c3c">{e['currency']}{abs(e['change']):,.2f}</td>
        </tr>"""

    # Stock Alert Rows
    stock_rows = ""
    for i, s in enumerate(stock_alerts, 1):
        bg = "#fff5f5" if i % 2 == 0 else "#ffffff"
        stock_rows += f"""<tr style="background:{bg}">
            <td style="padding:10px">🇮🇳</td>
            <td style="padding:10px"><b>{s['name']}</b><br>
            <span style="font-size:11px;color:#888">{s['symbol']}</span></td>
            <td style="padding:10px;font-weight:600">₹{s['price']:,.2f}</td>
            <td style="padding:10px;color:#e74c3c;font-weight:700;font-size:15px">▼ {abs(s['pct'])}%</td>
            <td style="padding:10px;color:#e74c3c">₹{abs(s['change']):,.2f}</td>
        </tr>"""

    body = ""
    if etf_alerts:
        body += f"""
        <div class="s">
            <p style="color:#c0392b;font-weight:600;background:#fff5f5;padding:12px;border-radius:8px;margin-bottom:14px">
            🚨 ETFs dropped 2% or more</p>
            <table><thead><tr>
                <th></th><th>ETF Name</th><th>Price</th><th>Drop %</th><th>Drop Amount</th>
            </tr></thead><tbody>{etf_rows}</tbody></table>
        </div>"""

    if stock_alerts:
        body += f"""
        <div class="s">
            <p style="color:#c0392b;font-weight:600;background:#fff5f5;padding:12px;border-radius:8px;margin-bottom:14px">
            🚨 Stocks dropped 5% or more</p>
            <table><thead><tr>
                <th></th><th>Stock Name</th><th>Price</th><th>Drop %</th><th>Drop Amount</th>
            </tr></thead><tbody>{stock_rows}</tbody></table>
        </div>"""

    html = email_wrap(
        "🚨 ALERT — ETF/Stock Drop",
        f"⏰ {date} IST · Real-time monitoring",
        "#c0392b", body
    )
    
    subject = "🚨 ALERT"
    if etf_alerts:
        subject += f" — ETF Down 2%+ ({len(etf_alerts)})"
    if stock_alerts:
        subject += f" — Stock Down 5%+ ({len(stock_alerts)})"
    
    send_email(subject, html)

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
