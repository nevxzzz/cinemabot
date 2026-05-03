"""
CinemaBot - Bot de Filmes e Séries para Telegram
Ponto de entrada principal da aplicação
"""

import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path

from pyrogram import Client
from config import settings
from handlers import register_handlers
from services.cache import cache
from services.database import user_db


# ─────────────────────────── Logging ────────────────────────────────

def setup_logging() -> None:
    """
    Configura o sistema de logs com dois destinos:
    - Terminal (stdout): INFO+, formato colorido/legível
    - Arquivo logs/cinemabot.log: DEBUG+, com rotação diária (7 dias)
    """
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # Handler de terminal — INFO e acima
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    # Handler de arquivo — DEBUG e acima, rotação diária, 7 dias
    log_file = log_dir / "cinemabot.log"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)

    # Silencia libs muito verbosas
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.getLogger("CinemaBot").info(
        "Sistema de logs iniciado — arquivo: %s", log_file
    )


# ─────────────────────────── Inicialização ──────────────────────────

async def main() -> None:
    setup_logging()
    logger = logging.getLogger("CinemaBot")
    logger.info("=" * 55)
    logger.info("🎬  CinemaBot iniciando...")
    logger.info("=" * 55)

    # Inicializa banco de dados e cache (síncronos, antes do loop async)
    cache.init()
    user_db.init()

    app = Client(
        "cinemabot",
        bot_token=settings.BOT_TOKEN,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
    )

    register_handlers(app)

    try:
        async with app:
            me = await app.get_me()
            logger.info("✅ Bot online como @%s (id=%d)", me.username, me.id)
            logger.info("👤 Admin configurado: id=%d", settings.ADMIN_ID)
            logger.info("⏳ Aguardando mensagens… (Ctrl+C para parar)")
            await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("🛑 Bot encerrado pelo usuário.")
    finally:
        cache.close()
        user_db.close()
        logger.info("Recursos liberados. Até logo!")


if __name__ == "__main__":
    asyncio.run(main())
