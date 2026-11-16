# Runbook do NOC – Empresa X

Procedimentos padrão para cada alerta do Zabbix. Objetivo: qualquer analista N1 consegue **diagnosticar e resolver** (ou escalar) seguindo os passos, sem depender de quem montou o ambiente.

**Regra geral para todo alerta**
1. **Reconhecer (Acknowledge)** o problema no Zabbix, com uma mensagem curta: "Analisando – Ariel".
2. Seguir o procedimento abaixo.
3. Se não resolver em **15 minutos** (High) ou **30 minutos** (Average/Warning), **escalar** para o N2 com o que já foi verificado.
4. Depois de resolvido, **registrar o chamado** em `docs/incidentes/` usando o `TEMPLATE-incidente.md`.

Comandos rodam na VM, dentro da pasta do projeto (`cd ~/noc`).

---

## Site interno fora do ar
**Severidade:** High · **Trigger:** `last(/site-interno/net.tcp.service[http,web-teste,80])=0`

**Impacto:** usuários não acessam o sistema interno.

**Diagnóstico**
```bash
docker ps -a --filter name=web-teste       # o container está "Up" ou "Exited"?
docker logs --tail 50 web-teste            # erro no nginx?
docker run --rm --network container:zbx-server alpine:3.20 wget -S -O /dev/null http://web-teste/   # o Zabbix alcança o site?
```
| O que você viu | Causa provável | Ação |
|---|---|---|
| Status `Exited` | Container parado/caiu | `docker start web-teste` |
| `Up`, mas log com erro de config | Configuração do nginx quebrada | Desfazer a última mudança e `docker restart web-teste` |
| `Up` e porta não responde | Rede Docker / container travado | `docker restart web-teste` |
| Tudo ok, mas alerta continua | Problema no próprio monitoramento | Ver "Agente / Zabbix indisponível" |

**Validação:** o trigger muda para **Resolved** e o painel "Site interno" do Grafana volta para **● NO AR**.

---

## Site interno lento
**Severidade:** Warning · **Trigger:** média do tempo de resposta > 0,5s em 2 minutos

**Diagnóstico**
```bash
docker stats --no-stream                   # algum container consumindo CPU/memória demais?
uptime                                     # load da VM alto?
docker run --rm --network container:zbx-server alpine:3.20 sh -c "time wget -q -O /dev/null http://web-teste/"
```
- Se a VM estiver com **CPU alta**, siga também "CPU alta na VM".
- Se só o site está lento: `docker restart web-teste` e acompanhe o gráfico "Tempo de resposta do site".
- Se persistir após o restart: **escalar** (pode ser problema de aplicação).

---

## Cenário web falhou
**Severidade:** Average · **Trigger:** `web.test.fail[Site interno] <> 0`

O cenário web baixa a página e espera **HTTP 200**. Ele falha quando o site está fora ou devolve erro (404, 500...).
```bash
docker run --rm --network container:zbx-server alpine:3.20 wget -S -O /dev/null http://web-teste/ 2>&1 | head -5
```
- Código **5xx** → erro no servidor: ver logs do nginx (`docker logs web-teste`).
- Código **404** → página removida/alterada: verificar o último deploy.
- Sem resposta → seguir "Site interno fora do ar".

---

## CPU alta na VM
**Severidade:** Warning/Average (template *Linux by Zabbix agent*) · **Origem:** host `vm-noc-lab`

```bash
top -o %CPU            # quem está usando CPU? (q para sair)
docker stats --no-stream
```
- Processo/container conhecido em pico temporário (ex.: backup) → acompanhar por 10 min.
- Container travado em 100% → `docker restart <nome>`.
- Processo desconhecido → **não matar sem entender**. Anotar PID/nome/usuário e **escalar para Segurança** (pode ser mineração de cripto ou malware).

---

## Memória alta / pouca memória disponível
**Origem:** host `vm-noc-lab`
```bash
free -h
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"
```
- Identificar o maior consumidor. Se for um container, reiniciar fora do horário de pico.
- Se a VM inteira está no limite com uso normal → abrir requisição para **aumentar a RAM** da VM.

---

## Disco quase cheio
**Origem:** host `vm-noc-lab` (FS `/hostfs` = raiz da VM)
```bash
df -h /
sudo du -xh / --max-depth=2 2>/dev/null | sort -h | tail -15   # maiores pastas
docker system df                                               # espaço usado pelo Docker
```
- Imagens/containers antigos: `docker system prune` (**confirmar com o N2 antes** em produção).
- Logs grandes em `/var/log`: `sudo journalctl --vacuum-size=200M`.
- Arquivo de teste esquecido do simulador: `rm ~/lixo-teste-disco.bin`.

---

## Agente / Zabbix indisponível
**Sintoma:** ícone **ZBX** ou **SNMP** vermelho no host, ou "Zabbix agent is not available".
```bash
docker compose ps                          # todos "Up"?
docker logs --tail 30 vm-agent
docker logs --tail 30 snmpd
docker run --rm --network container:zbx-server --entrypoint zabbix_get \
  zabbix/zabbix-agent2:ubuntu-7.0-latest -s 172.30.0.1 -k agent.ping   # deve responder 1
```
- Container parado → `docker compose up -d`.
- SNMP sem resposta → conferir a comunidade (`{$SNMP_COMMUNITY}` no host) e o `snmp/snmpd.conf`.

---

## Contatos de escalonamento (exemplo do lab)
| Nível | Quem | Quando |
|---|---|---|
| N1 | Analista NOC de plantão | Primeiro atendimento, até 15/30 min |
| N2 | Infraestrutura | Não resolvido pelo runbook |
| Segurança | SOC | Processo desconhecido, acesso suspeito, malware |
