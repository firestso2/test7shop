import io, csv
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from database import (
    get_all_admin_ids, get_setting, set_setting,
    get_users_count, get_new_users_today, get_new_users_week,
    get_total_revenue, get_top_products, get_top_spenders,
    get_all_users, get_all_orders, update_balance,
    ban_user, search_user, add_admin, remove_admin,
    get_referral_stats, get_total_deposits, get_total_referral_earnings,
    add_referral_earning, add_to_queue, get_queue_position, get_queue_by_order_num,
    create_coupon, set_purchase_discount
)
from products import (
    get_all_items_with_stock, get_items_in_category,
    add_stock_items, delete_stock_item, clear_category_stock,
    get_stock_summary, export_stock_txt,
    set_item_description, set_item_manual, set_item_price,
    pop_stock_item, CATEGORY_DISPLAY
)
from keyboards import (
    admin_main_kb, admin_products_kb, admin_users_kb,
    admin_settings_kb, admin_broadcast_kb, broadcast_confirm_kb,
    admin_categories_kb, admin_items_kb, confirm_action_kb,
    back_btn, after_purchase_kb
)
from utils import parse_numbered_list, fmt_date, log_event
from config import QUEUE_ITEMS_CATS, MANUAL_LINK, EXCHANGE_ITEMS, REFERRAL_PERCENT
from config import PURCHASE_TIER_EVERY, PURCHASE_TIER_DISCOUNT, PURCHASE_TIER_USES

router = Router()


class AdminStates(StatesGroup):
    select_cat_add        = State()
    select_item_add       = State()
    new_item_name         = State()
    waiting_stock_data    = State()
    select_cat_del        = State()
    select_item_del       = State()
    waiting_del_index     = State()
    select_cat_clear      = State()
    select_cat_edit_desc  = State()
    select_item_edit_desc = State()
    waiting_new_desc      = State()
    select_cat_edit_manual  = State()
    select_item_edit_manual = State()
    waiting_new_manual      = State()
    select_cat_edit_price   = State()
    select_item_edit_price  = State()
    waiting_new_price       = State()
    waiting_find_user       = State()
    waiting_ban_id          = State()
    waiting_balance_id      = State()
    waiting_balance_amount  = State()
    waiting_balance_comment = State()
    waiting_broadcast_msg   = State()
    waiting_welcome_text    = State()
    waiting_new_admin_id    = State()
    waiting_del_admin_id    = State()
    waiting_coupon_uid      = State()
    waiting_coupon_pct      = State()
    waiting_coupon_uses     = State()


async def is_admin(uid): return uid in await get_all_admin_ids()

async def guard(call):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещён.", show_alert=True); return False
    return True

async def edit_or_send(call, text, kb):
    try: await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except: await call.message.answer(text, reply_markup=kb, parse_mode="HTML")


# ── ENTRY ─────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён."); return
    await message.answer("👑 <b>@дм1н-п@нель</b>", reply_markup=admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:main")
async def adm_main(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.clear()
    await edit_or_send(call, "👑 <b>@дм1н-п@нель</b>", admin_main_kb())
    await call.answer()


# ── STATS ─────────────────────────────────────────────────

@router.callback_query(F.data == "adm:stats")
async def adm_stats(call: CallbackQuery):
    if not await guard(call): return
    total = await get_users_count()
    today = await get_new_users_today()
    week  = await get_new_users_week()
    rev   = await get_total_revenue()
    deps  = await get_total_deposits()
    ref_e = await get_total_referral_earnings()
    top_p = await get_top_products(5)
    top_s = await get_top_spenders(5)
    tp = "".join(f"  {i}. {p['product_name']} — {p['cnt']} шт. | ${p['revenue']:.2f}\n" for i,p in enumerate(top_p,1)) or "  Нет данных\n"
    ts = "".join(f"  {i}. {'@'+u['username'] if u['username'] else 'ID:'+str(u['tg_id'])} — ${u['total_spent']:.2f}\n" for i,u in enumerate(top_s,1)) or "  Нет данных\n"
    text = (f"📊 <b>Ст@тистик@</b>\n\n"
            f"👥 Пользователи: <b>{total}</b> | Сегодня: <b>+{today}</b> | Неделя: <b>+{week}</b>\n\n"
            f"💰 Продажи: <b>${rev:.2f}</b> | Пополнения: <b>${deps:.2f}</b> | Реф: <b>${ref_e:.2f}</b>\n\n"
            f"🏆 <b>Топ товаров:</b>\n{tp}\n💸 <b>Топ покупателей:</b>\n{ts}")
    await edit_or_send(call, text, back_btn("adm:main"))
    await call.answer()


# ── PRODUCTS ──────────────────────────────────────────────

@router.callback_query(F.data == "adm:products")
async def adm_products(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.clear()
    await edit_or_send(call, "📦 <b>Упр@вление т0в@р@ми</b>", admin_products_kb())
    await call.answer()

@router.callback_query(F.data == "adm:stock_summary")
async def adm_stock_summary(call: CallbackQuery):
    if not await guard(call): return
    summary = get_stock_summary()
    lines = ["📋 <b>0ст@тки:</b>\n"]
    for cat_key, cat_data in summary.items():
        lines.append(f"<b>{cat_data['name']}</b>")
        for name, count in cat_data["items"].items():
            lines.append(f"  {'✅' if count>0 else '❌'} {name}: {count} шт.")
        lines.append("")
    await edit_or_send(call, "\n".join(lines), back_btn("adm:products"))
    await call.answer()

@router.callback_query(F.data == "adm:export_stock")
async def adm_export_stock(call: CallbackQuery):
    if not await guard(call): return
    content = export_stock_txt()
    await call.message.answer_document(BufferedInputFile(content.encode("utf-8"), filename="stock.txt"), caption="📤 Наличие товаров")
    await call.answer()

@router.callback_query(F.data == "adm:add_stock")
async def adm_add_stock(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.clear()
    await state.set_state(AdminStates.select_cat_add)
    await edit_or_send(call, "➕ <b>П0п0лнить т0в@р</b>\n\nВыберите к@тег0рию:", admin_categories_kb("adm_add_cat"))
    await call.answer()

@router.callback_query(F.data.startswith("adm_add_cat:"))
async def adm_add_cat_sel(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    # Принимаем в любом состоянии — на случай если FSM слетело
    cat_key = call.data.split(":")[1]
    await state.update_data(cat_key=cat_key)
    await state.set_state(AdminStates.select_item_add)
    items = get_all_items_with_stock(cat_key)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = admin_items_kb(cat_key, items, "adm_add_item")
    rows = kb.inline_keyboard.copy()
    rows.insert(-1, [InlineKeyboardButton(text="🆕 Н0вый т0в@р", callback_data=f"adm_new_item:{cat_key}")])
    await call.message.edit_text(
        f"📂 <b>{CATEGORY_DISPLAY[cat_key]}</b>\n\nВыберите существующий товар или создайте новый:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data.startswith("adm_new_item:"))
async def adm_new_item(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    cat_key = call.data.split(":")[1]
    await state.update_data(cat_key=cat_key)
    await state.set_state(AdminStates.new_item_name)
    await call.message.edit_text(
        f"📂 Категория: <b>{CATEGORY_DISPLAY[cat_key]}</b>\n\n✏️ Введите н@звание нового товара:\n<i>(просто напишите ответным сообщением)</i>",
        reply_markup=back_btn("adm:products"), parse_mode="HTML"
    )
    await call.answer()

@router.message(AdminStates.new_item_name)
async def adm_new_item_name(message: Message, state: FSMContext):
    item_name = message.text.strip()
    if not item_name:
        await message.answer("❌ Название не может быть пустым. Введите ещё раз:")
        return
    data = await state.get_data()
    cat_key = data.get("cat_key", "")
    await state.update_data(item_name=item_name)
    await state.set_state(AdminStates.waiting_stock_data)
    await message.answer(
        f"📂 Категория: <b>{CATEGORY_DISPLAY.get(cat_key, cat_key)}</b>\n"
        f"📦 Товар: <b>{item_name}</b>\n\n"
        f"Теперь отправьте данные нумерованным списком:\n\n"
        f"<code>1. данные первой единицы\n"
        f"2. данные второй единицы\n"
        f"3. и так далее...</code>\n\n"
        f"<i>Каждая строка = одна единица товара</i>",
        reply_markup=back_btn("adm:products"), parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("adm_add_item:"))
async def adm_add_existing(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    parts = call.data.split(":")
    cat_key, item_name = parts[1], parts[2]
    await state.update_data(cat_key=cat_key, item_name=item_name)
    await state.set_state(AdminStates.waiting_stock_data)
    items = get_all_items_with_stock(cat_key)
    current_stock = items.get(item_name, {}).get("stock", 0)
    await call.message.edit_text(
        f"📂 Категория: <b>{CATEGORY_DISPLAY.get(cat_key, cat_key)}</b>\n"
        f"📦 Товар: <b>{item_name}</b>\n"
        f"📊 Сейчас в наличии: <b>{current_stock} шт.</b>\n\n"
        f"Отправьте новые данные нумерованным списком:\n\n"
        f"<code>1. данные первой единицы\n"
        f"2. данные второй единицы\n"
        f"3. и так далее...</code>\n\n"
        f"<i>Каждая строка = одна единица товара</i>",
        reply_markup=back_btn("adm:products"), parse_mode="HTML"
    )
    await call.answer()

@router.message(AdminStates.waiting_stock_data)
async def adm_stock_received(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_key   = data.get("cat_key")
    item_name = data.get("item_name")

    # Защита: если данные FSM потерялись
    if not cat_key or not item_name:
        await message.answer(
            "❌ Что-то пошло не так — начните заново через /admin → Управление товарами → Пополнить товар.",
            reply_markup=admin_products_kb()
        )
        await state.clear()
        return

    if not message.text or not message.text.strip():
        await message.answer("❌ Пустое сообщение. Отправьте список данных.")
        return

    items = parse_numbered_list(message.text)
    if not items:
        await message.answer(
            "❌ Не удалось распознать список.\n\n"
            "Убедитесь что формат правильный:\n"
            "<code>1. данные\n2. данные</code>",
            parse_mode="HTML"
        )
        return

    add_stock_items(cat_key, item_name, items)
    log_event("STOCK_ADD", message.from_user.id, f"cat={cat_key}, item={item_name}, n={len(items)}")
    await state.clear()
    await message.answer(
        f"✅ <b>Готово!</b>\n\n"
        f"📂 Категория: {CATEGORY_DISPLAY.get(cat_key, cat_key)}\n"
        f"📦 Товар: <b>{item_name}</b>\n"
        f"➕ Добавлено: <b>{len(items)} шт.</b>",
        reply_markup=admin_products_kb(), parse_mode="HTML"
    )

@router.callback_query(F.data == "adm:del_stock_item")
async def adm_del_stock(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.select_cat_del)
    await edit_or_send(call, "🗑 Выберите к@тег0рию:", admin_categories_kb("adm_del_cat"))
    await call.answer()

@router.callback_query(F.data.startswith("adm_del_cat:"), AdminStates.select_cat_del)
async def adm_del_cat(call: CallbackQuery, state: FSMContext):
    cat_key = call.data.split(":")[1]
    await state.update_data(cat_key=cat_key); await state.set_state(AdminStates.select_item_del)
    await call.message.edit_text("Выберите товар:", reply_markup=admin_items_kb(cat_key, get_all_items_with_stock(cat_key), "adm_del_item"))
    await call.answer()

@router.callback_query(F.data.startswith("adm_del_item:"), AdminStates.select_item_del)
async def adm_del_item(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":"); cat_key, item_name = parts[1], parts[2]
    await state.update_data(cat_key=cat_key, item_name=item_name); await state.set_state(AdminStates.waiting_del_index)
    stock = get_items_in_category(cat_key).get(item_name, {}).get("stock", [])
    if not stock: await call.answer("Склад пуст.", show_alert=True); return
    lines = [f"<b>{item_name}</b> — {len(stock)} шт.\n"]
    for i, s in enumerate(stock[:20]): lines.append(f"<code>{i}.</code> {str(s)[:60]}")
    if len(stock) > 20: lines.append(f"... и ещё {len(stock)-20}")
    lines.append("\nВведите индекс (с 0):")
    await call.message.edit_text("\n".join(lines), reply_markup=back_btn("adm:products"), parse_mode="HTML")
    await call.answer()

@router.message(AdminStates.waiting_del_index)
async def adm_del_index(message: Message, state: FSMContext):
    data = await state.get_data()
    try: idx = int(message.text.strip())
    except ValueError: await message.answer("❌ Введите число."); return
    ok = delete_stock_item(data["cat_key"], data["item_name"], idx)
    await state.clear()
    await message.answer("✅ Удалено." if ok else "❌ Индекс не найден.", reply_markup=admin_products_kb())

@router.callback_query(F.data == "adm:clear_cat")
async def adm_clear_cat(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.select_cat_clear)
    await edit_or_send(call, "🧹 Выберите к@тег0рию:", admin_categories_kb("adm_clear_cat"))
    await call.answer()

@router.callback_query(F.data.startswith("adm_clear_cat:"), AdminStates.select_cat_clear)
async def adm_clear_confirm(call: CallbackQuery, state: FSMContext):
    cat_key = call.data.split(":")[1]; await state.clear()
    await call.message.edit_text(f"⚠️ Очистить <b>{CATEGORY_DISPLAY[cat_key]}</b>?", reply_markup=confirm_action_kb(f"adm_clear_do:{cat_key}"), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("adm_clear_do:"))
async def adm_clear_do(call: CallbackQuery):
    if not await guard(call): return
    cat_key = call.data.split(":")[1]; clear_category_stock(cat_key)
    log_event("STOCK_CLEAR", call.from_user.id, f"cat={cat_key}")
    await call.message.edit_text(f"✅ <b>{CATEGORY_DISPLAY[cat_key]}</b> очищена.", reply_markup=admin_products_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "adm:edit_desc")
async def adm_edit_desc(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.select_cat_edit_desc)
    await edit_or_send(call, "✏️ Выберите к@тег0рию:", admin_categories_kb("adm_edesc_cat")); await call.answer()

@router.callback_query(F.data.startswith("adm_edesc_cat:"), AdminStates.select_cat_edit_desc)
async def adm_edesc_cat(call: CallbackQuery, state: FSMContext):
    cat_key = call.data.split(":")[1]; await state.update_data(cat_key=cat_key); await state.set_state(AdminStates.select_item_edit_desc)
    await call.message.edit_text("Выберите товар:", reply_markup=admin_items_kb(cat_key, get_all_items_with_stock(cat_key), "adm_edesc_item")); await call.answer()

@router.callback_query(F.data.startswith("adm_edesc_item:"), AdminStates.select_item_edit_desc)
async def adm_edesc_item(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":"); await state.update_data(item_name=parts[2]); await state.set_state(AdminStates.waiting_new_desc)
    await call.message.edit_text("✏️ Введите новое описание:", reply_markup=back_btn("adm:products")); await call.answer()

@router.message(AdminStates.waiting_new_desc)
async def adm_save_desc(message: Message, state: FSMContext):
    data = await state.get_data(); set_item_description(data["cat_key"], data["item_name"], message.text.strip()); await state.clear()
    await message.answer("✅ Описание обновлено.", reply_markup=admin_products_kb())

@router.callback_query(F.data == "adm:edit_manual")
async def adm_edit_manual(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.select_cat_edit_manual)
    await edit_or_send(call, "📝 Выберите к@тег0рию:", admin_categories_kb("adm_emanual_cat")); await call.answer()

@router.callback_query(F.data.startswith("adm_emanual_cat:"), AdminStates.select_cat_edit_manual)
async def adm_emanual_cat(call: CallbackQuery, state: FSMContext):
    cat_key = call.data.split(":")[1]; await state.update_data(cat_key=cat_key); await state.set_state(AdminStates.select_item_edit_manual)
    await call.message.edit_text("Выберите товар:", reply_markup=admin_items_kb(cat_key, get_all_items_with_stock(cat_key), "adm_emanual_item")); await call.answer()

@router.callback_query(F.data.startswith("adm_emanual_item:"), AdminStates.select_item_edit_manual)
async def adm_emanual_item(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":"); await state.update_data(item_name=parts[2]); await state.set_state(AdminStates.waiting_new_manual)
    await call.message.edit_text("📝 Введите новый мануал:", reply_markup=back_btn("adm:products")); await call.answer()

@router.message(AdminStates.waiting_new_manual)
async def adm_save_manual(message: Message, state: FSMContext):
    data = await state.get_data(); set_item_manual(data["cat_key"], data["item_name"], message.text.strip()); await state.clear()
    await message.answer("✅ Мануал обновлён.", reply_markup=admin_products_kb())

@router.callback_query(F.data == "adm:edit_price")
async def adm_edit_price(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.select_cat_edit_price)
    await edit_or_send(call, "💲 Выберите к@тег0рию:", admin_categories_kb("adm_eprice_cat")); await call.answer()

@router.callback_query(F.data.startswith("adm_eprice_cat:"), AdminStates.select_cat_edit_price)
async def adm_eprice_cat(call: CallbackQuery, state: FSMContext):
    cat_key = call.data.split(":")[1]; await state.update_data(cat_key=cat_key); await state.set_state(AdminStates.select_item_edit_price)
    await call.message.edit_text("Выберите товар:", reply_markup=admin_items_kb(cat_key, get_all_items_with_stock(cat_key), "adm_eprice_item")); await call.answer()

@router.callback_query(F.data.startswith("adm_eprice_item:"), AdminStates.select_item_edit_price)
async def adm_eprice_item(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":"); await state.update_data(item_name=parts[2]); await state.set_state(AdminStates.waiting_new_price)
    await call.message.edit_text("💲 Введите новую цену ($):", reply_markup=back_btn("adm:products")); await call.answer()

@router.message(AdminStates.waiting_new_price)
async def adm_save_price(message: Message, state: FSMContext):
    data = await state.get_data()
    try: price = float(message.text.replace(",",".").strip())
    except ValueError: await message.answer("❌ Введите число."); return
    set_item_price(data["cat_key"], data["item_name"], price); await state.clear()
    await message.answer(f"✅ Цена: <b>${price:.2f}</b>", reply_markup=admin_products_kb(), parse_mode="HTML")


# ── USERS ─────────────────────────────────────────────────

@router.callback_query(F.data == "adm:users")
async def adm_users(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.clear(); await edit_or_send(call, "👥 <b>П0льз0в@тели</b>", admin_users_kb()); await call.answer()

@router.callback_query(F.data == "adm:find_user")
async def adm_find_user(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.waiting_find_user)
    await edit_or_send(call, "🔍 Введите ID или @username:", back_btn("adm:users")); await call.answer()

@router.message(AdminStates.waiting_find_user)
async def adm_find_user_result(message: Message, state: FSMContext):
    await state.clear()
    q = message.text.strip()
    user = await search_user(tg_id=int(q) if q.lstrip("@").isdigit() else None, username=None if q.lstrip("@").isdigit() else q)
    if not user: await message.answer("❌ Не найден.", reply_markup=admin_users_kb()); return
    inv, ref_e = await get_referral_stats(user["tg_id"])
    uname = f"@{user['username']}" if user["username"] else "—"
    text = (f"👤 <b>Профиль</b>\n\n🆔 ID: <code>{user['tg_id']}</code>\n👤 {uname}\n"
            f"💰 Баланс: <b>${user['balance']:.2f}</b>\n🛒 Покупок: <b>{user['purchases_count']}</b>\n"
            f"💸 Потрачено: <b>${user['total_spent']:.2f}</b>\n👥 Рефералов: <b>{inv}</b>\n"
            f"🎁 Реф. заработок: <b>${ref_e:.2f}</b>\n📅 Рег.: {fmt_date(user['registered_at'])}\n"
            f"Статус: {'🚫 Забанен' if user['is_banned'] else '✅ Активен'}")
    await message.answer(text, reply_markup=admin_users_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:edit_balance")
async def adm_edit_balance(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.waiting_balance_id)
    await edit_or_send(call, "💰 Введите ID пользователя:", back_btn("adm:users")); await call.answer()

@router.message(AdminStates.waiting_balance_id)
async def adm_balance_id(message: Message, state: FSMContext):
    try: uid = int(message.text.strip())
    except ValueError: await message.answer("❌ Введите числовой ID."); return
    user = await search_user(tg_id=uid)
    if not user: await message.answer("❌ Не найден.", reply_markup=admin_users_kb()); await state.clear(); return
    await state.update_data(target_uid=uid); await state.set_state(AdminStates.waiting_balance_amount)
    await message.answer(f"💰 Баланс: <b>${user['balance']:.2f}</b>\n\nВведите сумму (<code>+10</code> или <code>-5</code>):", reply_markup=back_btn("adm:users"), parse_mode="HTML")

@router.message(AdminStates.waiting_balance_amount)
async def adm_balance_amount(message: Message, state: FSMContext):
    try: amount = float(message.text.replace(",",".").strip())
    except ValueError: await message.answer("❌ Введите число."); return
    await state.update_data(balance_amount=amount); await state.set_state(AdminStates.waiting_balance_comment)
    await message.answer("✏️ Комментарий (или «-»):")

@router.message(AdminStates.waiting_balance_comment)
async def adm_balance_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text.strip() if message.text.strip() != "-" else "Ручная корректировка"
    await update_balance(data["target_uid"], data["balance_amount"], comment)
    log_event("ADMIN_BALANCE", message.from_user.id, f"target={data['target_uid']}, delta={data['balance_amount']}")
    await state.clear()
    await message.answer(f"✅ Баланс <code>{data['target_uid']}</code> изменён на <b>{data['balance_amount']:+.2f}$</b>", reply_markup=admin_users_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:ban_user")
async def adm_ban(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.waiting_ban_id)
    await edit_or_send(call, "🚫 Введите ID для бана/разбана:", back_btn("adm:users")); await call.answer()

@router.message(AdminStates.waiting_ban_id)
async def adm_ban_do(message: Message, state: FSMContext):
    await state.clear()
    try: uid = int(message.text.strip())
    except ValueError: await message.answer("❌ Числовой ID.", reply_markup=admin_users_kb()); return
    user = await search_user(tg_id=uid)
    if not user: await message.answer("❌ Не найден.", reply_markup=admin_users_kb()); return
    new_ban = not bool(user["is_banned"]); await ban_user(uid, new_ban)
    log_event("BAN" if new_ban else "UNBAN", message.from_user.id, f"target={uid}")
    await message.answer(f"{'🚫 Забанен' if new_ban else '✅ Разбанен'}: <code>{uid}</code>", reply_markup=admin_users_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:export_users")
async def adm_export_users(call: CallbackQuery):
    if not await guard(call): return
    users = await get_all_users()
    out = io.StringIO(); wr = csv.writer(out)
    wr.writerow(["tg_id","username","balance","purchases_count","total_spent","registered_at","is_banned"])
    for u in users: wr.writerow([u["tg_id"],u["username"],u["balance"],u["purchases_count"],u["total_spent"],u["registered_at"],u["is_banned"]])
    await call.message.answer_document(BufferedInputFile(out.getvalue().encode("utf-8-sig"), filename="users.csv"), caption="📥 Пользователи (CSV)")
    await call.answer()


# ── ORDERS ────────────────────────────────────────────────

@router.callback_query(F.data == "adm:orders")
async def adm_orders(call: CallbackQuery):
    if not await guard(call): return
    orders = await get_all_orders(20)
    if not orders: await edit_or_send(call, "🛒 Заказов нет.", back_btn("adm:main")); await call.answer(); return
    lines = ["🛒 <b>Последние 20 з@к@зов:</b>\n"]
    for o in orders:
        uname = f"@{o['username']}" if o["username"] else f"ID:{o['user_id']}"
        lines.append(f"<b>#{o['order_num']}</b> | {uname} | {o['product_name']} | ${o['price']:.2f} | {fmt_date(o['created_at'])}")
    text = "\n".join(lines)
    if len(text) > 4000: text = text[:3900] + "\n..."
    await edit_or_send(call, text, back_btn("adm:main")); await call.answer()


# ── BROADCAST ─────────────────────────────────────────────

@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.clear(); await edit_or_send(call, "📣 <b>Р@ссылк@</b>\nВыберите аудиторию:", admin_broadcast_kb()); await call.answer()

@router.callback_query(F.data.startswith("adm:broadcast:"))
async def adm_broadcast_target(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    target = call.data.split(":")[2]
    labels = {"all":"Всем","buyers":"Покупателям","new":"Новым"}
    await state.update_data(broadcast_target=target); await state.set_state(AdminStates.waiting_broadcast_msg)
    await call.message.edit_text(f"📣 <b>{labels.get(target)}</b>\n\nОтправьте сообщение (текст или фото с подписью):", reply_markup=back_btn("adm:broadcast"), parse_mode="HTML")
    await call.answer()

@router.message(AdminStates.waiting_broadcast_msg)
async def adm_broadcast_preview(message: Message, state: FSMContext):
    data = await state.get_data(); target = data.get("broadcast_target","all")
    if message.photo: await state.update_data(msg_type="photo", file_id=message.photo[-1].file_id, caption=message.caption or "")
    else: await state.update_data(msg_type="text", text=message.text or "")
    labels = {"all":"Всем","buyers":"Покупателям","new":"Новым"}
    await message.answer(f"👁 Предпросмотр выше.\nАудитория: <b>{labels.get(target)}</b>\nОтправить?", reply_markup=broadcast_confirm_kb(target), parse_mode="HTML")

@router.callback_query(F.data.startswith("adm:broadcast_send:"))
async def adm_broadcast_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await guard(call): return
    target = call.data.split(":")[2]; data = await state.get_data(); await state.clear()
    users = await get_all_users()
    if target == "buyers": users = [u for u in users if u["purchases_count"] > 0]
    elif target == "new": users = [u for u in users if u["purchases_count"] == 0]
    sent = blocked = 0
    await call.message.edit_text(f"📣 Отправка... 0/{len(users)}")
    for i, user in enumerate(users):
        try:
            if data.get("msg_type") == "photo": await bot.send_photo(user["tg_id"], photo=data["file_id"], caption=data.get("caption",""))
            else: await bot.send_message(user["tg_id"], data.get("text",""))
            sent += 1
        except: blocked += 1
        if (i+1) % 30 == 0:
            try: await call.message.edit_text(f"📣 Отправка... {i+1}/{len(users)}")
            except: pass
    log_event("BROADCAST", call.from_user.id, f"target={target}, sent={sent}, blocked={blocked}")
    await call.message.edit_text(f"✅ <b>Р@ссылка завершена</b>\n\n📤 Доставлено: <b>{sent}</b>\n🚫 Заблокировало: <b>{blocked}</b>", reply_markup=back_btn("adm:main"), parse_mode="HTML")
    await call.answer()


# ── FINANCE ───────────────────────────────────────────────

@router.callback_query(F.data == "adm:finance")
async def adm_finance(call: CallbackQuery):
    if not await guard(call): return
    rev = await get_total_revenue(); deps = await get_total_deposits(); ref = await get_total_referral_earnings()
    orders = await get_all_orders(5)
    recent = "\n".join(f"  #{o['order_num']} | ${o['price']:.2f} | {fmt_date(o['created_at'])}" for o in orders) or "  Нет данных"
    text = (f"💰 <b>Фин@нсы</b>\n\n📈 Продажи: <b>${rev:.2f}</b>\n💳 Пополнения: <b>${deps:.2f}</b>\n🎁 Реф. выплаты: <b>${ref:.2f}</b>\n\n🕐 <b>Последние 5 заказов:</b>\n{recent}")
    await edit_or_send(call, text, back_btn("adm:main")); await call.answer()


# ── SETTINGS ──────────────────────────────────────────────

@router.callback_query(F.data == "adm:settings")
async def adm_settings(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.clear()
    m = await get_setting("maintenance_mode"); status = "🟢 Включён" if m=="1" else "🔴 Выключен"
    await edit_or_send(call, f"⚙️ <b>Н@стр0йки</b>\n\nТехобслуживание: {status}", admin_settings_kb()); await call.answer()

@router.callback_query(F.data == "adm:toggle_maintenance")
async def adm_toggle_maintenance(call: CallbackQuery):
    if not await guard(call): return
    cur = await get_setting("maintenance_mode"); nv = "0" if cur=="1" else "1"
    await set_setting("maintenance_mode", nv)
    log_event("MAINTENANCE", call.from_user.id, f"mode={nv}")
    await call.answer(f"Техобслуживание: {'🟢 ВКЛ' if nv=='1' else '🔴 ВЫКЛ'}", show_alert=True)
    m = await get_setting("maintenance_mode"); s = "🟢 Включён" if m=="1" else "🔴 Выключен"
    await call.message.edit_text(f"⚙️ <b>Н@стр0йки</b>\n\nТехобслуживание: {s}", reply_markup=admin_settings_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:edit_welcome")
async def adm_edit_welcome(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.waiting_welcome_text)
    await edit_or_send(call, "✏️ Введите новый текст приветствия:", back_btn("adm:settings")); await call.answer()

@router.message(AdminStates.waiting_welcome_text)
async def adm_save_welcome(message: Message, state: FSMContext):
    await set_setting("welcome_text", message.text.strip()); await state.clear()
    await message.answer("✅ Текст приветствия обновлён.", reply_markup=admin_settings_kb())

@router.callback_query(F.data == "adm:add_admin")
async def adm_add_admin_cb(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.waiting_new_admin_id)
    await edit_or_send(call, "👑 Введите ID нового администратора:", back_btn("adm:settings")); await call.answer()

@router.message(AdminStates.waiting_new_admin_id)
async def adm_add_admin_do(message: Message, state: FSMContext):
    await state.clear()
    try: uid = int(message.text.strip())
    except ValueError: await message.answer("❌ Числовой ID.", reply_markup=admin_settings_kb()); return
    await add_admin(uid); log_event("ADD_ADMIN", message.from_user.id, f"new={uid}")
    await message.answer(f"✅ Администратор <code>{uid}</code> добавлен.", reply_markup=admin_settings_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:del_admin")
async def adm_del_admin_cb(call: CallbackQuery, state: FSMContext):
    if not await guard(call): return
    await state.set_state(AdminStates.waiting_del_admin_id)
    await edit_or_send(call, "❌ Введите ID для удаления:", back_btn("adm:settings")); await call.answer()

@router.message(AdminStates.waiting_del_admin_id)
async def adm_del_admin_do(message: Message, state: FSMContext):
    await state.clear()
    try: uid = int(message.text.strip())
    except ValueError: await message.answer("❌ Числовой ID.", reply_markup=admin_settings_kb()); return
    from config import ADMIN_IDS
    if uid in ADMIN_IDS: await message.answer("❌ Нельзя удалить главного администратора.", reply_markup=admin_settings_kb()); return
    await remove_admin(uid); log_event("DEL_ADMIN", message.from_user.id, f"removed={uid}")
    await message.answer(f"✅ Администратор <code>{uid}</code> удалён.", reply_markup=admin_settings_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:list_admins")
async def adm_list_admins(call: CallbackQuery):
    if not await guard(call): return
    admins = await get_all_admin_ids()
    text = "👑 <b>Администраторы:</b>\n\n" + "\n".join(f"• <code>{a}</code>" for a in admins)
    await edit_or_send(call, text, back_btn("adm:settings")); await call.answer()

@router.callback_query(F.data == "adm:backup_db")
async def adm_backup_db(call: CallbackQuery):
    if not await guard(call): return
    from config import DB_PATH
    try:
        with open(DB_PATH, "rb") as f: data = f.read()
        from datetime import datetime
        fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        await call.message.answer_document(BufferedInputFile(data, filename=fname), caption="💾 Резервная копия БД")
    except Exception as e:
        await call.message.answer(f"❌ Ошибка: {e}")
    await call.answer()


# ── BUY ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy:"))
async def buy_product(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":"); cat_key, item_name = parts[1], parts[2]
    from database import get_user, create_order, consume_purchase_discount, check_and_grant_purchase_tier, set_purchase_discount, get_coupon, use_coupon
    user = await get_user(call.from_user.id)
    items = get_all_items_with_stock(cat_key)
    item = items.get(item_name)
    if not item or item["stock"] <= 0:
        await call.answer("❌ Товар закончился.", show_alert=True); return

    price = item["price"]

    # Определяем итоговую скидку
    discount_pct = 0
    discount_src = ""

    # 1. Скидка за покупки (приоритет)
    tier_discount = await consume_purchase_discount(call.from_user.id)
    if tier_discount > 0:
        discount_pct = tier_discount; discount_src = f"скидка за активность {tier_discount}%"

    # 2. Купон из state (если нет скидки за покупки)
    if discount_pct == 0:
        fsm_data = await state.get_data()
        pending_coupon = fsm_data.get("pending_coupon")
        if pending_coupon:
            coupon = await get_coupon(pending_coupon)
            if coupon and coupon["uses_left"] > 0:
                discount_pct = coupon["discount_percent"]; discount_src = f"купон {pending_coupon}"

    final_price = round(price * (1 - discount_pct / 100), 2) if discount_pct > 0 else price

    if user["balance"] < final_price:
        await call.answer(f"❌ Недостаточно средств.\nНужно: ${final_price:.2f} | У вас: ${user['balance']:.2f}", show_alert=True); return

    product_data = pop_stock_item(cat_key, item_name)
    if not product_data: await call.answer("❌ Товар закончился.", show_alert=True); return

    order_num, order_db_id = await create_order(call.from_user.id, item_name, cat_key, final_price, str(product_data))

    # Применяем купон
    if discount_pct > 0 and discount_src.startswith("купон"):
        fsm_data = await state.get_data()
        pending_coupon = fsm_data.get("pending_coupon")
        if pending_coupon:
            coupon = await get_coupon(pending_coupon)
            if coupon: await use_coupon(coupon["id"], call.from_user.id, order_num)
        await state.update_data(pending_coupon=None)

    log_event("PURCHASE", call.from_user.id, f"order={order_num}, item={item_name}, price={final_price}, disc={discount_pct}%")

    # Реферальный бонус
    if user["referrer_id"]:
        bonus = round(final_price * REFERRAL_PERCENT / 100, 2)
        await add_referral_earning(user["referrer_id"], call.from_user.id, bonus)
        try: await call.bot.send_message(user["referrer_id"], f"🎁 Реф. бонус +${bonus:.2f} от покупки реферала!", parse_mode="HTML")
        except: pass

    # Проверяем порог скидки за покупки
    should_grant = await check_and_grant_purchase_tier(call.from_user.id)
    if should_grant:
        await set_purchase_discount(call.from_user.id, PURCHASE_TIER_DISCOUNT, PURCHASE_TIER_USES)
        try:
            await call.bot.send_message(
                call.from_user.id,
                f"🎉 <b>Вы совершили {PURCHASE_TIER_EVERY} покупки!</b>\n\n"
                f"Вам начислена скидка <b>{PURCHASE_TIER_DISCOUNT}%</b> на следующие <b>{PURCHASE_TIER_USES}</b> покупки.\n"
                f"Скидка применяется автоматически.",
                parse_mode="HTML"
            )
        except: pass

    discount_line = f"\n💥 Скидка: <b>{discount_pct}%</b> ({discount_src})\n💲 Итого: <b>${final_price:.2f}</b>" if discount_pct > 0 else f"\n💲 Цена: <b>${price:.2f}</b>"

    in_queue = cat_key in QUEUE_ITEMS_CATS

    # Добавляем в очередь если нужно
    if in_queue:
        await add_to_queue(order_db_id, order_num, call.from_user.id, item_name, cat_key)
        q = await get_queue_by_order_num(order_num)
        pos_item, pos_total = (await get_queue_position(q["id"])) if q else (1, 1)
        queue_info = (f"\n\n📊 <b>Позиция в очереди:</b>\n"
                      f"├ По сервису «{item_name}»: <b>#{pos_item}</b>\n"
                      f"└ 0бщ@я: <b>#{pos_total}</b>")
    else:
        queue_info = ""

    # Для бирж — инструкция по 2FA
    if item_name in EXCHANGE_ITEMS:
        extra = ("\n\n⚠️ <b>Для верификации:</b>\n"
                 "1️⃣ Отключите 2FA\n"
                 "2️⃣ Напишите в поддержку: <code>email:пароль</code>")
    else:
        extra = ""

    text = (f"✅ <b>П0купка успешна!</b>\n\n"
            f"📦 Тов@р: <b>{item_name}</b>\n"
            f"🧾 З@к@з: <b>#{order_num}</b>"
            f"{discount_line}{queue_info}{extra}")

    # Для банков — выдаём данные сразу
    if cat_key == "banks":
        text += f"\n\n📋 <b>Д@нные:</b>\n<code>{product_data}</code>"

    review_text = (f"\n\n✍️ <b>0ставьте отзыв</b> в @rewiews_vorache777\n"
                   f"Формат: <code>+реп @vorache777, верифнул {item_name}...</code> + скрин\n"
                   f"За отзыв — купон <b>10%</b> на 3 покупки 🎁")
    text += review_text

    kb = after_purchase_kb(order_num, MANUAL_LINK if cat_key != "banks" else None, in_queue)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer("✅ Покупка совершена!")
