"""
Handler de administração — comandos exclusivos do dono do bot.

Comandos:
  /admin       — Painel com estatísticas do bot
  /broadcast   — Enviar mensagem para todos os usuários
  /clearcache  — Limpar o cache SQLite manualmente

Segurança: todos os comandos verificam se o remetente é o ADMIN_ID
configurado no .env. Se não for, a mensagem é ignorada silenciosamente.
"""

from __future__ import annotations

import asyncio
import logging
import time

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    PeerIdInvalid,
    UserIsBlocked,
)
from pyrogram.types import Message

from config import settings
from services.cache import cache
from services.database import user_db

logger = logging.getLogger("CinemaBot.admin")

# Controle de broadcast em andamento (evita disparos duplicados)
_broadcast_running: bool = False


def register_admin_handlers(app: Client):

    # ── Filtro de admin ──────────────────────────────────────────────
    def is_admin(_, __, message: Message) -> bool:
        return message.from_user and message.from_user.id == settings.ADMIN_ID

    admin_filter = filters.create(is_admin)

    # ── /admin — Painel de estatísticas ─────────────────────────────
    @app.on_message(filters.command("admin") & filters.private & admin_filter)
    async def admin_panel(client: Client, message: Message):
        db_stats    = await user_db.stats()
        cache_stats = await cache.stats()

        lines = [
            "🛠 **Painel Admin — CinemaBot**\n",
            "**👥 Usuários**",
            f"  • Total registrado: `{db_stats.get('total', 0)}`",
            f"  • Ativos (não bloquearam): `{db_stats.get('active', 0)}`",
            f"  • Bloquearam o bot: `{db_stats.get('blocked', 0)}`",
            f"  • Novos esta semana: `{db_stats.get('new_this_week', 0)}`\n",
            "**📦 Cache SQLite**",
            f"  • Entradas válidas: `{cache_stats.get('valid', 0)}`",
            f"  • Expiradas (pendentes): `{cache_stats.get('expired', 0)}`",
            f"  • Tamanho do arquivo: `{cache_stats.get('size_kb', 0)} KB`\n",
            "**⚙️ Comandos disponíveis**",
            "  `/broadcast <mensagem>` — Enviar para todos",
            "  `/clearcache` — Limpar cache agora",
        ]
        await message.reply("\n".join(lines), quote=True)

    # ── /broadcast — Envio em massa ─────────────────────────────────
    @app.on_message(filters.command("broadcast") & filters.private & admin_filter)
    async def broadcast(client: Client, message: Message):
        global _broadcast_running

        # Extrai o texto após o comando
        text = message.text.split(None, 1)
        if len(text) < 2 or not text[1].strip():
            await message.reply(
                "⚠️ Uso: `/broadcast <mensagem>`\n\n"
                "Exemplo:\n`/broadcast 🎬 Nova funcionalidade disponível!`",
                quote=True,
            )
            return

        if _broadcast_running:
            await message.reply("⏳ Já há um broadcast em andamento. Aguarde terminar.", quote=True)
            return

        broadcast_text = text[1].strip()
        user_ids = await user_db.get_all_active_ids()
        total = len(user_ids)

        if total == 0:
            await message.reply("❌ Nenhum usuário ativo para enviar.", quote=True)
            return

        # Confirmação inicial
        status_msg = await message.reply(
            f"📡 Iniciando broadcast para **{total}** usuário(s)…\n"
            f"⏳ Isso pode levar alguns minutos.",
            quote=True,
        )

        _broadcast_running = True
        sent = 0
        failed = 0
        blocked = 0
        start_ts = time.time()

        for uid in user_ids:
            try:
                await client.send_message(uid, broadcast_text)
                sent += 1

            except FloodWait as e:
                # Telegram pediu para esperar — respeitamos
                logger.warning("FloodWait %ds durante broadcast", e.value)
                await asyncio.sleep(e.value)
                try:
                    await client.send_message(uid, broadcast_text)
                    sent += 1
                except Exception:
                    failed += 1

            except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
                # Usuário bloqueou o bot ou conta desativada
                await user_db.mark_blocked(uid)
                blocked += 1

            except Exception as exc:
                logger.error("Broadcast falhou para uid=%d: %s", uid, exc)
                failed += 1

            # Pausa entre mensagens para evitar rate limit (20 msgs/s máx)
            await asyncio.sleep(0.05)

        _broadcast_running = False
        elapsed = round(time.time() - start_ts, 1)

        await status_msg.edit(
            f"✅ **Broadcast concluído** em {elapsed}s\n\n"
            f"📬 Enviado: `{sent}`\n"
            f"🚫 Bloquearam o bot: `{blocked}` _(marcados como inativos)_\n"
            f"❌ Outros erros: `{failed}`"
        )
        logger.info(
            "Broadcast finalizado — sent=%d blocked=%d failed=%d elapsed=%.1fs",
            sent, blocked, failed, elapsed,
        )

    # ── /clearcache — Limpar cache manualmente ───────────────────────
    @app.on_message(filters.command("clearcache") & filters.private & admin_filter)
    async def clear_cache(client: Client, message: Message):
        count = await cache.clear_all()
        await message.reply(
            f"🗑 Cache limpo com sucesso!\n`{count}` entradas removidas.",
            quote=True,
        )
        logger.info("Cache limpo manualmente pelo admin. Entradas: %d", count)
