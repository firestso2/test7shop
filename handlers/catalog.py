from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from products import get_all_items_with_stock
from keyboards import catalog_kb, products_kb, product_detail_kb
from config import SUPPORT_CONTACT

router = Router()

CAT_DESC = {
    "banks":      "🏦 <b>Б@нки ~ К0шельки</b>\n\n✅ Товар выдаётся в формате: номер, пароль, ключ TOTP\n✅ Гарантия на вход — 6 часов\n✅ М0ментальная выдача после оплаты\n✅ Верификацию выполняете самостоятельно по мануалу",
    "crypto":     "💹 <b>Кр1пт0Б1ржи ~ TG С€рвисы</b>\n\nВерификация аккаунта на криптобирже.\nПроцедура выполняется путём авторизации и последующего верифа на платформе.",
    "manuals":    "📖 <b>М@нyалы</b>\n\nПодробные инструкции по работе с платформами.",
    "bookmakers": "🎰 <b>Бyкм€k€рk1</b>\n\nВерификация аккаунта на букмекерской платформе.",
}

@router.message(F.text == "🛒 К@т@л0г")
async def catalog_menu(message: Message):
    await message.answer("📂 <b>К@т@л0г т0в@р0в</b>\n\nВыберите к@тег0рию:", reply_markup=catalog_kb(), parse_mode="HTML")

@router.callback_query(F.data == "back:catalog")
async def back_catalog(call: CallbackQuery):
    await call.message.edit_text("📂 <b>К@т@л0г т0в@р0в</b>\n\nВыберите к@тег0рию:", reply_markup=catalog_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("cat:"))
async def show_category(call: CallbackQuery):
    await _show_page(call, call.data.split(":")[1], 0)

@router.callback_query(F.data.startswith("cat_page:"))
async def show_page(call: CallbackQuery):
    _, cat_key, page = call.data.split(":")
    await _show_page(call, cat_key, int(page))

async def _show_page(call, cat_key, page):
    items = get_all_items_with_stock(cat_key)
    desc = CAT_DESC.get(cat_key, "Описание отсутствует.")
    try:
        await call.message.edit_text(desc, reply_markup=products_kb(items, cat_key, page), parse_mode="HTML")
    except:
        await call.message.answer(desc, reply_markup=products_kb(items, cat_key, page), parse_mode="HTML")
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
    stock_txt = f"✅ В н@личии: {item['stock']} шт." if item["stock"] > 0 else "❌ Н€т в н@личии"
    manual_txt = f"\n\n📋 <b>М@ну@л:</b>\n{item['manual']}" if item["manual"] else ""
    text = f"🏷 <b>{item_name}</b>\n\n{item['description']}{manual_txt}\n\n💲 <b>Цен@:</b> ${item['price']}\n{stock_txt}"
    kb = product_detail_kb(cat_key, item_name, page, item["stock"] > 0)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("not_found:"))
async def not_found(call: CallbackQuery):
    await call.answer(f"Напишите в поддержку: {SUPPORT_CONTACT}", show_alert=True)

@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()
