"""
Handler de callbacks (botões inline)
Gerencia: detalhes de mídia, temporadas, episódios, trending, navegação
"""

import logging
from pyrogram import Client, enums
from pyrogram.types import CallbackQuery, InputMediaPhoto

from services.tmdb import tmdb
from keyboards import (
    start_keyboard,
    media_detail_keyboard,
    series_detail_keyboard,
    seasons_keyboard,
    episodes_keyboard,
    ep_detail_keyboard,
    trending_keyboard,
    back_to_start_keyboard,
    search_result_keyboard,
)
from messages import (
    WELCOME_TEXT,
    HELP_TEXT,
    esc,
    format_media_caption,
    format_seasons_list,
    format_episodes_list,
    format_episode_detail,
    format_trending_header,
)
from handlers.search import (
    get_user_results,
    get_user_trending,
    set_user_trending,
)

logger = logging.getLogger("CinemaBot.callbacks")

_ep_cache: dict[int, dict] = {}
_tv_cache: dict[int, dict] = {}


def register_callback_handler(app: Client):

    @app.on_callback_query()
    async def handle_callback(client: Client, query: CallbackQuery):
        data = query.data
        uid  = query.from_user.id
        logger.info("Callback '%s' uid=%s", data, uid)

        if data == "noop":
            await query.answer()
            return

        if data == "start":
            try:
                await query.message.edit_caption(
                    caption=WELCOME_TEXT,
                    parse_mode=enums.ParseMode.DISABLED,
                    reply_markup=start_keyboard(),
                )
            except Exception:
                await query.message.edit_text(
                    text=WELCOME_TEXT,
                    parse_mode=enums.ParseMode.DISABLED,
                    reply_markup=start_keyboard(),
                )

        elif data == "help":
            await _edit_text_or_caption(query, HELP_TEXT, back_to_start_keyboard())

        elif data == "back_results":
            results = get_user_results(uid)
            if not results:
                await query.answer("Sessão expirada. Faça uma nova busca.", show_alert=True)
                return
            lines = ["🔍 Seus resultados:\n"]
            for i, r in enumerate(results, 1):
                emoji = "📺" if r.is_series else "🎬"
                lines.append(f"{i}. {emoji} {r.title} ({r.release_year}) — ⭐ {r.vote_average:.1f}")
            await _edit_text_or_caption(query, "\n".join(lines), search_result_keyboard(results))

        elif data.startswith("detail:"):
            _, media_type, media_id_str = data.split(":")
            media_id = int(media_id_str)
            await query.answer("Carregando…")

            if media_type == "movie":
                media = await tmdb.get_movie_details(media_id)
                keyboard = media_detail_keyboard(media_id, "movie", media.title) if media else back_to_start_keyboard()
            else:
                media = await tmdb.get_tv_details(media_id)
                if media:
                    _tv_cache.setdefault(uid, {})[media_id] = media
                keyboard = series_detail_keyboard(media_id, media.title) if media else back_to_start_keyboard()

            if not media:
                await query.answer("❌ Erro ao carregar detalhes.", show_alert=True)
                return

            caption = format_media_caption(media)
            await _edit_media_or_caption(query, media.poster_url, caption, keyboard)

        elif data.startswith("seasons:"):
            tv_id = int(data.split(":")[1])
            await query.answer("Buscando temporadas…")

            seasons = await tmdb.get_seasons(tv_id)
            if not seasons:
                await query.answer("❌ Temporadas não encontradas.", show_alert=True)
                return

            tv = _tv_cache.get(uid, {}).get(tv_id) or await tmdb.get_tv_details(tv_id)
            title = tv.title if tv else "Série"

            caption = format_seasons_list(title, seasons)
            await _edit_text_or_caption(query, caption, seasons_keyboard(tv_id, seasons))

        elif data.startswith("eps:"):
            _, tv_id_str, season_str = data.split(":")
            tv_id, season_number = int(tv_id_str), int(season_str)
            await query.answer("Carregando episódios…")

            cache_key = (tv_id, season_number)
            episodes = _ep_cache.get(uid, {}).get(cache_key)
            if not episodes:
                episodes = await tmdb.get_episodes(tv_id, season_number)
                if not episodes:
                    await query.answer("❌ Episódios não encontrados.", show_alert=True)
                    return
                _ep_cache.setdefault(uid, {})[cache_key] = episodes

            tv = _tv_cache.get(uid, {}).get(tv_id) or await tmdb.get_tv_details(tv_id)
            series_title = tv.title if tv else "Série"

            seasons = await tmdb.get_seasons(tv_id)
            season_obj = next((s for s in seasons if s.season_number == season_number), None)
            season_name = season_obj.name if season_obj else f"Temporada {season_number}"

            caption = format_episodes_list(series_title, season_name, season_number, episodes)
            await _edit_text_or_caption(
                query, caption,
                episodes_keyboard(tv_id, season_number, episodes, page=1)
            )

        elif data.startswith("eps_page:"):
            _, tv_id_str, season_str, page_str = data.split(":")
            tv_id, season_number, page = int(tv_id_str), int(season_str), int(page_str)
            await query.answer()

            cache_key = (tv_id, season_number)
            episodes = _ep_cache.get(uid, {}).get(cache_key, [])
            if not episodes:
                await query.answer("Sessão expirada. Abra a temporada novamente.", show_alert=True)
                return

            await query.message.edit_reply_markup(
                reply_markup=episodes_keyboard(tv_id, season_number, episodes, page=page)
            )

        elif data.startswith("ep_detail:"):
            _, tv_id_str, season_str, ep_str = data.split(":")
            tv_id, season_number, ep_number = int(tv_id_str), int(season_str), int(ep_str)
            await query.answer("Carregando episódio…")

            cache_key = (tv_id, season_number)
            episodes = _ep_cache.get(uid, {}).get(cache_key, [])
            ep = next((e for e in episodes if e.episode_number == ep_number), None)

            if not ep:
                await query.answer("❌ Episódio não encontrado.", show_alert=True)
                return

            tv = _tv_cache.get(uid, {}).get(tv_id) or await tmdb.get_tv_details(tv_id)
            series_title = tv.title if tv else "Série"

            caption = format_episode_detail(series_title, season_number, ep)
            keyboard = ep_detail_keyboard(tv_id, season_number, ep_number, series_title)

            if ep.still_url:
                await _edit_media_or_caption(query, ep.still_url, caption, keyboard)
            else:
                await _edit_text_or_caption(query, caption, keyboard)

        elif data.startswith("trending:"):
            media_type = data.split(":")[1]
            await query.answer("Carregando…")

            results = get_user_trending(uid, media_type)
            if not results:
                results = await tmdb.get_trending(media_type)
                if not results:
                    await query.answer("❌ Não foi possível carregar.", show_alert=True)
                    return
                set_user_trending(uid, media_type, results)

            caption = format_trending_header(media_type)
            await _edit_text_or_caption(
                query, caption,
                trending_keyboard(results, media_type, page=1)
            )

        elif data.startswith("trending_page:"):
            _, media_type, page_str = data.split(":")
            page = int(page_str)
            await query.answer()

            results = get_user_trending(uid, media_type)
            if not results:
                await query.answer("Sessão expirada. Abra o trending novamente.", show_alert=True)
                return

            await query.message.edit_reply_markup(
                reply_markup=trending_keyboard(results, media_type, page=page)
            )

        else:
            await query.answer("Ação desconhecida.", show_alert=True)


async def _edit_text_or_caption(query: CallbackQuery, text: str, keyboard) -> None:
    try:
        await query.message.edit_caption(
            caption=text,
            parse_mode=enums.ParseMode.DISABLED,
            reply_markup=keyboard,
        )
    except Exception:
        try:
            await query.message.edit_text(
                text=text,
                parse_mode=enums.ParseMode.DISABLED,
                reply_markup=keyboard,
            )
        except Exception as exc:
            logger.warning("Falha ao editar mensagem: %s", exc)


async def _edit_media_or_caption(
    query: CallbackQuery,
    photo_url: str | None,
    caption: str,
    keyboard,
) -> None:
    if photo_url:
        try:
            await query.message.edit_media(
                media=InputMediaPhoto(
                    media=photo_url,
                    caption=caption,
                    parse_mode=enums.ParseMode.DISABLED,
                ),
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    await _edit_text_or_caption(query, caption, keyboard)
