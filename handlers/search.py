"""
Handler de busca de filmes e séries — com limpeza automática de mensagens antigas
e filtro de disponibilidade nos players WarezCDN / SuperflixAPI.
"""

import logging
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from services.tmdb import tmdb
from services.players import filter_available
from keyboards import search_result_keyboard
from messages import format_no_results, esc
from message_tracker import track_message, delete_old_search_messages

logger = logging.getLogger("CinemaBot.search")

_search_cache: dict[int, list] = {}
_trending_cache: dict[int, dict] = {}


def get_user_results(user_id: int) -> list:
    return _search_cache.get(user_id, [])


def set_user_results(user_id: int, results: list):
    _search_cache[user_id] = results


def get_user_trending(user_id: int, media_type: str) -> list:
    return _trending_cache.get(user_id, {}).get(media_type, [])


def set_user_trending(user_id: int, media_type: str, results: list):
    _trending_cache.setdefault(user_id, {})[media_type] = results


def register_search_handler(app: Client):

    @app.on_message(filters.text & filters.private & ~filters.command(["start", "buscar", "populares", "series", "trending"]))
    async def search_by_text(client: Client, message: Message):
        query = message.text.strip()
        if not query or len(query) < 2:
            return
        await _execute_search(client, message, query)

    @app.on_message(filters.command("buscar") & filters.private)
    async def search_by_command(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("❓ Use: /buscar Nome do Filme", parse_mode=enums.ParseMode.DISABLED)
            return
        await _execute_search(client, message, parts[1].strip())

    @app.on_message(filters.command("populares") & filters.private)
    async def cmd_populares(client: Client, message: Message):
        await _send_trending(client, message, "movie")

    @app.on_message(filters.command("series") & filters.private)
    async def cmd_series(client: Client, message: Message):
        await _send_trending(client, message, "tv")

    @app.on_message(filters.command("trending") & filters.private)
    async def cmd_trending(client: Client, message: Message):
        await _send_trending(client, message, "all")


async def _execute_search(client: Client, message: Message, query: str):
    user_id = message.from_user.id
    logger.info("Busca de '%s' pelo usuário %s", query, user_id)

    await delete_old_search_messages(client, user_id)
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    results = await tmdb.search(query, page=1)

    if not results:
        sent = await message.reply(
            format_no_results(query),
            parse_mode=enums.ParseMode.DISABLED,
        )
        track_message(user_id, message.chat.id, sent.id)
        return

    available = await filter_available(results)

    if not available:
        sent = await message.reply(
            f"🔍 Busca por {query} não encontrou títulos disponíveis nos players no momento.\n"
            "Tente outro título ou aguarde alguns instantes.",
            parse_mode=enums.ParseMode.DISABLED,
        )
        track_message(user_id, message.chat.id, sent.id)
        return

    set_user_results(user_id, available)

    lines = [f"🔍 Resultados para: {query}\n"]
    for i, r in enumerate(available, 1):
        emoji = "📺" if r.is_series else "🎬"
        lines.append(f"{i}. {emoji} {r.title} ({r.release_year}) — ⭐ {r.vote_average:.1f}")
    lines.append("\nToque em um título para ver os detalhes")

    sent = await message.reply(
        "\n".join(lines),
        parse_mode=enums.ParseMode.DISABLED,
        reply_markup=search_result_keyboard(available),
    )
    track_message(user_id, message.chat.id, sent.id)


async def _send_trending(client: Client, message: Message, media_type: str):
    from keyboards import trending_keyboard
    from messages import format_trending_header

    user_id = message.from_user.id
    logger.info("Trending '%s' para usuário %s", media_type, user_id)

    await delete_old_search_messages(client, user_id)
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    results = await tmdb.get_trending(media_type, count=20)
    if not results:
        sent = await message.reply(
            "❌ Não foi possível carregar os dados. Tente novamente.",
            parse_mode=enums.ParseMode.DISABLED,
        )
        track_message(user_id, message.chat.id, sent.id)
        return

    available = await filter_available(results, max_concurrent=6)
    if not available:
        sent = await message.reply(
            "😕 Nenhum título disponível nos players agora. Tente mais tarde.",
            parse_mode=enums.ParseMode.DISABLED,
        )
        track_message(user_id, message.chat.id, sent.id)
        return

    set_user_trending(user_id, media_type, available)

    sent = await message.reply(
        format_trending_header(media_type),
        parse_mode=enums.ParseMode.DISABLED,
        reply_markup=trending_keyboard(available, media_type, page=1),
    )
    track_message(user_id, message.chat.id, sent.id)
