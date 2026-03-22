#!/bin/bash
# Script de inicio automático para ACUAMED + LM Studio

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== ACUAMED - Inicio Automático ===${NC}"

# 1. Verificar que LM Studio esté corriendo
echo -e "${YELLOW}[1/4] Verificando LM Studio...${NC}"
if curl -s http://localhost:1234/v1/models > /dev/null 2>&1; then
    echo -e "${GREEN}✓ LM Studio está corriendo${NC}"
else
    echo -e "${RED}✗ LM Studio no está disponible en localhost:1234${NC}"
    echo -e "${YELLOW}  Por favor, inicia LM Studio y carga el modelo 'ministral-3-8b-instruct-2512'${NC}"
    exit 1
fi

# 2. Iniciar proxy socat si no está corriendo
echo -e "${YELLOW}[2/4] Iniciando proxy LM Studio...${NC}"
if pgrep -f "socat.*11234.*1234" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Proxy ya está corriendo${NC}"
else
    pkill -f "socat.*11234.*1234" 2>/dev/null || true
    sleep 1
    nohup socat TCP-LISTEN:11234,reuseaddr,fork TCP:127.0.0.1:1234 > /tmp/socat_lmstudio.log 2>&1 &
    sleep 2
    if pgrep -f "socat.*11234.*1234" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Proxy iniciado correctamente${NC}"
    else
        echo -e "${RED}✗ No se pudo iniciar el proxy${NC}"
        cat /tmp/socat_lmstudio.log
        exit 1
    fi
fi

# 3. Verificar proxy
echo -e "${YELLOW}[3/4] Verificando proxy...${NC}"
if curl -s http://localhost:11234/v1/models > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Proxy funcionando correctamente${NC}"
else
    echo -e "${RED}✗ Proxy no responde${NC}"
    exit 1
fi

# 4. Iniciar contenedores Docker
echo -e "${YELLOW}[4/4] Iniciando contenedores Docker...${NC}"
docker compose up -d --build

# Esperar a que los servicios estén listos
echo -e "${YELLOW}Esperando a que los servicios estén listos...${NC}"
sleep 5

# Verificar estado
echo ""
echo -e "${GREEN}=== Estado de los servicios ===${NC}"
docker compose ps

echo ""
echo -e "${GREEN}=== URLs disponibles ===${NC}"
echo "Frontend:  http://localhost:3000"
echo "Backend:   http://localhost:8000"
echo "API Docs:  http://localhost:8000/docs"
echo ""
echo -e "${GREEN}¡ACUAMED iniciado correctamente!${NC}"
