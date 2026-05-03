"""
Rastreador de mensagens — armazena IDs de mensagens por usuário para limpeza automática.

Estratégia:
  - Cada usuário tem uma fila com as últimas N mensagens do bot.
  - Antes de enviar uma nova resposta de busca, as mensagens antigas são apagadas.
  - Mensagens de detalhe (foto+legenda) NÃO são apagadas automaticamente,
    apenas as de lista de resultados, para não frustrar o usuário.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque

from pyrogram import Client
from pyrogram.errors import MessageDeleteForbidden, MessageIdInvalid

logger = logging.getLogger("CinemaBot.tracker")

# Máximo de mensagens de resultado guardadas por usuário
_MAX_TRACKED = 5

# { user_id: deque[(chat_id, message_id)] }
_search_messages: dict[int, deque] = defaultdict(lambda: deque(maxlen=_MAX_TRACKED))


def track_message(user_id: int, chat_id: int, message_id: int) -> None:
    """Registra uma mensagem de resultado para futura limpeza."""
    _search_messages[user_id].append((chat_id, message_id))


async def delete_old_search_messages(client: Client, user_id: int) -> None:
    """
    Apaga todas as mensagens de resultado anteriores do usuário.
    Chamado antes de enviar uma nova busca.
    """
    queue = _search_messages.pop(user_id, deque())
    if not queue:
        return

    tasks = [_safe_delete(client, chat_id, msg_id) for chat_id, msg_id in queue]
    await asyncio.gather(*tasks, return_exceptions=True)


async def _safe_delete(client: Client, chat_id: int, message_id: int) -> None:
    try:
        await client.delete_messages(chat_id, message_id)
        logger.debug("Mensagem %d apagada do chat %d", message_id, chat_id)
    except (MessageDeleteForbidden, MessageIdInvalid):
        pass  # Mensagem já apagada ou sem permissão — ignora silenciosamente
    except Exception as exc:
        logger.warning("Erro ao apagar mensagem %d: %s", message_id, exc)
