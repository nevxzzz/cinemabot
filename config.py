"""
Módulo de configuração — lê variáveis do .env usando python-dotenv.
Sem pydantic para máxima compatibilidade com Termux (sem Rust necessário).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega o .env da pasta do projeto
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise RuntimeError(
            f"❌ Variável obrigatória '{key}' não encontrada no .env\n"
            f"   Edite o arquivo .env e preencha o valor."
        )
    return val


def _int(key: str, default: int = 0) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except ValueError:
        return default


class _Settings:
    # Telegram
    BOT_TOKEN:   str = _require("BOT_TOKEN")
    API_ID:      int = _int("API_ID")
    API_HASH:    str = _require("API_HASH")

    # Admin (seu ID numérico — use @userinfobot para descobrir)
    ADMIN_ID:    int = _int("ADMIN_ID", 0)

    # TMDB
    TMDB_API_KEY:   str = _require("TMDB_API_KEY")
    TMDB_BASE_URL:  str = os.getenv("TMDB_BASE_URL",  "https://api.themoviedb.org/3")
    TMDB_IMAGE_BASE: str = os.getenv("TMDB_IMAGE_BASE", "https://image.tmdb.org/t/p/w500")
    TMDB_LANGUAGE:  str = os.getenv("TMDB_LANGUAGE",  "pt-BR")


settings = _Settings()
