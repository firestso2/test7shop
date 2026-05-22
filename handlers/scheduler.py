import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from database import get_all_admin_ids, DB_PATH
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

BACKUP_INTERVAL_HOURS = 3


async def send_backup(bot: Bot):
    """Отправляет бэкап БД всем админам"""
    try:
        with open(DB_PATH, "rb") as f:
            data = f.read()
        fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        admin_ids = await get_all_admin_ids()
        for aid in admin_ids:
            try:
                from aiogram.types import BufferedInputFile
                await bot.send_document(
                    aid,
                    BufferedInputFile(data, filename=fname),
                    caption=f"💾 <b>Авт0бэкап БД</b>\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Backup send error to {aid}: {e}")
        logger.info(f"Backup sent: {fname}")
    except Exception as e:
        logger.error(f"Backup error: {e}")


async def scheduler_loop(bot: Bot):
    """Основной цикл планировщика — запускается при старте бота"""
    logger.info(f"Scheduler started — backup every {BACKUP_INTERVAL_HOURS}h")
    while True:
        await asyncio.sleep(BACKUP_INTERVAL_HOURS * 3600)
        logger.info("Running scheduled backup...")
        await send_backup(bot)
