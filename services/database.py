"""
Banco de dados de usuários — registro de quem iniciou o bot.

Tabela `users`:
  - user_id     INTEGER PRIMARY KEY
  - username    TEXT
  - first_name  TEXT
  - last_name   TEXT
  - joined_at   REAL  (unix timestamp)
  - is_blocked  INTEGER (0/1) — usuários que bloquearam o bot

Usado pelo /broadcast para enviar mensagens a todos os usuários.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("CinemaBot.db")

_DB_PATH = Path(__file__).parent.parent / "users.db"


@dataclass
class UserRecord:
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    joined_at: float
    is_blocked: bool = False


class UserDB:
    """Gerencia o banco de dados de usuários do bot."""

    def __init__(self, db_path: Path = _DB_PATH):
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    # ── Ciclo de vida ────────────────────────────────────────

    def init(self) -> None:
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                first_name TEXT    NOT NULL DEFAULT '',
                last_name  TEXT,
                joined_at  REAL    NOT NULL,
                is_blocked INTEGER NOT NULL DEFAULT 0
            )
        """)
        self._conn.commit()
        count = self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        logger.info("✅ UserDB iniciado — %d usuário(s) registrado(s)", count)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── API pública (async) ──────────────────────────────────

    async def register(
        self,
        user_id: int,
        first_name: str,
        username: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> bool:
        """
        Registra ou atualiza um usuário.
        Retorna True se era um usuário novo, False se já existia.
        """
        async with self._lock:
            if not self._conn:
                return False
            existing = self._conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()

            if existing:
                # Atualiza nome/username (podem mudar) e desmarca como bloqueado
                self._conn.execute(
                    """UPDATE users
                       SET username=?, first_name=?, last_name=?, is_blocked=0
                       WHERE user_id=?""",
                    (username, first_name, last_name, user_id),
                )
            else:
                self._conn.execute(
                    """INSERT INTO users (user_id, username, first_name, last_name, joined_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, username, first_name, last_name, time.time()),
                )
            self._conn.commit()
            return not bool(existing)

    async def mark_blocked(self, user_id: int) -> None:
        """Marca usuário como tendo bloqueado o bot (UserIsBlocked error)."""
        async with self._lock:
            if self._conn:
                self._conn.execute(
                    "UPDATE users SET is_blocked=1 WHERE user_id=?", (user_id,)
                )
                self._conn.commit()

    async def get_all_active_ids(self) -> list[int]:
        """Retorna IDs de todos os usuários ativos (não bloquearam o bot)."""
        async with self._lock:
            if not self._conn:
                return []
            rows = self._conn.execute(
                "SELECT user_id FROM users WHERE is_blocked = 0"
            ).fetchall()
            return [r[0] for r in rows]

    async def stats(self) -> dict:
        """Estatísticas para o painel admin."""
        async with self._lock:
            if not self._conn:
                return {}
            total    = self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active   = self._conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_blocked=0"
            ).fetchone()[0]
            blocked  = total - active
            # Últimos 7 dias
            week_ago = time.time() - 7 * 86_400
            new_week = self._conn.execute(
                "SELECT COUNT(*) FROM users WHERE joined_at > ?", (week_ago,)
            ).fetchone()[0]
            return {
                "total": total,
                "active": active,
                "blocked": blocked,
                "new_this_week": new_week,
            }


# Instância global
user_db = UserDB()
