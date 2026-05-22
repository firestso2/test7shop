from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_all_queue_items, get_pending_queue_by_item,
    complete_queue_item, get_all_admin_ids
)
from keyboards import back_btn
from utils import fmt_date

router = Router()


async def is_admin(uid: int) -> bool:
    return uid in await get_all_admin_ids()


@router.callback_query(F.data == "adm:queue")
async def adm_queue_main(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return

    items = await get_all_queue_items()
    b = InlineKeyboardBuilder()
    b.button(text="📋 Все заказы (по дате)",  callback_data="adm:queue_all")
    b.button(text="🏦 По сервису",             callback_data="adm:queue_by_item")
    b.button(text="◀️ Назад",                  callback_data="adm:main")
    b.adjust(1)

    text = (
        f"📋 <b>Очередь верификации</b>\n\n"
        f"⏳ Ожидают выполнения: <b>{len(items)}</b>"
    )
    try:
        await call.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm:queue_all")
async def adm_queue_all(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        return

    items = await get_all_queue_items()
    if not items:
        await call.message.edit_text(
            "✅ Очередь пуста.",
            reply_markup=back_btn("adm:queue")
        )
        await call.answer()
        return

    rows = []
    for it in items:
        uname = f"@{it['username']}" if it["username"] else f"ID:{it['user_id']}"
        rows.append([InlineKeyboardButton(
            text=f"#{it['order_num']} | {it['item_name']} | {uname}",
            callback_data=f"adm:queue_do:{it['id']}:{it['user_id']}:{it['order_num']}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm:queue")])

    try:
        await call.message.edit_text(
            f"📋 <b>Все заказы ({len(items)} шт.)</b>\n\nНажмите для выполнения:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data == "adm:queue_by_item")
async def adm_queue_by_item(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        return

    items = await get_all_queue_items()
    by_item: dict = {}
    for it in items:
        by_item[it["item_name"]] = by_item.get(it["item_name"], 0) + 1

    if not by_item:
        await call.message.edit_text(
            "✅ Очередь пуста.",
            reply_markup=back_btn("adm:queue")
        )
        await call.answer()
        return

    rows = []
    for name, cnt in sorted(by_item.items(), key=lambda x: -x[1]):
        rows.append([InlineKeyboardButton(
            text=f"🏦 {name} — {cnt} шт.",
            callback_data=f"adm:queue_item:{name}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm:queue")])

    try:
        await call.message.edit_text(
            "🏦 <b>Выберите сервис:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("adm:queue_item:"))
async def adm_queue_item_list(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        return

    item_name = call.data.split(":", 2)[2]
    items = await get_pending_queue_by_item(item_name)

    if not items:
        await call.answer("Очередь по этому сервису пуста.", show_alert=True)
        return

    rows = []
    for it in items:
        uname = f"@{it['username']}" if it["username"] else f"ID:{it['user_id']}"
        rows.append([InlineKeyboardButton(
            text=f"#{it['order_num']} | {uname} | {fmt_date(it['created_at'])}",
            callback_data=f"adm:queue_do:{it['id']}:{it['user_id']}:{it['order_num']}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm:queue_by_item")])

    try:
        await call.message.edit_text(
            f"🏦 <b>{item_name}</b> — {len(items)} заказов:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("adm:queue_do:"))
async def adm_queue_do(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        return

    parts = call.data.split(":")
    queue_id  = int(parts[2])
    user_id   = int(parts[3])
    order_num = int(parts[4])

    await complete_queue_item(queue_id)

    # Уведомляем пользователя
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        review_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✍️ Оставить отзыв",
                url="https://t.me/rewiews_vorache777"
            )]
        ])
        await bot.send_message(
            user_id,
            f"✅ <b>Верификация по заказу #{order_num} выполнена!</b>\n\n"
            f"Если есть вопросы — обратитесь в поддержку.\n\n"
            f"Будем рады вашему отзыву 👇\n"
            f"Формат: <code>+реп @vorache777, верифнул [сервис]...</code> + скрин\n"
            f"За отзыв — купон <b>10%</b> на 3 покупки 🎁",
            reply_markup=review_kb,
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.message.edit_text(
        f"✅ Заказ <b>#{order_num}</b> выполнен.\n"
        f"Пользователь <code>{user_id}</code> уведомлён.",
        reply_markup=back_btn("adm:queue"),
        parse_mode="HTML"
    )
    await call.answer("✅ Выполнено")
