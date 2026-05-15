import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db, init_discount_tables, init_login_tables
from handlers import (
    start, catalog, profile, support, admin, balance,
    purchases, referral, orders, queue, admin_queue,
    discount, reviews, login_flow
)
from handlers.scheduler import scheduler_loop
from middlewares.maintenance import MaintenanceMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    await init_db()
    await init_discount_tables()
    await init_login_tables()

    dp.message.middleware(MaintenanceMiddleware())
    dp.callback_query.middleware(MaintenanceMiddleware())

    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(profile.router)
    dp.include_router(support.router)
    dp.include_router(balance.router)
    dp.include_router(purchases.router)
    dp.include_router(referral.router)
    dp.include_router(orders.router)
    dp.include_router(queue.router)
    dp.include_router(discount.router)
    dp.include_router(reviews.router)
    dp.include_router(login_flow.router)
    dp.include_router(admin_queue.router)
    dp.include_router(admin.router)

    # Запускаем планировщик параллельно с ботом
    asyncio.create_task(scheduler_loop(bot))

    logger.info("✅ Bot started — Vorache Store")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
