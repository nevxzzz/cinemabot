#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────
#  update.sh — Atualiza o CinemaBot e o player.html do GitHub
#  Uso: bash update.sh
# ─────────────────────────────────────────────────────────────

set -e

BOT_DIR="$HOME/bots/cinemabot"
REPO_URL="https://github.com/nevxzzz/cinemabot.git"   # <-- troque pelo seu repo
BRANCH="main"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
err()  { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎬 CinemaBot — Atualizador"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Garante que git está instalado ────────────────────────
if ! command -v git &>/dev/null; then
    warn "git não encontrado — instalando..."
    pkg install git -y
fi

# ── 2. Primeira vez: clonar. Demais: pull ────────────────────
if [ ! -d "$BOT_DIR/.git" ]; then
    log "Primeiro clone do repositório..."
    mkdir -p "$HOME/bots"
    git clone "$REPO_URL" "$BOT_DIR"
    cd "$BOT_DIR"
else
    log "Repositório já existe — puxando atualizações..."
    cd "$BOT_DIR"

    # Guarda arquivos que NÃO devem ser sobrescritos pelo git
    git stash --include-untracked 2>/dev/null || true

    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"

    # Restaura .env e session (nunca estão no repo)
    git stash pop 2>/dev/null || true
fi

# ── 3. Instala/atualiza dependências Python ──────────────────
log "Atualizando dependências Python..."
pip install -r requirements.txt -q

# ── 4. Reinicia o bot no PM2 ─────────────────────────────────
if command -v pm2 &>/dev/null; then
    if pm2 list | grep -q "cinemabot"; then
        log "Reiniciando bot no PM2..."
        pm2 restart cinemabot
    else
        warn "PM2 existe mas 'cinemabot' não está na lista. Iniciando..."
        pm2 start ecosystem.config.js
    fi
    pm2 save -q
else
    warn "PM2 não encontrado. Reinicie o bot manualmente: python main.py"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Atualização concluída! ✅"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
