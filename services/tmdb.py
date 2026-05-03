"""
Serviço TMDB — toda a comunicação com a API do The Movie Database
Cache SQLite integrado para economizar quota da API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from config import settings
from services.cache import cache, TTL_SEARCH, TTL_DETAILS, TTL_TRENDING, TTL_SEASONS, TTL_EPISODES

logger = logging.getLogger("CinemaBot.tmdb")


# ─────────────────────────── Data Models ────────────────────────────

@dataclass
class MediaResult:
    id: int
    title: str
    overview: str
    release_year: str
    vote_average: float
    poster_url: Optional[str]
    media_type: str
    genres: list[str] = field(default_factory=list)
    total_seasons: Optional[int] = None
    total_episodes: Optional[int] = None

    @property
    def is_series(self) -> bool:
        return self.media_type == "tv"

    @property
    def rating_stars(self) -> str:
        stars = round(self.vote_average / 2)
        return "⭐" * stars + "☆" * (5 - stars)

    @property
    def media_emoji(self) -> str:
        return "📺" if self.is_series else "🎬"


@dataclass
class Season:
    season_number: int
    name: str
    episode_count: int
    air_date: str
    overview: str
    poster_url: Optional[str]


@dataclass
class Episode:
    episode_number: int
    name: str
    overview: str
    air_date: str
    runtime: Optional[int]
    vote_average: float
    still_url: Optional[str]


# ─────────────────────────── TMDB Client ────────────────────────────

class TMDBService:
    """Cliente assíncrono para a API do TMDB com cache integrado."""

    def __init__(self):
        self._base_url = settings.TMDB_BASE_URL
        self._params = {
            "api_key": settings.TMDB_API_KEY,
            "language": settings.TMDB_LANGUAGE,
        }

    def _poster(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        return f"{settings.TMDB_IMAGE_BASE}{path}"

    def _year(self, raw: Optional[str]) -> str:
        if raw and len(raw) >= 4:
            return raw[:4]
        return "N/A"

    async def _get(self, endpoint: str, extra: dict | None = None) -> dict:
        params = {**self._params, **(extra or {})}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self._base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def search(self, query: str, page: int = 1) -> list[MediaResult]:
        cache_key = f"search:{query.lower().strip()}:p{page}"
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache HIT — busca '%s'", query)
            return cached

        try:
            data = await self._get("/search/multi", {"query": query, "page": page, "include_adult": False})
        except httpx.HTTPError as exc:
            logger.error("Erro na busca TMDB: %s", exc)
            return []

        results = []
        for item in data.get("results", []):
            media_type = item.get("media_type")
            if media_type not in ("movie", "tv"):
                continue
            title = item.get("title") or item.get("name") or "Sem título"
            release_raw = item.get("release_date") or item.get("first_air_date") or ""
            results.append(MediaResult(
                id=item["id"], title=title,
                overview=item.get("overview") or "Sinopse não disponível.",
                release_year=self._year(release_raw),
                vote_average=item.get("vote_average", 0.0),
                poster_url=self._poster(item.get("poster_path")),
                media_type=media_type,
            ))

        results = results[:5]
        await cache.set(cache_key, results, TTL_SEARCH)
        return results

    async def get_movie_details(self, movie_id: int) -> Optional[MediaResult]:
        cache_key = f"movie:{movie_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._get(f"/movie/{movie_id}", {"append_to_response": "genres"})
        except httpx.HTTPError as exc:
            logger.error("Erro ao buscar detalhes do filme %d: %s", movie_id, exc)
            return None

        genres = [g["name"] for g in data.get("genres", [])]
        result = MediaResult(
            id=data["id"], title=data.get("title", "Sem título"),
            overview=data.get("overview") or "Sinopse não disponível.",
            release_year=self._year(data.get("release_date")),
            vote_average=data.get("vote_average", 0.0),
            poster_url=self._poster(data.get("poster_path")),
            media_type="movie", genres=genres,
        )
        await cache.set(cache_key, result, TTL_DETAILS)
        return result

    async def get_tv_details(self, tv_id: int) -> Optional[MediaResult]:
        cache_key = f"tv:{tv_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._get(f"/tv/{tv_id}", {"append_to_response": "genres"})
        except httpx.HTTPError as exc:
            logger.error("Erro ao buscar detalhes da série %d: %s", tv_id, exc)
            return None

        genres = [g["name"] for g in data.get("genres", [])]
        result = MediaResult(
            id=data["id"], title=data.get("name", "Sem título"),
            overview=data.get("overview") or "Sinopse não disponível.",
            release_year=self._year(data.get("first_air_date")),
            vote_average=data.get("vote_average", 0.0),
            poster_url=self._poster(data.get("poster_path")),
            media_type="tv", genres=genres,
            total_seasons=data.get("number_of_seasons"),
            total_episodes=data.get("number_of_episodes"),
        )
        await cache.set(cache_key, result, TTL_DETAILS)
        return result

    async def get_seasons(self, tv_id: int) -> list[Season]:
        cache_key = f"seasons:{tv_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._get(f"/tv/{tv_id}")
        except httpx.HTTPError as exc:
            logger.error("Erro ao buscar temporadas da série %d: %s", tv_id, exc)
            return []

        seasons = []
        for s in data.get("seasons", []):
            if s.get("season_number", 0) == 0:
                continue
            seasons.append(Season(
                season_number=s["season_number"],
                name=s.get("name", f"Temporada {s['season_number']}"),
                episode_count=s.get("episode_count", 0),
                air_date=self._year(s.get("air_date")),
                overview=s.get("overview") or "",
                poster_url=self._poster(s.get("poster_path")),
            ))
        await cache.set(cache_key, seasons, TTL_SEASONS)
        return seasons

    async def get_episodes(self, tv_id: int, season_number: int) -> list[Episode]:
        cache_key = f"episodes:{tv_id}:{season_number}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._get(f"/tv/{tv_id}/season/{season_number}")
        except httpx.HTTPError as exc:
            logger.error("Erro ao buscar episódios T%d da série %d: %s", season_number, tv_id, exc)
            return []

        episodes = []
        for ep in data.get("episodes", []):
            still_path = ep.get("still_path")
            episodes.append(Episode(
                episode_number=ep.get("episode_number", 0),
                name=ep.get("name") or f"Episódio {ep.get('episode_number', '?')}",
                overview=ep.get("overview") or "Sem sinopse disponível.",
                air_date=self._year(ep.get("air_date")),
                runtime=ep.get("runtime"),
                vote_average=ep.get("vote_average", 0.0),
                still_url=f"https://image.tmdb.org/t/p/w300{still_path}" if still_path else None,
            ))

        await cache.set(cache_key, episodes, TTL_EPISODES)
        return episodes

    async def get_trending(
        self,
        media_type: str = "all",
        time_window: str = "week",
        count: int = 10,
    ) -> list[MediaResult]:
        cache_key = f"trending:{media_type}:{time_window}:n{count}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._get(f"/trending/{media_type}/{time_window}", {"region": "BR"})
        except httpx.HTTPError as exc:
            logger.error("Erro ao buscar trending %s/%s: %s", media_type, time_window, exc)
            return []

        results = []
        for item in data.get("results", []):
            mt = item.get("media_type", media_type)
            if mt not in ("movie", "tv"):
                continue
            title = item.get("title") or item.get("name") or "Sem título"
            release_raw = item.get("release_date") or item.get("first_air_date") or ""
            results.append(MediaResult(
                id=item["id"], title=title,
                overview=item.get("overview") or "Sinopse não disponível.",
                release_year=self._year(release_raw),
                vote_average=item.get("vote_average", 0.0),
                poster_url=self._poster(item.get("poster_path")),
                media_type=mt,
            ))

        results = results[:count]
        await cache.set(cache_key, results, TTL_TRENDING)
        return results


tmdb = TMDBService()
