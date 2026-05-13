from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def main_menu_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🛒 К@т@л0г"); kb.button(text="👤 Пр0ф1ль"); kb.button(text="🆘 П0ддержк@")
    kb.adjust(2,1)
    return kb.as_markup(resize_keyboard=True)

def back_btn(cb):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔴 Н@з@д",callback_data=cb)]])

def cancel_kb(cb="back:profile"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔴 0тмен@",callback_data=cb)]])

def catalog_kb():
    b=InlineKeyboardBuilder()
    b.button(text="🏦 Б@нки ~ К0шельки",callback_data="cat:banks")
    b.button(text="💹 Кр1пт0Б1ржи ~ TG С€рвисы",callback_data="cat:crypto")
    b.button(text="📖 М@нyалы",callback_data="cat:manuals")
    b.button(text="🎰 Бyкм€k€рk1",callback_data="cat:bookmakers")
    b.adjust(1); return b.as_markup()

def products_kb(items, cat_key, page=0, per_page=5):
    b=InlineKeyboardBuilder(); item_list=list(items.items()); total=len(item_list)
    total_pages=max(1,(total+per_page-1)//per_page); page_items=item_list[page*per_page:(page+1)*per_page]
    for name,data in page_items:
        stock=data.get("stock",0); price=data.get("price",0); icon="✅" if stock>0 else "❌"
        b.button(text=f"{icon} {name} — ${price} ({stock} шт.)",callback_data=f"product:{cat_key}:{name}:{page}")
    b.adjust(1); nav=[]
    if page>0: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"cat_page:{cat_key}:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}",callback_data="noop"))
    if page<total_pages-1: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"cat_page:{cat_key}:{page+1}"))
    rows=b.export(); rows.append(nav)
    rows.append([InlineKeyboardButton(text="❓ Не н@шли т0в@р?",callback_data=f"not_found:{cat_key}"),InlineKeyboardButton(text="🔴 Н@з@д",callback_data="back:catalog")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_detail_kb(cat_key, item_name, page, has_stock):
    b=InlineKeyboardBuilder()
    if has_stock: b.button(text="💳 Купить",callback_data=f"buy:{cat_key}:{item_name}")
    b.button(text="🔴 Н@з@д",callback_data=f"cat_page:{cat_key}:{page}")
    b.adjust(1); return b.as_markup()

def profile_kb():
    b=InlineKeyboardBuilder()
    b.button(text="💰 П0п0лнить б@ланс",callback_data="balance:add")
    b.button(text="📦 М0и п0купки",callback_data="my_purchases")
    b.button(text="🔍 Н@йти з@к@з",callback_data="find_order")
    b.button(text="👥 Реф€р@льн@я с1стем@",callback_data="referral")
    b.button(text="🎫 М0и скидки",callback_data="my_discounts")
    b.button(text="🏠 Гл@вн0е мен@",callback_data="main_menu")
    b.adjust(1); return b.as_markup()

def invoice_kb(pay_url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 0пл@тить",url=pay_url)],
        [InlineKeyboardButton(text="✅ Пр0верить 0плату",callback_data="balance:check")],
        [InlineKeyboardButton(text="🔴 0тмен@",callback_data="back:profile")]
    ])

def referral_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔴 Н@з@д",callback_data="back:profile")]])

def after_purchase_kb(order_num, manual_link=None, in_queue=False):
    rows=[]
    if manual_link: rows.append([InlineKeyboardButton(text="📖 М@ну@л по верификации",url=manual_link)])
    if in_queue: rows.append([InlineKeyboardButton(text="🔄 М0ё место в очереди",callback_data=f"queue_refresh:{order_num}")])
    rows.append([InlineKeyboardButton(text="✍️ 0ставить 0тзыв",url="https://t.me/rewiews_vorache777")])
    rows.append([InlineKeyboardButton(text="🏠 Гл@вн0е мен@",callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def queue_refresh_kb(order_num):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 0бновить",callback_data=f"queue_refresh:{order_num}")]])

def admin_main_kb():
    b=InlineKeyboardBuilder()
    b.button(text="📦 Упр@вление т0в@р@ми",callback_data="adm:products")
    b.button(text="👥 П0льз0в@тели",callback_data="adm:users")
    b.button(text="📊 Ст@тистик@",callback_data="adm:stats")
    b.button(text="🛒 З@к@зы",callback_data="adm:orders")
    b.button(text="📣 Р@ссылк@",callback_data="adm:broadcast")
    b.button(text="💰 Фин@нсы",callback_data="adm:finance")
    b.button(text="📋 0чередь верификации",callback_data="adm:queue")
    b.button(text="⚙️ Н@стр0йки",callback_data="adm:settings")
    b.adjust(2,2,2,1,1); return b.as_markup()

def admin_products_kb():
    b=InlineKeyboardBuilder()
    b.button(text="📋 0ст@тки",callback_data="adm:stock_summary")
    b.button(text="➕ П0п0лнить т0в@р",callback_data="adm:add_stock")
    b.button(text="🗑 Удалить единицу",callback_data="adm:del_stock_item")
    b.button(text="🧹 0чистить к@тег0рию",callback_data="adm:clear_cat")
    b.button(text="📤 Эксп0рт н@личия",callback_data="adm:export_stock")
    b.button(text="✏️ Изменить 0пис@ние",callback_data="adm:edit_desc")
    b.button(text="📝 Изменить м@ну@л",callback_data="adm:edit_manual")
    b.button(text="💲 Изменить цену",callback_data="adm:edit_price")
    b.button(text="🔴 Н@з@д",callback_data="adm:main")
    b.adjust(1); return b.as_markup()

def admin_users_kb():
    b=InlineKeyboardBuilder()
    b.button(text="🔍 Н@йти п0льз0в@теля",callback_data="adm:find_user")
    b.button(text="💰 Изменить б@ланс",callback_data="adm:edit_balance")
    b.button(text="🚫 Б@н / Разб@н",callback_data="adm:ban_user")
    b.button(text="📥 Эксп0рт п0льз0в@телей",callback_data="adm:export_users")
    b.button(text="🔴 Н@з@д",callback_data="adm:main")
    b.adjust(1); return b.as_markup()

def admin_settings_kb():
    b=InlineKeyboardBuilder()
    b.button(text="🔧 Техобслуживание",callback_data="adm:toggle_maintenance")
    b.button(text="✏️ Текст приветствия",callback_data="adm:edit_welcome")
    b.button(text="👑 Д0б@вить @дмин@",callback_data="adm:add_admin")
    b.button(text="❌ Удалить @дмин@",callback_data="adm:del_admin")
    b.button(text="📋 Список @дминов",callback_data="adm:list_admins")
    b.button(text="💾 Б@кап БД",callback_data="adm:backup_db")
    b.button(text="🔴 Н@з@д",callback_data="adm:main")
    b.adjust(1); return b.as_markup()

def admin_broadcast_kb():
    b=InlineKeyboardBuilder()
    b.button(text="📣 Всем",callback_data="adm:broadcast:all")
    b.button(text="🛒 Т0льк0 п0купателям",callback_data="adm:broadcast:buyers")
    b.button(text="🆕 Н0вым",callback_data="adm:broadcast:new")
    b.button(text="🔴 Н@з@д",callback_data="adm:main")
    b.adjust(1); return b.as_markup()

def broadcast_confirm_kb(target):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ 0тпр@вить",callback_data=f"adm:broadcast_send:{target}"),
        InlineKeyboardButton(text="🔴 0тмен@",callback_data="adm:broadcast")
    ]])

def admin_categories_kb(action):
    from products import CATEGORY_DISPLAY
    b=InlineKeyboardBuilder()
    for key,name in CATEGORY_DISPLAY.items(): b.button(text=name,callback_data=f"{action}:{key}")
    b.button(text="🔴 Н@з@д",callback_data="adm:products"); b.adjust(1); return b.as_markup()

def admin_items_kb(cat_key, items, action):
    b=InlineKeyboardBuilder()
    for name in items: b.button(text=name,callback_data=f"{action}:{cat_key}:{name}")
    b.button(text="🔴 Н@з@д",callback_data="adm:products"); b.adjust(1); return b.as_markup()

def confirm_action_kb(yes_cb, no_cb="adm:products"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Д@",callback_data=yes_cb),
        InlineKeyboardButton(text="🔴 Нет",callback_data=no_cb)
    ]])
