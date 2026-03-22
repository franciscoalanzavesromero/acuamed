#!/bin/bash
# Proxy para que los contenedores Docker puedan alcanzar LM Studio (Windows/localhost:1234)
# Ejecútalo una vez antes de docker compose up
pkill -f "socat.*172.18.0.1.*11234" 2>/dev/null
sleep 1
nohup socat TCP-LISTEN:11234,bind=172.18.0.1,reuseaddr,fork TCP:127.0.0.1:1234 > /tmp/socat_lmstudio.log 2>&1 &
echo "LM Studio proxy iniciado (PID: $!)"
echo "Escuchando en 172.18.0.1:11234 → localhost:1234"
