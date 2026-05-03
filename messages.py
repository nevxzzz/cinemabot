"""
Templates de mensagens — Markdown V1 (parse_mode=MARKDOWN do Pyrogram).

Caracteres especiais no Markdown V1 que precisam de escape com \:
  _ * ` [
Tudo o mais (pontos, parênteses, traços, exclamação) NÃO precisa de escape.
"""

from services.tmdb import MediaResult, Season, Episode


# ─── Escaping helper ────────────────────────────────────────────────

def esc(text: str) -> str:
    """Escapa apenas os caracteres especiais do Markdown V1: _ * ` ["""
    for c in ("_", "*", "`", "["):
        text = text.replace(c, f"\\{c}")
    return text


WELCOME_TEXT = (
    "🎬 *Bem-vindo ao CinemaBot!*\n\n"
    "Seu assistente pessoal de filmes e séries, com informações em português.\n\n"
    "*O que posso fazer por você?*\n"
    "• 🔍 Buscar qualquer filme ou série\n"
    "• 🔥 Ver o que está em alta no Brasil\n"
    "• 📺 Explorar temporadas e episódios\n"
    "• ⭐ Notas, sinopses e muito mais\n\n"
    "_Digite o nome de um filme ou série para começar!_"
)


HELP_TEXT = (
    "ℹ️ *Como usar o CinemaBot*\n\n"
    "*Busca rápida:*\n"
    "Simplesmente envie o nome do filme ou série.\n"
    "Exemplos: `Inception` ou `Breaking Bad`\n\n"
    "*Comandos disponíveis:*\n"
    "• /start — Tela inicial\n"
    "• /buscar [nome] — Busca direta\n"
    "• /populares — Filmes populares agora\n"
    "• /series — Séries em alta no Brasil\n"
    "• /trending — Tudo em alta (filmes + séries)\n\n"
    "*Dicas:*\n"
    "• Para séries, toque em *Ver Temporadas* → depois em uma temporada para ver os episódios\n"
    "• As listas de trending são atualizadas semanalmente\n"
    "• Mensagens antigas de busca são apagadas automaticamente 🧹"
)


def format_media_caption(media: MediaResult) -> str:
    """Formata a legenda completa para um filme ou série."""
    genres_str = " • ".join(media.genres[:3]) if media.genres else "N/A"
    overview = media.overview[:350] + "…" if len(media.overview) > 350 else media.overview

    rating_bar = rating_progress(media.vote_average)
    media_type_label = "Série" if media.is_series else "Filme"

    lines = [
        f"{media.media_emoji} *{esc(media.title)}* ({esc(media.release_year)})",
        "",
        f"🏷️ _{esc(media_type_label)}_ • {esc(genres_str)}",
        "",
        f"⭐ *{media.vote_average:.1f}/10* {rating_bar}",
        "",
        "📝 *Sinopse:*",
        esc(overview),
    ]

    if media.is_series and media.total_seasons:
        s = "s" if media.total_seasons > 1 else ""
        eps = media.total_episodes or "?"
        lines += [
            "",
            f"📺 *{media.total_seasons} temporada{s}* • *{eps} episódios*",
        ]

    lines += ["", "▶️ _Toque em Assistir Online para reproduzir dentro do Telegram._"]
    return "\n".join(lines)


def format_seasons_list(title: str, seasons: list[Season]) -> str:
    lines = [f"📋 *Temporadas de {esc(title)}*\n"]
    for s in seasons:
        lines.append(
            f"*T{s.season_number}* — {esc(s.name)}\n"
            f"📅 {esc(s.air_date)} · {s.episode_count} episódios\n"
        )
    lines.append("_Toque em uma temporada para ver os episódios_")
    return "\n".join(lines)


def format_episodes_list(series_title: str, season_name: str, season_number: int, episodes: list[Episode]) -> str:
    total = len(episodes)
    s = "s" if total != 1 else ""
    lines = [
        f"📺 *{esc(series_title)}*",
        f"📋 *{esc(season_name)}* — {total} episódio{s}",
        "",
        "_Toque em um episódio para ver os detalhes:_",
    ]
    return "\n".join(lines)


def format_episode_detail(series_title: str, season_number: int, ep: Episode) -> str:
    overview = ep.overview[:400] + "…" if len(ep.overview) > 400 else ep.overview
    runtime_str = f"⏱ *{ep.runtime} min*\n" if ep.runtime else ""
    rating_bar = rating_progress(ep.vote_average) if ep.vote_average else ""

    lines = [
        f"📺 *{esc(series_title)}* — T{season_number}E{ep.episode_number:02d}",
        "",
        f"🎬 *{esc(ep.name)}*",
        f"📅 {esc(ep.air_date)}   {runtime_str}",
    ]
    if ep.vote_average:
        lines.append(f"⭐ *{ep.vote_average:.1f}/10* {rating_bar}")
    lines += [
        "", "📝 *Sinopse:*", esc(overview),
        "", "▶️ _Toque em Assistir Episódio para reproduzir dentro do Telegram._"
    ]
    return "\n".join(lines)


def format_trending_header(media_type: str) -> str:
    labels = {
        "movie": ("🎬", "Filmes Populares", "no Brasil esta semana"),
        "tv":    ("📺", "Séries em Alta",   "no Brasil esta semana"),
        "all":   ("🔥", "Tudo em Alta",     "filmes + séries no Brasil"),
    }
    emoji, title, subtitle = labels.get(media_type, ("🔥", "Em Alta", ""))
    return f"{emoji} *{title}*\n_{subtitle}_\n\n_Toque em um título para ver detalhes:_"


def format_no_results(query: str) -> str:
    return (
        f"😕 *Nenhum resultado encontrado para:*\n_{esc(query)}_\n\n"
        "Tente verificar a ortografia ou buscar em inglês."
    )


def rating_progress(score: float) -> str:
    """Barra visual de progresso para a nota (0–10)."""
    filled = round(score / 10 * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"`{bar}`"
