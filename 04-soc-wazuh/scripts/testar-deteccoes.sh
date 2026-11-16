#!/usr/bin/env bash
# Testes de detecção do lab SOC – gera eventos benignos que o Wazuh já sabe
# classificar, para você treinar a INVESTIGAÇÃO (o que foi, IOC, técnica MITRE,
# resposta). Nada aqui ataca outra máquina: são ações normais de administração
# que, num endpoint monitorado, viram alerta. Rode DENTRO do endpoint com agente
# (a VM noc-lab), como root.
#
#   bash testar-deteccoes.sh        # menu
#   bash testar-deteccoes.sh 1      # roda o teste 1
#
# Depois de cada teste, abra o dashboard do Wazuh em Threat Hunting / Alerts e
# procure o evento. Anote regra, nível e a técnica MITRE no seu relatório.
set -euo pipefail

cor()  { printf '\033[1;%sm%s\033[0m\n' "$1" "$2"; }
info() { cor 36 "[$(date +%H:%M:%S)] $*"; }
[ "$(id -u)" -eq 0 ] || { echo "Rode como root (sudo -i)"; exit 1; }

# 1) Falhas de autenticação locais (gera 5503/5710 – Authentication failed)
#    Usa 'su' para um usuário inexistente: o PAM registra a falha no log do sistema.
t_auth_fail() {
  info "Teste 1: 5 falhas de autenticação (su para usuário inexistente)"
  for i in $(seq 1 5); do
    su - naoexiste-$i -c true 2>/dev/null || true
  done
  info "Procure no Wazuh por 'authentication failure' (regra 5503). MITRE T1110 (Brute Force)."
}

# 2) Criação e remoção de usuário (gera 5902/5903 – user added/deleted)
t_user() {
  local u="teste_soc"
  info "Teste 2: criar e remover o usuário '$u' (evento de alteração de conta)"
  useradd -m "$u" 2>/dev/null || true
  sleep 2
  userdel -r "$u" 2>/dev/null || true
  info "Procure por 'new user added' / 'user deleted'. MITRE T1136 (Create Account)."
}

# 3) Uso de sudo para comando sensível (gera 5402 – successful sudo)
t_sudo() {
  info "Teste 3: comando via sudo (trilha de auditoria de privilégio)"
  sudo cat /etc/shadow >/dev/null 2>&1 || true
  info "Procure por 'sudo' no painel. Leitura de /etc/shadow é um bom exemplo de ação sensível."
}

# 4) Integridade de arquivo (FIM) – exige que /etc esteja no syscheck (está, por padrão)
t_fim() {
  info "Teste 4: alterar um arquivo monitorado (FIM) – cria e apaga /etc/teste_fim.conf"
  echo "linha de teste $(date)" > /etc/teste_fim.conf
  sleep 2
  rm -f /etc/teste_fim.conf
  info "O FIM roda periodicamente; o alerta (regra 550/554) pode levar alguns minutos."
  info "MITRE T1565 (Data Manipulation). Para ver na hora, reinicie o agente: systemctl restart wazuh-agent"
}

# 5) Rootcheck / binário suspeito num lugar incomum (gera alerta de integridade)
t_binario() {
  info "Teste 5: copiar um binário do sistema para /tmp (padrão de 'living off the land')"
  cp /bin/ls /tmp/.oculto_ls 2>/dev/null || true
  sleep 2
  info "Arquivo criado: /tmp/.oculto_ls (apague depois com: rm -f /tmp/.oculto_ls)"
  info "Exercício: por que um executável escondido em /tmp chama atenção? MITRE T1059."
}

menu() {
  cat >&2 <<EOF
=== Testes de detecção – Lab SOC (Wazuh) ===
 1) Falhas de autenticação (brute force local)
 2) Criar e remover usuário
 3) sudo para comando sensível
 4) Alteração de arquivo monitorado (FIM)
 5) Binário escondido em /tmp
 0) Sair
EOF
  read -rp "Escolha: " op
  echo "$op"
}

op=${1:-$(menu | tail -1)}
case "$op" in
  1) t_auth_fail ;;
  2) t_user ;;
  3) t_sudo ;;
  4) t_fim ;;
  5) t_binario ;;
  *) echo "Saindo." ;;
esac
