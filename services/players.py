"""
Serviço de players — WarezCDN e SuperflixAPI.

Responsabilidades:
  - Construir URLs de embed para filmes e episódios
  - Verificar assincronamente se o conteúdo está disponível
  - Cachear resultados para evitar verificações repetidas

Padrão de URL usado (confirme nos sites se mudar):
  Filme  → /filme/{tmdb_id}
  Série  → /serie/{tmdb_id}              (T1E1 padrão)
  Episódio → /serie/{tmdb_id}/{season}/{episode}
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from services.cache import cache

logger = logging.getLogger("CinemaBot.players")

# ── TTL para cache de disponibilidade ──────────────────────────────
TTL_AVAILABILITY = 14_400   # 4 horas

# ── URLs base dos players ───────────────────────────────────────────
WAREZCDN_BASE  = "https://warezcdn.site"
SUPERFLIX_BASE = "https://superflixapi.online"

# ── Headers para simular requisição de browser ─────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; SM-S901B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.144 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    "Referer": "https://t.me/",
}


# ─────────────────────────── URL Builders ──────────────────────────

def warezcdn_url(
    tmdb_id: int,
    media_type: str,
    season: int = 0,
    episode: int = 0,
) -> str:
    """Retorna a URL de embed do WarezCDN."""
    tipo = "serie" if media_type == "tv" else "filme"
    url  = f"{WAREZCDN_BASE}/{tipo}/{tmdb_id}"
    if media_type == "tv" and season and episode:
        url += f"/{season}/{episode}"
    return url


def superflix_url(
    tmdb_id: int,
    media_type: str,
    season: int = 0,
    episode: int = 0,
) -> str:
    """Retorna a URL de embed do SuperflixAPI."""
    tipo = "serie" if media_type == "tv" else "filme"
    url  = f"{SUPERFLIX_BASE}/{tipo}/{tmdb_id}"
    if media_type == "tv" and season and episode:
        url += f"/{season}/{episode}"
    return url


# ──────────────────────── Availability Check ───────────────────────

async def _check_url(client: httpx.AsyncClient, url: str) -> bool:
    """
    Verifica se a URL retorna resposta válida (não 404/410).
    Tenta HEAD primeiro; se o servidor não suportar, faz GET parcial.
    """
    try:
        resp = await client.head(url, follow_redirects=True, timeout=5.0)
        if resp.status_code not in (404, 410, 400):
            return True
    except Exception:
        pass

    try:
        resp = await client.get(
            url,
            follow_redirects=True,
            timeout=6.0,
            headers={**_HEADERS, "Range": "bytes=0-0"},
        )
        return resp.status_code not in (404, 410, 400)
    except Exception:
        return False


async def check_availability(
    tmdb_id: int,
    media_type: str,
) -> tuple[bool, bool]:
    """
    Verifica disponibilidade em WarezCDN e SuperflixAPI em paralelo.
    Retorna (warezcdn_ok, superflix_ok).
    Resultado é cacheado por TTL_AVAILABILITY segundos.
    """
    cache_key = f"avail:{media_type}:{tmdb_id}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    url_warez  = warezcdn_url(tmdb_id, media_type)
    url_super  = superflix_url(tmdb_id, media_type)

    async with httpx.AsyncClient(headers=_HEADERS, timeout=7.0) as client:
        warez_ok, super_ok = await asyncio.gather(
            _check_url(client, url_warez),
            _check_url(client, url_super),
        )

    result: tuple[bool, bool] = (bool(warez_ok), bool(super_ok))
    await cache.set(cache_key, result, TTL_AVAILABILITY)
    logger.debug(
        "Disponibilidade %s:%d → warez=%s superflix=%s",
        media_type, tmdb_id, warez_ok, super_ok,
    )
    return result


async def filter_available(results: list, max_concurrent: int = 5) -> list:
    """
    Recebe uma lista de MediaResult e retorna apenas os que estão
    disponíveis em pelo menos um dos players.

    Checagens são feitas em paralelo com semáforo para não sobrecarregar.
    """
    if not results:
        return []

    sem = asyncio.Semaphore(max_concurrent)

    async def _check_one(r):
        async with sem:
            warez, superflix = await check_availability(r.id, r.media_type)
            return r if (warez or superflix) else None

    checked = await asyncio.gather(*[_check_one(r) for r in results])
    available = [r for r in checked if r is not None]
    logger.info(
        "Filtro de disponibilidade: %d/%d disponíveis",
        len(available), len(results),
    )
    return available


def best_player_url(
    tmdb_id: int,
    media_type: str,
    warez_ok: bool,
    super_ok: bool,
    season: int = 0,
    episode: int = 0,
) -> str:
    """Retorna a URL do melhor player disponível (WarezCDN tem prioridade)."""
    if warez_ok:
        return warezcdn_url(tmdb_id, media_type, season, episode)
    return superflix_url(tmdb_id, media_type, season, episode)
