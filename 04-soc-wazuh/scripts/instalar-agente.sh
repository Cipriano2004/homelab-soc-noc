#!/usr/bin/env bash
# Instala o Wazuh Agent 4.14.10 numa máquina Linux (Ubuntu) e conecta ao manager.
# Rode como root no endpoint (ex.: na VM noc-lab):
#   bash instalar-agente.sh                      -> usa o manager 192.168.2.192
#   bash instalar-agente.sh 192.168.2.192 noc-lab -> manager e nome do agente
set -euo pipefail

MANAGER="${1:-192.168.2.192}"
NOME="${2:-$(hostname)}"
VERSAO="4.14.10-1"     # o agente nunca pode ser mais novo que o manager

log() { printf '\033[1;36m[agente %s] %s\033[0m\n' "$(date +%H:%M:%S)" "$*"; }
[ "$(id -u)" -eq 0 ] || { echo "Rode como root (sudo -i)"; exit 1; }

log "1/4 Chave GPG e repositório oficial do Wazuh"
apt-get install -y -q curl gnupg >/dev/null
curl -fsSL https://packages.wazuh.com/key/GPG-KEY-WAZUH \
  | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
  > /etc/apt/sources.list.d/wazuh.list
apt-get update -q

log "2/4 Instalando wazuh-agent ${VERSAO} (manager=${MANAGER}, nome=${NOME})"
WAZUH_MANAGER="$MANAGER" WAZUH_AGENT_NAME="$NOME" apt-get install -y -q "wazuh-agent=${VERSAO}"
apt-mark hold wazuh-agent   # evita que um 'apt upgrade' instale versão mais nova que o manager

log "3/4 Ativando o serviço"
systemctl daemon-reload
systemctl enable --now wazuh-agent

log "4/4 Conferindo a conexão"
sleep 10
grep -E "Connected to the server|ERROR" /var/ossec/logs/ossec.log | tail -3 || true
log "Pronto. No dashboard do Wazuh: Agents -> ${NOME} deve aparecer como Active."
