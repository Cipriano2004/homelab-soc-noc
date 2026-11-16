# Guia passo a passo – Projeto 04 SOC (Wazuh)

Guia para quem está começando. Cada etapa tem **o que fazer**, **por quê** e **✅ como saber se deu certo**. Tire prints em cada ✅ e salve em `docs/img/`.

**Pré-requisitos:** ter o [Projeto 01 – NOC](../01-noc-monitoramento) rodando (a VM `noc-lab` vira o endpoint monitorado).

---

## Etapa 0 – A VM do SOC

Crie uma VM **separada** só para o Wazuh, porque ele é pesado:
- Ubuntu Server 24.04, **6 GB de RAM**, 2 vCPU, **50 GB** de disco (o Wazuh guarda muito log).
- Rede em **Bridge** (IP próprio na rede).
- Na instalação: **desmarque LVM** (deixa o disco inteiro para o sistema) e marque **Install OpenSSH server**.

Depois de instalar, descubra o IP: `ip -br a`. No guia ele aparece como `IP_DA_SOC`.

> **Por que outra VM?** Misturar o SIEM (que consome muita RAM) com o endpoint monitorado atrapalha os dois. Em produção, o SOC fica sempre separado do que ele vigia.

---

## Etapa 1 – Subir o Wazuh

O Wazuh single-node tem três peças: **Manager** (analisa e alerta), **Indexer** (OpenSearch, guarda e busca) e **Dashboard** (a interface).

Copie o projeto para a VM e rode o instalador:
```bash
sudo -i
cd /caminho/do/projeto/scripts
bash instalar-soc.sh
```
O script faz tudo: Docker, ajuste de kernel, certificados TLS e sobe os containers.

**O que o `vm.max_map_count=262144` faz?** O Indexer é baseado em OpenSearch/Elasticsearch, que exige esse limite de memória mapeada do kernel. Sem ele, o container reinicia em loop. É o erro nº 1 de quem sobe Wazuh ou Elastic pela primeira vez.

✅ `docker compose ps` mostra `wazuh.manager`, `wazuh.indexer` e `wazuh.dashboard` como **Up**.

---

## Etapa 2 – Primeiro acesso ao dashboard

1. No navegador: `https://IP_DA_SOC` (com **https**). Aceite o aviso de certificado (é autoassinado, normal no lab).
2. Espere ~2 minutos depois da página abrir: o Indexer ainda está inicializando.
3. Login inicial: **admin / SecretPassword**.
4. **Troque a senha** depois (as senhas padrão estão nos arquivos `config/` e no `docker-compose.yml`).

✅ Você vê o menu do Wazuh: Endpoint security, Threat intelligence, Agents management, etc.

---

## Etapa 3 – Conectar um endpoint (agente na noc-lab)

O **agente** é instalado na máquina que você quer vigiar e envia os eventos para o manager.

Na VM **noc-lab**, como root:
```bash
bash instalar-agente.sh 192.168.2.192 noc-lab
#                        ^IP do manager  ^nome do agente
```
O script adiciona o repositório oficial do Wazuh, instala o agente, **trava a versão** (`apt-mark hold`) e ativa o serviço.

**Por que travar a versão?** O agente **nunca** pode ser mais novo que o manager, ou para de reportar. O `apt-mark hold` evita que um `apt upgrade` quebre isso.

✅ `systemctl is-active wazuh-agent` responde `active`.
✅ No dashboard, em **Agents**, a `noc-lab` aparece como **Active**.

> **Enrollment:** na primeira conexão, o agente se registra sozinho no manager pela porta **1515**. Depois, os eventos vão pela porta **1514**.

---

## Etapa 4 – Gerar alertas e investigar

Os testes geram eventos benignos de administração que, num endpoint monitorado, viram alerta. Rode **dentro da noc-lab**, como root:
```bash
bash testar-deteccoes.sh        # menu
bash testar-deteccoes.sh 1      # direto
```

| Teste | O que faz | Técnica MITRE |
|---|---|---|
| 1 | 5 falhas de autenticação | T1110 – Brute Force |
| 2 | Criar e remover usuário | T1136 – Create Account |
| 3 | sudo lendo /etc/shadow | T1548 – Abuse Elevation |
| 4 | Alterar arquivo monitorado (FIM) | T1565 – Data Manipulation |
| 5 | Binário escondido em /tmp | T1059 – Command and Scripting |

**Depois de cada teste**, no dashboard: **Threat Hunting → Events** (ou Security events), filtre pelo agente `noc-lab` e pelos últimos minutos. Clique no evento para ver os campos (`rule.id`, `rule.level`, `data.dstuser`, etc.).

✅ O evento aparece com a regra e o nível esperados.

> O FIM (teste 4) roda periodicamente; o alerta pode levar alguns minutos. Para ver na hora: `systemctl restart wazuh-agent`.

---

## Etapa 5 – Investigar como um analista (o que mais importa)

Para cada alerta, siga o [RUNBOOK](docs/RUNBOOK.md):
1. **Triagem:** host, regra, nível, usuário, origem.
2. **Classifique** no MITRE ATT&CK (a técnica já vem no alerta).
3. **Decida:** falso positivo, legítimo ou incidente.
4. **Responda** conforme a severidade.
5. **Documente** em `docs/incidentes/` usando o template.

O `INC-0001.md` já está preenchido com o teste de brute force; use-o de modelo para escrever INC-0002 a INC-0005 (um por teste).

---

## Etapa 6 – Publicar

1. Preencha "Lições aprendidas" do README com as suas palavras.
2. Coloque os prints em `docs/img/` (dashboard, agente Active, um evento, a aba MITRE ATT&CK).
3. Confira que **não há senhas** nos prints.
4. Suba para o GitHub, no `security-network-portfolio`.

**Ideia de post no LinkedIn:**
> Montei um SOC em casa 🛡️
> Subi o Wazuh (SIEM/XDR) com Docker e conectei um agente num endpoint Linux.
> Gerei eventos de segurança controlados (brute force, criação de usuário, FIM...) e investiguei cada alerta: do evento ao IOC e à técnica MITRE ATT&CK, documentando como um chamado de SOC.
> Agora a mesma máquina é monitorada pelo meu NOC (Zabbix) e pelo meu SOC (Wazuh).
> #SOC #Wazuh #BlueTeam #MITREATTACK #Cybersecurity

---

## Problemas comuns

| Sintoma | Causa | Solução |
|---|---|---|
| Indexer reiniciando em loop | `vm.max_map_count` baixo | O script já ajusta; confira `sysctl vm.max_map_count` (deve ser 262144) |
| Dashboard não loga (erro de conexão) | Indexer ainda subindo | Espere ~2 min e atualize |
| Agente aparece "Never connected" | Firewall ou IP errado | Libere 1514/1515 até o manager; confira o IP no agente |
| Agente "Disconnected" | Serviço parado | `systemctl restart wazuh-agent` |
| Alerta de FIM não aparece | Syscheck roda periódico | `systemctl restart wazuh-agent` força a verificação |

**Desligar:** na VM, `poweroff` (para os containers em ordem). **Parar só o Wazuh:** `docker compose down` (mantém os dados nos volumes).
