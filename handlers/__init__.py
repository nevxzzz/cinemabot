"""
Registro centralizado de todos os handlers do bot
"""

from pyrogram import Client
from handlers.start import register_start_handler
from handlers.search import register_search_handler
from handlers.callbacks import register_callback_handler
from handlers.admin import register_admin_handlers


def register_handlers(app: Client):
    register_start_handler(app)
    register_search_handler(app)
    register_callback_handler(app)
    register_admin_handlers(app)
