from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from products import get_all_items_with_stock
from keyboards import catalog_kb, products_kb, product_detail_kb
from config import SUPPORT_CONTACT

router = Router()

# Оббуф только в названиях категорий — именно здесь триггерные слова
CAT_DESC = {
    "banks": (
        "🏦 <b>Б@нки ~ Кошельки</b>\n\n"
        "✅ Товар выдаётся в формате: номер, пароль, ключ TOTP\n"
        "✅ Гарантия на вход — 6 часов\n"
        "✅ Моментальная выдача после оплаты\n"
        "✅ Верификацию выполняете самостоятельно по инструкции"
    ),
    "crypto": (
        "💹 <b>Крипт0биржи ~ TG Сервисы</b>\n\n"
        "Верификация аккаунта на платформе.\n"
        "Процедура выполняется путём авторизации "
        "и последующего верифа — без передачи постоянного доступа."
    ),
    "manuals": (
        "📖 <b>Мануалы</b>\n\n"
        "Подробные инструкции по работе с платформами."
    ),
    "bookmakers": (
        "🎰 <b>Букм@керки</b>\n\n"
        "Верификация аккаунта на букмекерской платформе."
    ),
}


@router.message(F.text == "🛒 Каталог")
async def catalog_menu(message: Message):
    await message.answer(
        "📂 <b>Каталог товаров</b>\n\nВыберите категорию:",
        reply_markup=catalog_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back:catalog")
async def back_catalog(call: CallbackQuery):
    await call.message.edit_text(
        "📂 <b>Каталог товаров</b>\n\nВыберите категорию:",
        reply_markup=catalog_kb(),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def show_category(call: CallbackQuery):
    await _show_page(call, call.data.split(":")[1], 0)


@router.callback_query(F.data.startswith("cat_page:"))
async def show_page(call: CallbackQuery):
    _, cat_key, page = call.data.split(":")
    await _show_page(call, cat_key, int(page))


async def _show_page(call: CallbackQuery, cat_key: str, page: int):
    items = get_all_items_with_stock(cat_key)
    desc = CAT_DESC.get(cat_key, "Описание отсутствует.")
    kb = products_kb(items, cat_key, page)
    try:
        await call.message.edit_text(desc, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer(desc, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("product:"))
async def show_product(call: CallbackQuery):
    parts = call.data.split(":")
    cat_key, item_name = parts[1], parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    items = get_all_items_with_stock(cat_key)
    item = items.get(item_name)
    if not item:
        await call.answer("Товар не найден.", show_alert=True)
        return

    item_type = item.get("item_type", "text")
    stock = item["stock"]
    price = item["price"]

    # Статус наличия зависит от типа товара
    if item_type == "text":
        stock_txt = f"✅ В наличии: {stock} шт." if stock > 0 else "❌ Нет в наличии"
        available = stock > 0
    else:
        stock_txt = "✅ Доступно"
        available = True

    manual_txt = f"\n\n📋 <b>Инструкция:</b>\n{item['manual']}" if item["manual"] else ""

    # Описание типа для пользователя
    type_note = ""
    if item_type == "creds":
        type_note = "\n\n🔑 <i>Верификация: потребуются логин и пароль</i>"
    elif item_type == "phone":
        type_note = "\n\n📱 <i>Верификация: потребуется номер телефона</i>"

    text = (
        f"🏷 <b>{item_name}</b>\n\n"
        f"{item['description']}"
        f"{manual_txt}"
        f"{type_note}\n\n"
        f"💲 <b>Цена:</b> ${price}\n"
        f"{stock_txt}"
    )

    kb = product_detail_kb(cat_key, item_name, page, available, item_type)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("not_found:"))
async def not_found(call: CallbackQuery):
    await call.answer(
        f"Напишите нам: {SUPPORT_CONTACT}",
        show_alert=True
    )


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()
