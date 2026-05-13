import aiohttp, logging
from datetime import datetime
from config import CRYPTO_PAY_TOKEN, CRYPTO_PAY_API_URL, LOGS_FILE

logger = logging.getLogger(__name__)

async def create_invoice(amount, description="Пополнение баланса"):
    headers={"Crypto-Pay-API-Token":CRYPTO_PAY_TOKEN}
    params={"currency_type":"fiat","fiat":"USD","amount":round(amount,2),"description":description,"allow_anonymous":True,"expires_in":3600}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{CRYPTO_PAY_API_URL}/createInvoice",headers=headers,params=params) as r:
                data=await r.json()
                if data.get("ok"): return data["result"]
    except Exception as e: logger.error(f"CryptoPay error: {e}")
    return None

async def check_invoice(invoice_id):
    headers={"Crypto-Pay-API-Token":CRYPTO_PAY_TOKEN}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{CRYPTO_PAY_API_URL}/getInvoices",headers=headers,params={"invoice_ids":invoice_id}) as r:
                data=await r.json()
                if data.get("ok") and data["result"]["items"]: return data["result"]["items"][0]
    except Exception as e: logger.error(f"CryptoPay check error: {e}")
    return None

def log_event(event, user_id=None, details=""):
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"); line=f"[{ts}] {event}"
    if user_id: line+=f" | user:{user_id}"
    if details: line+=f" | {details}"
    try:
        with open(LOGS_FILE,"a",encoding="utf-8") as f: f.write(line+"\n")
    except Exception as e: logger.error(f"Log error: {e}")

def fmt_date(dt_str):
    try: return datetime.fromisoformat(dt_str).strftime("%d.%m.%Y %H:%M")
    except: return dt_str

def parse_numbered_list(text):
    items=[]
    for line in text.strip().split("\n"):
        line=line.strip()
        if not line: continue
        for sep in [". ",") "," - ","- "]:
            parts=line.split(sep,1)
            if len(parts)==2 and parts[0].strip().isdigit(): items.append(parts[1].strip()); break
        else: items.append(line)
    return items
