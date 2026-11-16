# Guia passo a passo – Projeto 01 NOC (Zabbix + Grafana)

Guia feito para quem está começando. Cada etapa tem **o que fazer**, **por que** e **✅ como saber se deu certo**.
Tire prints em cada ✅ e salve em `docs/img/` — eles vão para o README e para o LinkedIn.

**Tempo estimado:** 2 semanas, de 6 a 8 h por semana.

---

## ⚡ Atalho: o que já é automático

Ao rodar `docker compose up -d`, o container **zabbix-setup** configura o Zabbix sozinho pela API
(arquivo `setup/configure_zabbix.py`). Acompanhe com `docker logs -f zbx-setup` até aparecer **✅**.

| Etapa do guia | Situação |
|---|---|
| 3 – Zabbix monitorando a si mesmo | ✅ automática (agente "sidecar") |
| 4 – Monitorar o site interno | ✅ automática (host `site-interno`: porta, tempo de resposta, cenário web e 3 triggers) |
| 5 – Monitorar a VM via SNMP | ✅ automática (container `snmpd` + host `vm-noc-lab-snmp`) |
| 6 – Monitorar o Windows | manual (é no seu PC) |
| 7 – Alertas no Telegram | ✅ automática **se** preencher `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` no `.env` |
| 8 – Dashboard NOC | ✅ automático (abre direto no Grafana) |
| 9 – Simular incidente | use `bash scripts/simular-incidentes.sh` |

> **Mesmo com tudo automático, leia as etapas manuais.** Na entrevista vão perguntar *como* se cria um item ou um trigger – e você precisa saber fazer na mão também.

---

## Etapa 0 – Preparar a VM

**O que você precisa:** VMware Workstation Pro (gratuito para uso pessoal) ou VirtualBox, e a ISO do **Ubuntu Server 24.04 LTS**.

Crie a VM com:
- 2 vCPU, **4 GB de RAM**, 30 GB de disco
- Rede em modo **Bridge** (a VM recebe um IP da sua rede de casa, o que facilita acessar pelo navegador do Windows e monitorar o Windows depois)
- Na instalação, marque **Install OpenSSH server**

Depois de instalada, descubra o IP da VM:
```bash
ip -br a
```
Anote o IP (ex.: `192.168.0.50`). No resto do guia ele aparece como `IP_DA_VM`.

Dica: acesse a VM pelo terminal do Windows com `ssh seu_usuario@IP_DA_VM`, que é mais confortável e permite copiar e colar.

**Instalar o Docker:**
```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```
Saia e entre de novo no SSH (para o grupo `docker` valer).

✅ `docker run hello-world` mostra a mensagem "Hello from Docker!".

> **Por quê Docker?** Cada serviço (banco, Zabbix, Grafana) roda isolado num container, e o `docker-compose.yml` descreve tudo em um arquivo. Sobe com um comando, apaga com outro.

---

## Etapa 1 – Subir o ambiente

Copie a pasta do projeto para a VM (via `git clone` do seu repositório ou `scp`) e entre nela:
```bash
cd 01-noc-monitoramento
cp .env.example .env
nano .env        # troque as senhas de POSTGRES_PASSWORD e GRAFANA_ADMIN_PASSWORD
docker compose up -d
```
A primeira vez demora alguns minutos (baixa as imagens e cria o banco).

Confira:
```bash
docker compose ps
```
✅ Todos os containers aparecem como `running` (ou `Up`).

Se algum estiver reiniciando, veja o log dele:
```bash
docker compose logs -f zabbix-server
```

---

## Etapa 2 – Primeiro acesso ao Zabbix

1. No navegador do Windows: `http://IP_DA_VM:8080`
2. Login padrão: **Admin** / **zabbix**
3. **Troque a senha imediatamente:** menu *User settings → Profile → Change password*.
4. Coloque a nova senha em `ZABBIX_API_PASSWORD` no `.env` e recarregue o Grafana:
   ```bash
   docker compose up -d grafana
   ```

✅ Você está no painel **Dashboards → Global view** do Zabbix.

> **Por quê trocar a senha?** Senha padrão é a primeira coisa que um atacante testa. Num SOC/NOC isso é básico.

---

## Etapa 3 – Fazer o Zabbix monitorar a si mesmo

O Zabbix já vem com um host chamado **Zabbix server**, configurado para `127.0.0.1`. No `docker-compose.yml`, o agente usa `network_mode: "service:zabbix-server"`: ele divide a rede com o container do servidor, então `127.0.0.1` dentro do servidor **é** o agente. Não precisa mudar nada na interface.

> **Para a entrevista:** isso é o mesmo padrão de "sidecar" usado no Kubernetes (containers do mesmo pod compartilham a rede).

✅ Em 1 a 2 minutos, o ícone **ZBX** do host fica **verde**, e em *Monitoring → Latest data* aparecem CPU, memória e disco.

> **Conceito:** o **Zabbix Agent** coleta dados da máquina (CPU, RAM, disco) e entrega ao **Zabbix Server**, que guarda no banco e avalia os **triggers** (regras de alerta).

---

## Etapa 4 – Monitorar um "serviço da empresa" (web-teste)

O container `web-teste` é um site nginx. Vamos verificar se ele responde.

**Criar o item:**
1. *Data collection → Hosts → Zabbix server → Items → Create item*
2. Preencha:
   - Name: `Site interno - HTTP no ar`
   - Type: **Simple check**
   - Key: `net.tcp.service[http,web-teste,80]`
   - Update interval: `30s`
3. **Add**

**Criar o trigger (a regra de alerta):**
1. No mesmo host → **Triggers → Create trigger**
2. Preencha:
   - Name: `Site interno fora do ar`
   - Severity: **High**
   - Expression: `last(/Zabbix server/net.tcp.service[http,web-teste,80])=0`
3. **Add**

✅ Em *Monitoring → Latest data*, filtrando por "Site interno", o valor aparece como **1** (no ar).

> **Conceito:** item = **o que** medir. Trigger = **quando** isso vira problema. Valor 1 significa que a porta 80 respondeu; 0 significa que não respondeu.

---

## Etapa 5 – Monitorar a VM via SNMP

SNMP é o protocolo usado para monitorar roteadores, switches, impressoras e nobreaks, ou seja, o dia a dia de NOC. Vamos ativá-lo na própria VM Ubuntu para praticar.

**Na VM:**
```bash
sudo apt install -y snmpd
sudo nano /etc/snmp/snmpd.conf
```
Deixe apenas estas linhas ativas (comente as outras com `#`):
```
agentaddress udp:161
rocommunity lab-noc-ro 172.16.0.0/12
```
- `agentaddress udp:161`: escuta em todas as interfaces (o padrão é só localhost)
- `rocommunity`: comunidade **somente leitura**, aceita apenas da rede interna do Docker

```bash
sudo systemctl restart snmpd
```

**No Zabbix:**
1. *Data collection → Hosts → Create host*
2. Host name: `vm-ubuntu-snmp`, Host group: `Linux servers`
3. Templates: **Linux by SNMP**
4. Interfaces → Add → **SNMP**: IP = `IP_DA_VM`, porta 161, SNMP version **SNMPv2**, SNMP community `{$SNMP_COMMUNITY}`
5. Aba **Macros**: `{$SNMP_COMMUNITY}` = `lab-noc-ro`
6. **Add**

✅ O ícone **SNMP** fica verde e aparecem itens de interfaces de rede (tráfego in/out).

> **Para a entrevista:** SNMPv2 manda a community em texto puro. Em produção o certo é **SNMPv3**, com usuário, autenticação e criptografia. Saber explicar isso já mostra maturidade.

---

## Etapa 6 – Monitorar o seu Windows

1. Baixe o **Zabbix Agent 2** para Windows, versão **7.0 LTS**, no site oficial (zabbix.com → Download → Zabbix agents).
2. Na instalação:
   - Host name: `pc-windows`
   - Zabbix server IP/DNS: `IP_DA_VM`
   - Server or Proxy for active checks: `IP_DA_VM`
   - Marque **Add agent location to the PATH**
3. Libere a porta no firewall do Windows (PowerShell como administrador):
   ```powershell
   New-NetFirewallRule -DisplayName "Zabbix Agent" -Direction Inbound -Protocol TCP -LocalPort 10050 -Action Allow
   ```
4. No Zabbix: *Create host* → Host name `pc-windows` (igual ao da instalação), grupo `Windows`, template **Windows by Zabbix agent**, interface Agent com o IP do Windows (`ipconfig` mostra), porta 10050.

✅ Ícone **ZBX** verde no host `pc-windows`.

---

## Etapa 7 – Alertas no Telegram

**Criar o bot:**
1. No Telegram, fale com **@BotFather** → `/newbot` → escolha nome e usuário → ele te dá um **token**. Guarde, pois é uma senha.
2. Mande qualquer mensagem para o seu bot.
3. Descubra seu **chat ID**: fale com **@userinfobot** (ele responde com seu ID).

**No Zabbix:**
1. *Alerts → Media types → Telegram* → em Parameters, preencha `Token` com o token do bot → **Enabled** → Update. Use o botão **Test** para validar.
2. *Users → Users → Admin → Media → Add*: Type **Telegram**, Send to = **seu chat ID** → Add → Update.
3. *Alerts → Actions → Trigger actions → Create action*:
   - Name: `Alertas NOC - Telegram`
   - Conditions: *Trigger severity* **is greater than or equals** `Average`
   - Aba **Operations**: Add → Send to users: `Admin`, Send only to: `Telegram`
   - Marque também em **Recovery operations** (para avisar quando resolver)
   - **Add**

✅ O botão **Test** do media type faz chegar uma mensagem no seu Telegram.

> **Nunca** coloque o token do bot no GitHub ou em print sem borrar.

---

## Etapa 8 – Dashboard NOC no Grafana

1. Acesse `http://IP_DA_VM:3000` e entre com o usuário e senha do `.env`.
2. *Connections → Data sources → Zabbix* → **Save & test**.
   ✅ Aparece "Zabbix API version: 7.0.x".
   (Se não existir, crie manualmente: tipo **Zabbix**, URL `http://zabbix-web:8080/api_jsonrpc.php`, usuário e senha do Zabbix.)
3. *Dashboards → New → New dashboard → Add visualization → Zabbix*.

Painéis sugeridos para um "telão de NOC":

| Painel | Visualização | Group / Host / Item |
|---|---|---|
| Problemas ativos | **Problems** (Query type: Problems) | todos |
| Site interno no ar? | **Stat** (0 = vermelho, 1 = verde) | Zabbix servers / Zabbix server / Site interno - HTTP no ar |
| CPU dos servidores | **Time series** | `/.*/` / `/.*/` / `/CPU utilization/` |
| Memória usada | **Gauge** | `/.*/` / `/.*/` / `/Memory utilization/` |
| Tráfego de rede da VM | **Time series** | Linux servers / vm-ubuntu-snmp / `/Bits (received|sent)/` |

Dica: no painel Stat, use *Value mappings* (1 → "NO AR", 0 → "FORA") e *Thresholds* com cores.

4. Salve como **"NOC - Empresa X"**.

✅ Print do dashboard completo → `docs/img/dashboard-noc.png`.

---

## Etapa 9 – Simular um incidente (a parte mais importante)

Isso é o que você vai contar na entrevista: **detectar → diagnosticar → resolver → documentar**.

1. Anote a hora e derrube o serviço:
   ```bash
   docker stop web-teste
   ```
2. Espere até cerca de 1 minuto e observe:
   - Telegram: chega o alerta **"Problem: Site interno fora do ar"** → print
   - Zabbix: *Monitoring → Problems* → print
   - Grafana: o painel fica vermelho → print
3. **Diagnostique como se não soubesse a causa:**
   ```bash
   docker ps -a            # o web-teste aparece "Exited"?
   docker logs web-teste   # o que diz o log?
   ```
4. Resolva:
   ```bash
   docker start web-teste
   ```
5. ✅ Chega **"Resolved"** no Telegram e o painel volta ao verde → print
6. Copie `docs/incidentes/TEMPLATE-incidente.md` para `docs/incidentes/INC-0001.md` e preencha com o que **realmente** aconteceu e os horários reais.

Para gravar um GIF da tela, o **ScreenToGif** (Windows, gratuito) funciona bem e GIF chama atenção no LinkedIn.

Ideias de outros incidentes para treinar:
- Desligar a VM Windows ou parar o serviço "Zabbix Agent 2" → alerta de host indisponível
- Encher o disco: `fallocate -l 5G /tmp/lixo` → alerta de espaço (apague depois)
- Estressar a CPU: `sudo apt install stress && stress --cpu 2 --timeout 300`

---

## Etapa 10 – Publicar

1. Preencha a seção **Lições aprendidas** do README com as suas palavras.
2. Coloque os prints em `docs/img/` com os nomes usados no README.
3. Confira que **não há senhas nem tokens** nos arquivos e prints.
4. Envie para o GitHub:
   ```bash
   git add 01-noc-monitoramento
   git commit -m "Projeto 01: NOC com Zabbix + Grafana"
   git push
   ```

**Ideia de post no LinkedIn:**
> Montei um mini NOC em casa 🖥️
> Subi Zabbix + Grafana com Docker, monitorando servidor Linux (agente e SNMP), meu PC Windows e um serviço web.
> Depois derrubei o serviço de propósito: o alerta chegou no Telegram em menos de 1 minuto, diagnostiquei, resolvi e documentei como um chamado real.
> Próximo passo: integrar com um SIEM (Wazuh).
> Repositório: <link>
> #NOC #Zabbix #Grafana #Monitoramento #Infraestrutura

---

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `zbx-server` reiniciando sem parar | Banco ainda criando ou senha errada | `docker compose logs zabbix-server`; espere 2 min; confira o `.env` |
| Página do Zabbix não abre | Porta bloqueada ou IP errado | `docker compose ps`; teste `curl localhost:8080` dentro da VM |
| ZBX vermelho no "Zabbix server" | Interface ainda em 127.0.0.1 | Refaça a Etapa 3 (DNS `zabbix-agent`) |
| SNMP vermelho | snmpd escutando só localhost ou community errada | Confira `agentaddress` e a macro; `sudo ss -ulnp | grep 161` |
| Windows vermelho | Firewall ou IP do servidor errado | Regra da porta 10050; `C:\Program Files\Zabbix Agent 2\zabbix_agent2.conf` → linha `Server=` |
| Grafana "Save & test" falha | Senha do Zabbix mudou | Atualize `ZABBIX_API_PASSWORD` no `.env` e rode `docker compose up -d grafana` |
| Plugin Zabbix não aparece no Grafana | Sem internet na hora do download | `docker compose restart grafana` e veja `docker compose logs grafana` |

**Desligar tudo:** `docker compose down` (mantém os dados) · **Apagar tudo:** `docker compose down -v` (apaga banco e dashboards)
