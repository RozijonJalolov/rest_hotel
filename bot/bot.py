import asyncio
import logging
import os
import sys
import traceback
from typing import Set
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramUnauthorizedError,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent
from dotenv import load_dotenv

from api_client import HotelApiClient
from handlers import admin, booking, common, my_bookings, rooms
from texts import MSG_GLOBAL_ERROR

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("hotel_bot")


def parse_admin_ids(raw_ids: str) -> Set[int]:
    """Parses comma-separated ADMIN_IDS into a set of integers."""
    result: Set[int] = set()
    for part in raw_ids.split(","):
        cleaned = part.strip()
        if cleaned.isdigit():
            result.add(int(cleaned))
    return result


async def main():
    # Load environment variables
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN") or "9134381937:AAFRc5qcuIzAURuBg5PifRJRUl2crzjXyZk"
    api_base_url = os.getenv("API_BASE_URL") or "http://127.0.0.1:8000"
    api_key = os.getenv("API_KEY") or "hotel_secret_api_key_123"
    raw_admin_ids = os.getenv("ADMIN_IDS", "")

    if not bot_token:
        logger.critical("BOT_TOKEN environment variable is missing!")
        sys.exit(1)

    if not api_key:
        logger.critical("API_KEY environment variable is missing!")
        sys.exit(1)

    admin_ids = parse_admin_ids(raw_admin_ids)
    logger.info("Loaded %d admin IDs (IDs not logged for privacy)", len(admin_ids))

    # Initialize Hotel API client
    api_client = HotelApiClient(base_url=api_base_url, api_key=api_key)

    # Initialize Telegram Bot and Dispatcher
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers (order matters: specific -> general)
    dp.include_router(admin.router)
    dp.include_router(rooms.router)
    dp.include_router(booking.router)
    dp.include_router(my_bookings.router)
    dp.include_router(common.router)

    # Global error handler
    @dp.error()
    async def global_error_handler(event: ErrorEvent):
        exc = event.exception
        logger.error(
            "Global unhandled error: %s\n%s",
            exc,
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )

        if isinstance(exc, TelegramForbiddenError):
            logger.info("User blocked the bot; skipping response.")
            return

        if isinstance(exc, TelegramAPIError):
            logger.warning("Telegram API error occurred: %s", exc)
            return

        # Attempt to inform the user gracefully
        try:
            update = event.update
            if update.message:
                await update.message.answer(MSG_GLOBAL_ERROR)
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.answer(MSG_GLOBAL_ERROR)
        except Exception as send_err:
            logger.warning("Could not deliver global error message to user: %s", send_err)

    logger.info("Starting hotel booking bot (long-polling)...")
    try:
        await dp.start_polling(
            bot,
            api_client=api_client,
            admin_ids=admin_ids,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("Closing bot session and API client...")
        await api_client.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
