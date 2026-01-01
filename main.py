"""Main bot file."""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
from database.base import init_db
from handlers.start_handler import router as start_router
from handlers.profile_handler import router as profile_router
from handlers.service_handler import router as service_router
from handlers.request_handler import router as request_router
from handlers.browse_handler import router as browse_router
from handlers.records_handler import router as records_router
from handlers.admin_handler import router as admin_router
from handlers.common import DatabaseMiddleware, UserMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the bot."""
    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")
    
    # Initialize bot and dispatcher
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    
    # Register routers
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(service_router)
    dp.include_router(request_router)
    dp.include_router(browse_router)
    dp.include_router(records_router)
    dp.include_router(admin_router)
    
    logger.info("Bot starting...")
    
    # Start polling
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)

