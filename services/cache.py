"""
Sistema de cache SQLite com TTL para resultados da API TMDB.

- Chave → valor serializado em JSON
- TTL padrão: 3600 segundos (1 hora)
- Limpeza automática de entradas expiradas na inicialização
- Thread-safe via asyncio.Lock (bot roda em thread única)
"""

from __future__ import annotations

import asyncio
import json
import logging
import pickle
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("CinemaBot.cache")

# Arquivo do banco de dados — criado na pasta do bot
_DB_PATH = Path(__file__).parent.parent / "cache.db"

# TTLs em segundos
TTL_SEARCH    = 3_600   # buscas por texto: 1 hora
TTL_DETAILS   = 7_200   # detalhes de filme/série: 2 horas
TTL_TRENDING  = 1_800   # trending: 30 minutos (muda com mais frequência)
TTL_SEASONS   = 86_400  # temporadas: 24 horas (dados raramente mudam)
TTL_EPISODES  = 86_400  # episódios: 24 horas


class CacheService:
    """Cache persistente baseado em SQLite."""

    def __init__(self, db_path: Path = _DB_PATH):
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    # ── Ciclo de vida ────────────────────────────────────────

    def init(self) -> None:
        """Inicializa o banco e limpa entradas expiradas."""
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")   # melhor performance
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key       TEXT PRIMARY KEY,
                value     BLOB    NOT NULL,
                expires_at REAL   NOT NULL
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
        self._conn.commit()
        self._purge_expired()
        logger.info("✅ Cache SQLite iniciado em %s", self._db_path)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── API pública (async) ──────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
        """Retorna o valor cacheado ou None se não existir / expirado."""
        async with self._lock:
            return self._get_sync(key)

    async def set(self, key: str, value: Any, ttl: int = TTL_SEARCH) -> None:
        """Armazena um valor com TTL em segundos."""
        async with self._lock:
            self._set_sync(key, value, ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            if self._conn:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()

    async def clear_all(self) -> int:
        """Apaga todo o cache. Retorna o número de entradas removidas."""
        async with self._lock:
            if not self._conn:
                return 0
            cur = self._conn.execute("DELETE FROM cache")
            self._conn.commit()
            count = cur.rowcount
            logger.info("Cache limpo: %d entradas removidas", count)
            return count

    async def stats(self) -> dict:
        """Retorna estatísticas do cache para o painel admin."""
        async with self._lock:
            if not self._conn:
                return {}
            now = time.time()
            total = self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            valid = self._conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at > ?", (now,)
            ).fetchone()[0]
            expired = total - valid
            size_kb = self._db_path.stat().st_size / 1024 if self._db_path.exists() else 0
            return {
                "total": total,
                "valid": valid,
                "expired": expired,
                "size_kb": round(size_kb, 1),
            }

    # ── Helpers internos (síncronos) ─────────────────────────

    def _get_sync(self, key: str) -> Optional[Any]:
        if not self._conn:
            return None
        row = self._conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return None
        value_blob, expires_at = row
        if time.time() > expires_at:
            # Entrada expirada — remove e retorna None
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
            return None
        try:
            return pickle.loads(value_blob)
        except Exception as exc:
            logger.warning("Erro ao desserializar cache key=%s: %s", key, exc)
            return None

    def _set_sync(self, key: str, value: Any, ttl: int) -> None:
        if not self._conn:
            return
        try:
            blob = pickle.dumps(value)
        except Exception as exc:
            logger.warning("Erro ao serializar cache key=%s: %s", key, exc)
            return
        expires_at = time.time() + ttl
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, blob, expires_at),
        )
        self._conn.commit()

    def _purge_expired(self) -> None:
        if not self._conn:
            return
        cur = self._conn.execute(
            "DELETE FROM cache WHERE expires_at <= ?", (time.time(),)
        )
        self._conn.commit()
        if cur.rowcount:
            logger.info("Cache: %d entradas expiradas removidas na inicialização", cur.rowcount)


# Instância global — importada por toda a aplicação
cache = CacheService()
