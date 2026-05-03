"""
Handler do comando /start
"""

import logging
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from keyboards import start_keyboard
from messages import WELCOME_TEXT

logger = logging.getLogger("CinemaBot.start")


def register_start_handler(app: Client):

    @app.on_message(filters.command("start") & filters.private)
    async def start(client: Client, message: Message):
        logger.info("Start de uid=%s", message.from_user.id)
        await message.reply(
            WELCOME_TEXT,
            parse_mode=enums.ParseMode.DISABLED,
            reply_markup=start_keyboard(),
        )
