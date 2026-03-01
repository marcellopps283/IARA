#!/bin/bash
# restart.sh — Reinicia a Kitty com segurança
# Uso: bash restart.sh

echo "🌊 Reiniciando Iara..."

# Matar processos existentes
ps aux | grep "python brain.py" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null
sleep 2

# Limpar log antigo (mantém backup)
cd ~/KittyClaw
if [ -f kitty.log ]; then
    tail -100 kitty.log > kitty.log.bak
    > kitty.log
fi

# Iniciar
nohup python brain.py >> kitty.log 2>&1 &
NEW_PID=$!

sleep 3
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ Iara online! PID: $NEW_PID"
    tail -5 kitty.log
else
    echo "❌ Falha ao iniciar. Log:"
    cat kitty.log
fi
