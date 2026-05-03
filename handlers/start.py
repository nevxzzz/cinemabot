"""
Handler do comando /start — registra usuários no banco de dados.
"""

import logging
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from keyboards import start_keyboard
from messages import WELCOME_TEXT
from services.database import user_db

logger = logging.getLogger("CinemaBot.start")


def register_start_handler(app: Client):

    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client: Client, message: Message):
        user = message.from_user
        logger.info("Usuário %s (%s) usou /start", user.id, user.first_name)

        # Registra ou atualiza o usuário no banco
        is_new = await user_db.register(
            user_id=user.id,
            first_name=user.first_name or "",
            username=user.username,
            last_name=user.last_name,
        )
        if is_new:
            logger.info("Novo usuário registrado: id=%d name=%s", user.id, user.first_name)

        await message.reply_photo(
            photo="https://image.tmdb.org/t/p/original/wwemzKWzjKYJFfCeiB57q3r4Bcm.png",
            caption=WELCOME_TEXT,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=start_keyboard(),
        )
