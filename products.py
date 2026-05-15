import json, os
from config import PRODUCTS_FILE

DEFAULT_PRODUCTS = {
    "banks":      {"name":"Б@нки ~ К0шельки","description":"✅ Товар выдаётся в формате: номер, пароль, ключ TOTP\n✅ Гарантия на вход — 6 часов\n✅ М0ментальная выдача после оплаты\n✅ Верификацию выполняете самостоятельно по мануалу","items":{}},
    "crypto":     {"name":"Кр1пт0Б1ржи ~ TG С€рвисы","description":"Верификация аккаунта.\nПроцедура выполняется путём авторизации и последующего верифа на платформе.","items":{}},
    "manuals":    {"name":"М@нyалы","description":"Подробные инструкции по работе с платформами.","items":{}},
    "bookmakers": {"name":"Бyкм€k€рk1","description":"Верификация аккаунта на букмекерской платформе.","items":{}},
}
CATEGORY_KEYS = list(DEFAULT_PRODUCTS.keys())
CATEGORY_DISPLAY = {k: v["name"] for k, v in DEFAULT_PRODUCTS.items()}

# Типы товаров
ITEM_TYPE_TEXT   = "text"          # обычный текстовый товар (банки, мануалы)
ITEM_TYPE_CREDS  = "creds"         # логин:пароль, просим отключить 2FA
ITEM_TYPE_PHONE  = "phone"         # верификация по номеру (логин-флоу)

ITEM_TYPE_LABELS = {
    ITEM_TYPE_TEXT:  "📦 Текстовый товар",
    ITEM_TYPE_CREDS: "🔑 Логин:пароль (откл. 2FA)",
    ITEM_TYPE_PHONE: "📱 Верификация по номеру",
}

def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        save_products(DEFAULT_PRODUCTS); return DEFAULT_PRODUCTS
    with open(PRODUCTS_FILE,"r",encoding="utf-8") as f: data=json.load(f)
    for k,v in DEFAULT_PRODUCTS.items():
        if k not in data: data[k]=v
    return data

def save_products(data):
    with open(PRODUCTS_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def get_all_items_with_stock(cat_key):
    data=load_products(); items=data.get(cat_key,{}).get("items",{})
    return {name:{
        "description": d.get("description","Описание отсутствует."),
        "manual":      d.get("manual",""),
        "price":       d.get("price",0),
        "stock":       len(d.get("stock",[])),
        "item_type":   d.get("item_type", ITEM_TYPE_TEXT),
    } for name,d in items.items()}

def get_items_in_category(cat_key):
    return load_products().get(cat_key,{}).get("items",{})

def get_item_type(cat_key, item_name):
    items = get_items_in_category(cat_key)
    return items.get(item_name, {}).get("item_type", ITEM_TYPE_TEXT)

def pop_stock_item(cat_key, item_name):
    data=load_products(); stock=data[cat_key]["items"].get(item_name,{}).get("stock",[])
    if not stock: return None
    item=stock.pop(0); save_products(data); return item

def add_stock_items(cat_key, item_name, new_items, item_type=ITEM_TYPE_TEXT):
    data=load_products(); items=data[cat_key]["items"]
    if item_name not in items:
        items[item_name]={"description":"Описание — заглушка.","manual":"","price":0,"stock":[],"item_type":item_type}
    else:
        # Обновляем тип если передан
        items[item_name]["item_type"] = item_type
    items[item_name]["stock"].extend(new_items); save_products(data)

def add_verification_item(cat_key, item_name, item_type):
    """Добавляет товар-верификацию без склада (склад не нужен — данные вводит сам покупатель)"""
    data=load_products(); items=data[cat_key]["items"]
    if item_name not in items:
        items[item_name]={"description":"Описание — заглушка.","manual":"","price":0,"stock":[],"item_type":item_type}
    else:
        items[item_name]["item_type"] = item_type
    save_products(data)

def delete_stock_item(cat_key, item_name, index):
    data=load_products(); stock=data[cat_key]["items"].get(item_name,{}).get("stock",[])
    if index<0 or index>=len(stock): return False
    stock.pop(index); save_products(data); return True

def clear_category_stock(cat_key):
    data=load_products()
    for name in data[cat_key]["items"]: data[cat_key]["items"][name]["stock"]=[]
    save_products(data)

def get_stock_summary():
    data=load_products()
    return {k:{"name":v["name"],"items":{
        n: {"count": len(d.get("stock",[])), "type": d.get("item_type", ITEM_TYPE_TEXT)}
        for n,d in v.get("items",{}).items()
    }} for k,v in data.items()}

def export_stock_txt():
    data=load_products(); lines=[]
    for cat_key,cat_val in data.items():
        lines.append(f"=== {cat_val['name']} ===")
        for name,d in cat_val.get("items",{}).items():
            t = d.get("item_type", ITEM_TYPE_TEXT)
            lines.append(f"  [{name}] — {len(d.get('stock',[]))} шт. | ${d.get('price',0)} | {ITEM_TYPE_LABELS.get(t,t)}")
        lines.append("")
    return "\n".join(lines)

def set_item_description(cat_key,item_name,desc):
    data=load_products()
    if item_name not in data[cat_key]["items"]: return False
    data[cat_key]["items"][item_name]["description"]=desc; save_products(data); return True

def set_item_manual(cat_key,item_name,manual):
    data=load_products()
    if item_name not in data[cat_key]["items"]: return False
    data[cat_key]["items"][item_name]["manual"]=manual; save_products(data); return True

def set_item_price(cat_key,item_name,price):
    data=load_products()
    if item_name not in data[cat_key]["items"]: return False
    data[cat_key]["items"][item_name]["price"]=price; save_products(data); return True
