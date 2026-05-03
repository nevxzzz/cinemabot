// ecosystem.config.js — PM2 process manager config
// Uso: pm2 start ecosystem.config.js

module.exports = {
  apps: [
    {
      name: "cinemabot",
      script: "main.py",
      interpreter: "python3",

      // Reinicia automaticamente se o processo travar ou crashar
      autorestart: true,
      watch: false,           // não reinicia ao salvar arquivo (use false em produção)
      max_memory_restart: "150M",  // reinicia se usar mais de 150MB de RAM

      // Logs do PM2 (separados dos logs do Python)
      out_file: "logs/pm2_out.log",
      error_file: "logs/pm2_err.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss",

      // Delay entre reinicializações automáticas
      restart_delay: 3000,   // 3 segundos

      // Variáveis de ambiente (alternativa ao .env — prefira o .env)
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};
