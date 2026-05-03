# 🎬 CinemaBot

Bot de Telegram para busca e assistir filmes e séries com dados em português, powered by TMDB + 2Embed + VidSrc.

---

## 📁 Estrutura do Projeto

```
cinemabot/
├── main.py              # Ponto de entrada
├── config.py            # Configurações via .env
├── keyboards.py         # Teclados inline (inclui player URLs)
├── messages.py          # Templates de mensagens
├── player.html          # Mini App do player de vídeo (hospede este arquivo!)
├── requirements.txt
├── .env.example
├── .gitignore
├── handlers/
│   ├── __init__.py
│   ├── start.py
│   ├── search.py
│   └── callbacks.py
└── services/
    ├── __init__.py
    └── tmdb.py
```

---

## ⚙️ Configuração

### 1. Clone e instale dependências

```bash
git clone <repo>
cd cinemabot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

```env
BOT_TOKEN=seu_token_do_botfather
API_ID=seu_api_id
API_HASH=seu_api_hash
TMDB_API_KEY=sua_chave_tmdb
```

### 3. Hospede o player.html

O player funciona como um **Telegram Mini App (WebApp)**.
Você precisa hospedar o `player.html` em um servidor HTTPS público.

**Opção gratuita recomendada — GitHub Pages:**
```bash
# Crie um repo público chamado "cinemabot-player"
# Coloque o player.html na raiz
# Acesse: https://SEU_USUARIO.github.io/cinemabot-player/player.html
```

**Outras opções:** Netlify, Vercel, Cloudflare Pages — todas gratuitas.

### 4. Atualize a URL do player em `keyboards.py`

```python
# keyboards.py — linha 17
PLAYER_BASE_URL = "https://SEU_USUARIO.github.io/cinemabot-player/player.html"
```

### 5. Configure o Bot como Mini App no BotFather

No BotFather:
```
/mybots → Escolha seu bot → Bot Settings → Menu Button
```
Defina qualquer URL (pode ser a mesma do player). Isso habilita WebApp no bot.

### 6. Execute

```bash
python main.py
```

---

## ▶️ Player de Vídeo

O player abre **dentro do Telegram** (sem sair do app) via WebApp/Mini App.

| Fonte | Filmes | Séries |
|-------|--------|--------|
| 2Embed | ✅ | ✅ |
| VidSrc.to | ✅ | ✅ |
| VidSrc.me | ✅ | ✅ |

**Como usar:**
- Em qualquer filme → botão **▶️ Assistir Online**
- Em qualquer série → botão **▶️ Assistir Online** (abre T1E1)
- Em um episódio específico → botão **▶️ Assistir Episódio**
- Dentro do player, troque de fonte pelos botões inferiores

---

## 🤖 Funcionalidades

| Ação | Como usar |
|------|-----------|
| Boas-vindas | `/start` |
| Busca | Digita qualquer nome |
| Busca por comando | `/buscar Inception` |
| Ver detalhes | Toca no resultado |
| **Assistir filme** | **Botão ▶️ Assistir Online** |
| Ver temporadas | Botão 📋 Ver Temporadas |
| **Assistir episódio** | **Botão ▶️ Assistir Episódio** |
| Trocar fonte de vídeo | Botões 2Embed / VidSrc na base do player |

---

## 🔐 Segurança

- Credenciais sempre em `.env`, nunca no código
- O `player.html` não armazena nenhum dado do usuário
- As APIs de embed são públicas e não requerem autenticação

---

## 🚀 Próximas features sugeridas

- [ ] Watchlist pessoal (SQLite)
- [ ] Notificações de novos episódios
- [ ] Trailer via YouTube
- [ ] Modo inline (`@botname inception`)
- [ ] Legendas integradas
