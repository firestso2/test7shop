from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ── ГЛАВНОЕ МЕНЮ ──────────────────────────────────────────────
def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🛒 Каталог")
    kb.button(text="👤 Профиль")
    kb.button(text="🆘 Поддержка")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def back_btn(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


def cancel_kb(cb: str = "back:profile") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Отмена", callback_data=cb)]
    ])


# ── КАТАЛОГ ───────────────────────────────────────────────────
def catalog_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    # Оббуф только в названиях категорий — триггерные слова
    b.button(text="🏦 Б@нки ~ Кошельки",            callback_data="cat:banks")
    b.button(text="💹 Крипт0биржи ~ TG Сервисы",     callback_data="cat:crypto")
    b.button(text="📖 Мануалы",                       callback_data="cat:manuals")
    b.button(text="🎰 Букм@керки",                    callback_data="cat:bookmakers")
    b.adjust(1)
    return b.as_markup()


def products_kb(items: dict, cat_key: str, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    item_list = list(items.items())
    total = len(item_list)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page_items = item_list[page * per_page:(page + 1) * per_page]

    for name, data in page_items:
        stock = data.get("stock", 0)
        price = data.get("price", 0)
        icon = "✅" if stock > 0 else "❌"
        label = f"{icon} {name} — ${price}"
        if data.get("item_type", "text") == "text":
            label += f" ({stock} шт.)"
        b.button(text=label, callback_data=f"product:{cat_key}:{name}:{page}")

    b.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cat_page:{cat_key}:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cat_page:{cat_key}:{page+1}"))

    rows = b.export()
    rows.append(nav)
    rows.append([
        InlineKeyboardButton(text="❓ Нет нужного товара?", callback_data=f"not_found:{cat_key}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back:catalog"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_kb(cat_key: str, item_name: str, page: int, has_stock: bool, item_type: str = "text") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if has_stock or item_type != "text":
        b.button(text="💳 Купить", callback_data=f"buy:{cat_key}:{item_name}")
    b.button(text="◀️ Назад", callback_data=f"cat_page:{cat_key}:{page}")
    b.adjust(1)
    return b.as_markup()


# ── ПРОФИЛЬ ───────────────────────────────────────────────────
def profile_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💰 Пополнить баланс",     callback_data="balance:add")
    b.button(text="📦 Мои покупки",           callback_data="my_purchases")
    b.button(text="🔍 Найти заказ",           callback_data="find_order")
    b.button(text="👥 Реферальная система",   callback_data="referral")
    b.button(text="🎫 Мои скидки",            callback_data="my_discounts")
    b.button(text="🏠 Главное меню",          callback_data="main_menu")
    b.adjust(1)
    return b.as_markup()


def invoice_kb(pay_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="balance:check")],
        [InlineKeyboardButton(text="🔴 Отмена", callback_data="back:profile")],
    ])


def referral_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back:profile")]
    ])


def after_purchase_kb(order_num: int, manual_link: str = None, in_queue: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if manual_link:
        rows.append([InlineKeyboardButton(text="📖 Инструкция по верификации", url=manual_link)])
    if in_queue:
        rows.append([InlineKeyboardButton(text="🔄 Моё место в очереди", callback_data=f"queue_refresh:{order_num}")])
    rows.append([InlineKeyboardButton(text="✍️ Оставить отзыв", url="https://t.me/rewiews_vorache777")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def queue_refresh_kb(order_num: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"queue_refresh:{order_num}")]
    ])


# ── АДМИНКА ───────────────────────────────────────────────────
def admin_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📦 Управление товарами",      callback_data="adm:products")
    b.button(text="👥 Пользователи",              callback_data="adm:users")
    b.button(text="📊 Статистика",                callback_data="adm:stats")
    b.button(text="🛒 Заказы",                   callback_data="adm:orders")
    b.button(text="📣 Рассылка",                  callback_data="adm:broadcast")
    b.button(text="💰 Финансы",                   callback_data="adm:finance")
    b.button(text="📋 Очередь верификации",       callback_data="adm:queue")
    b.button(text="⚙️ Настройки",                 callback_data="adm:settings")
    b.button(text="🔧 Технические работы",        callback_data="adm:techworks")
    b.adjust(2, 2, 2, 2, 1)
    return b.as_markup()


def admin_products_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 Остатки по категориям",     callback_data="adm:stock_summary")
    b.button(text="➕ Добавить товар",             callback_data="adm:add_stock")
    b.button(text="🗑 Удалить единицу",            callback_data="adm:del_stock_item")
    b.button(text="🧹 Очистить категорию",         callback_data="adm:clear_cat")
    b.button(text="📤 Экспорт наличия",            callback_data="adm:export_stock")
    b.button(text="✏️ Изменить описание",          callback_data="adm:edit_desc")
    b.button(text="📝 Изменить мануал",            callback_data="adm:edit_manual")
    b.button(text="💲 Изменить цену",              callback_data="adm:edit_price")
    b.button(text="◀️ Назад",                     callback_data="adm:main")
    b.adjust(1)
    return b.as_markup()


def admin_users_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔍 Найти пользователя",        callback_data="adm:find_user")
    b.button(text="💰 Изменить баланс",           callback_data="adm:edit_balance")
    b.button(text="🚫 Бан / Разбан",              callback_data="adm:ban_user")
    b.button(text="📥 Экспорт пользователей",     callback_data="adm:export_users")
    b.button(text="◀️ Назад",                    callback_data="adm:main")
    b.adjust(1)
    return b.as_markup()


def admin_settings_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔧 Техобслуживание вкл/выкл",  callback_data="adm:toggle_maintenance")
    b.button(text="✏️ Текст приветствия",          callback_data="adm:edit_welcome")
    b.button(text="👑 Добавить администратора",    callback_data="adm:add_admin")
    b.button(text="❌ Удалить администратора",     callback_data="adm:del_admin")
    b.button(text="📋 Список администраторов",     callback_data="adm:list_admins")
    b.button(text="💾 Бэкап БД",                  callback_data="adm:backup_db")
    b.button(text="◀️ Назад",                     callback_data="adm:main")
    b.adjust(1)
    return b.as_markup()


def admin_broadcast_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📣 Всем пользователям",        callback_data="adm:broadcast:all")
    b.button(text="🛒 Только покупателям",        callback_data="adm:broadcast:buyers")
    b.button(text="🆕 Новым (без покупок)",       callback_data="adm:broadcast:new")
    b.button(text="◀️ Назад",                    callback_data="adm:main")
    b.adjust(1)
    return b.as_markup()


def broadcast_confirm_kb(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Отправить", callback_data=f"adm:broadcast_send:{target}"),
        InlineKeyboardButton(text="🔴 Отмена",    callback_data="adm:broadcast"),
    ]])


def admin_categories_kb(action: str) -> InlineKeyboardMarkup:
    from products import CATEGORY_DISPLAY
    b = InlineKeyboardBuilder()
    for key, name in CATEGORY_DISPLAY.items():
        b.button(text=name, callback_data=f"{action}:{key}")
    b.button(text="◀️ Назад", callback_data="adm:products")
    b.adjust(1)
    return b.as_markup()


def admin_items_kb(cat_key: str, items: dict, action: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for name in items:
        b.button(text=name, callback_data=f"{action}:{cat_key}:{name}")
    b.button(text="◀️ Назад", callback_data="adm:products")
    b.adjust(1)
    return b.as_markup()


def confirm_action_kb(yes_cb: str, no_cb: str = "adm:products") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да",      callback_data=yes_cb),
        InlineKeyboardButton(text="🔴 Отмена",  callback_data=no_cb),
    ]])


def item_type_kb(cat_key: str, item_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Текстовый товар",           callback_data=f"adm_itype:text:{cat_key}:{item_name}")],
        [InlineKeyboardButton(text="🔑 Верификация логин:пароль",  callback_data=f"adm_itype:creds:{cat_key}:{item_name}")],
        [InlineKeyboardButton(text="📱 Верификация по номеру",     callback_data=f"adm_itype:phone:{cat_key}:{item_name}")],
        [InlineKeyboardButton(text="◀️ Назад",                    callback_data="adm:products")],
    ])


def add_type_first_kb(cat_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Текстовый товар",           callback_data=f"adm_type_first:text:{cat_key}")],
        [InlineKeyboardButton(text="🔑 Верификация логин:пароль",  callback_data=f"adm_type_first:creds:{cat_key}")],
        [InlineKeyboardButton(text="📱 Верификация по номеру",     callback_data=f"adm_type_first:phone:{cat_key}")],
        [InlineKeyboardButton(text="◀️ Назад",                    callback_data="adm:add_stock")],
    ])
