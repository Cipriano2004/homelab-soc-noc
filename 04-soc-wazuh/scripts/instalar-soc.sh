#!/usr/bin/env bash
# Instala o SOC (Wazuh single-node em Docker) na VM soc-lab.
# Rode como root, de dentro da pasta "scripts" do projeto:
#   sudo -i
#   cd /home/ariel/share/scripts      (ou onde estiver o projeto)
#   bash instalar-soc.sh
#
# Pode rodar de novo sem problema: cada passo verifica se já foi feito.
set -euo pipefail

ORIGEM="$(cd "$(dirname "$0")/.." && pwd)"   # pasta do projeto (um nível acima de scripts/)
USUARIO="${USUARIO:-ariel}"
DESTINO="/home/${USUARIO}/soc"

log() { printf '\033[1;36m[soc %s] %s\033[0m\n' "$(date +%H:%M:%S)" "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Rode como root: sudo -i e depois bash instalar-soc.sh"; exit 1
fi

log "1/6 Fuso horário: America/Sao_Paulo"
timedatectl set-timezone America/Sao_Paulo

log "2/6 Docker"
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -q
  apt-get install -y -q docker.io docker-compose-v2
fi
usermod -aG docker "$USUARIO"

log "3/6 Kernel: vm.max_map_count=262144 (exigido pelo Wazuh Indexer / OpenSearch)"
echo 'vm.max_map_count=262144' > /etc/sysctl.d/99-wazuh.conf
sysctl --system >/dev/null

log "4/6 Copiando o projeto para ${DESTINO}"
mkdir -p "$DESTINO"
cp -rT "$ORIGEM" "$DESTINO"
chown -R "$USUARIO:$USUARIO" "$DESTINO"
cd "$DESTINO/wazuh"

log "5/6 Certificados TLS entre manager, indexer e dashboard"
if [ ! -f config/wazuh_indexer_ssl_certs/root-ca.pem ]; then
  docker compose -f generate-indexer-certs.yml run --rm generator
else
  log "   certificados já existem, pulando"
fi

log "6/6 Subindo Wazuh (manager, indexer, dashboard) – o primeiro download leva alguns minutos"
docker compose up -d

IP=$(hostname -I | awk '{print $1}')
log "Pronto! Aguarde ~2 minutos e acesse: https://${IP}  (aceite o aviso de certificado)"
log "Login inicial: admin / SecretPassword  (troque depois)"
log "Para ver o estado: cd ${DESTINO}/wazuh && docker compose ps"
