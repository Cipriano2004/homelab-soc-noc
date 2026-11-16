#!/usr/bin/env bash
# Simulador de incidentes do lab NOC – gera alertas reais no Zabbix para treinar
# o ciclo: detectar → diagnosticar → resolver → documentar.
#
# Uso (dentro da pasta do projeto, na VM):
#   bash scripts/simular-incidentes.sh            # mostra o menu
#   bash scripts/simular-incidentes.sh 1          # roda direto o cenário 1
#
# Todos os cenários se desfazem sozinhos no fim (ou com Ctrl+C).

set -euo pipefail
DURACAO=${DURACAO:-300}   # segundos (padrão: 5 minutos)

cor()  { printf "\033[1;%sm%s\033[0m\n" "$1" "$2"; }
info() { cor 36 "[$(date +%H:%M:%S)] $*"; }

site_fora() {
  info "Cenário 1: derrubando o site interno por ${DURACAO}s (trigger: 'Site interno fora do ar' – High)"
  trap 'docker start web-teste >/dev/null; info "Site restaurado."' EXIT
  docker stop web-teste >/dev/null
  info "Site parado. Acompanhe: Zabbix → Monitoring → Problems e o Grafana."
  sleep "$DURACAO"
}

site_lento() {
  info "Cenário 2: adicionando 700ms de atraso na rede do site por ${DURACAO}s (trigger: 'Site interno lento' – Warning)"
  docker run --rm --name lentidao --net container:web-teste --cap-add NET_ADMIN alpine:3.20 \
    sh -c "apk add --no-cache iproute2 >/dev/null &&
           tc qdisc add dev eth0 root netem delay 700ms &&
           echo 'atraso aplicado' && sleep ${DURACAO};
           tc qdisc del dev eth0 root; echo 'atraso removido'"
}

cpu_alta() {
  info "Cenário 3: estressando 2 CPUs da VM por ${DURACAO}s (veja o gráfico de CPU subir no Grafana)"
  docker run --rm --name stress --pid host alpine:3.20 \
    sh -c "apk add --no-cache stress-ng >/dev/null && stress-ng --cpu 2 --timeout ${DURACAO}s --metrics-brief"
}

disco_cheio() {
  local arquivo="$HOME/lixo-teste-disco.bin"
  local livre_gb
  livre_gb=$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
  local tamanho=$(( livre_gb > 3 ? livre_gb - 2 : 1 ))
  info "Cenário 4: criando arquivo de ${tamanho}G para encher o disco por ${DURACAO}s"
  trap 'rm -f "$arquivo"; info "Arquivo removido, disco liberado."' EXIT
  fallocate -l "${tamanho}G" "$arquivo"
  df -h /
  sleep "$DURACAO"
}

menu() {
  cat >&2 <<EOF
=== Simulador de incidentes – Lab NOC ===
 1) Site interno fora do ar
 2) Site interno lento
 3) CPU alta na VM
 4) Disco quase cheio
 0) Sair
EOF
  read -rp "Escolha: " op
  echo "$op"
}

op=${1:-$(menu | tail -1)}
case "$op" in
  1) site_fora ;;
  2) site_lento ;;
  3) cpu_alta ;;
  4) disco_cheio ;;
  *) echo "Saindo." ;;
esac
