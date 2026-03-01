#!/bin/sh
# Adicione a seguinte linha no crontab (comando: crontab -e) 
# para rodar o backup todos os dias às 05:00 da manhã:
# 0 5 * * * /bin/sh /data/data/com.termux/files/home/KittyClaw/backup_cron.sh

# Acessa o diretório onde o script está localizado (raiz do projeto IARA)
cd "$(dirname "$0")" || exit

# Executa o script python salva e pendura a saída em um log na raiz do Termux
python backup_drive.py >> ~/iara_backup.log 2>&1
