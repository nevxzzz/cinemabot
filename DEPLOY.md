# 🚀 Guia de Deploy — CinemaBot no Termux com PM2

---

## Estrutura do projeto

```
~/bots/cinemabot/
├── main.py
├── config.py
├── keyboards.py
├── messages.py
├── player.html         ← hospedado no GitHub Pages (mesmo repo)
├── update.sh           ← script de atualização com 1 comando
├── ecosystem.config.js
├── requirements.txt
├── .env                ← suas credenciais (NÃO vai pro git)
├── .gitignore
├── handlers/
└── services/
```

---

## Primeira instalação

### 1. Instalar dependências no Termux

```bash
pkg update && pkg upgrade -y
pkg install python nodejs git -y
npm install -g pm2
```

### 2. Colocar o repositório no GitHub (só na primeira vez)

No seu PC ou celular, crie um repositório no GitHub chamado `cinemabot`.
Depois, no Termux:

```bash
mkdir -p ~/bots && cd ~/bots
git clone https://github.com/SEU_USUARIO/cinemabot.git
cd cinemabot
```

Ou, se você já tem os arquivos no Termux:

```bash
cd ~/bots/cinemabot
git init
git remote add origin https://github.com/SEU_USUARIO/cinemabot.git
git add .
git commit -m "primeiro commit"
git push -u origin main
```

### 3. Editar o update.sh com a URL do seu repo

```bash
nano ~/bots/cinemabot/update.sh
# Mude a linha: REPO_URL="https://github.com/SEU_USUARIO/cinemabot.git"
```

### 4. Configurar o .env

```bash
cp .env.example .env
nano .env
```

Preencha:
```env
BOT_TOKEN=seu_token_do_botfather
API_ID=123456
API_HASH=sua_api_hash
ADMIN_ID=seu_id_numerico_telegram
TMDB_API_KEY=sua_chave_tmdb
```

### 5. Configurar o PM2

```bash
# Descobre o caminho do python
which python

# Edita o ecosystem e coloca o caminho correto
nano ecosystem.config.js
# Mude: interpreter: "/data/data/com.termux/files/usr/bin/python"

# Inicia
pm2 start ecosystem.config.js
pm2 save
pm2 startup
# → Copie e execute o comando que aparecer
```

### 6. Ativar o GitHub Pages para o player.html

No GitHub, vá em Settings → Pages → Source: **Deploy from branch** → branch: `main` → pasta: `/ (root)`.

O player ficará disponível em:
`https://SEU_USUARIO.github.io/cinemabot/player.html`

Atualize o `PLAYER_BASE_URL` no `keyboards.py` com essa URL.

---

## Como atualizar depois (fluxo normal)

Quando eu te mandar arquivos novos, é um comando só no Termux:

```bash
bash ~/bots/cinemabot/update.sh
```

Isso faz automaticamente:
1. Puxa as mudanças do GitHub (`git pull`)
2. Atualiza dependências Python se necessário
3. Reinicia o bot no PM2

O `player.html` atualiza junto porque está no mesmo repositório que o GitHub Pages serve.

---

## Como eu vou te mandar atualizações (fluxo futuro)

Em vez de baixar zip, você vai:

1. No Claude: pedir a correção
2. Eu faço as mudanças e te dou os arquivos
3. Você commita e dá push pelo GitHub Desktop, pelo site do GitHub, ou pelo Termux:

```bash
cd ~/bots/cinemabot
git add .
git commit -m "correção"
git push
```

4. Depois:

```bash
bash ~/bots/cinemabot/update.sh
```

Pronto. Bot atualizado + player.html atualizado ao mesmo tempo.

---

## Comandos do dia a dia

```bash
pm2 logs cinemabot          # Logs ao vivo
pm2 restart cinemabot       # Reiniciar manualmente
pm2 status                  # Ver se está rodando
bash ~/bots/cinemabot/update.sh  # Atualizar tudo
```

---

## .gitignore recomendado

```
.env
*.session
*.session-journal
*.db
*.db-shm
*.db-wal
logs/
__pycache__/
*.pyc
```
