# 🛡️ Security & Network Portfolio — Home Lab

Portfólio prático de **SOC / NOC / Infraestrutura** construído em home lab, com um cenário único e contínuo: a **"Empresa X"** (matriz + filial, fictícia). Cada projeto é um bloco real de operação — monitoramento, segurança, banco de dados, identidade, rede e cloud — entregue com **infra como código, documentação e evidências (prints)**.

> Foco: nível **júnior** para vagas de **SOC N1 · NOC · Infraestrutura · Suporte**. Um projeto por vez, do simples ao intermediário.

## 📍 Roadmap

| # | Projeto | Área | Stack principal | Status |
|---|---------|------|-----------------|--------|
| 01 | **[NOC – Monitoramento](01-noc-monitoramento)** | NOC / Observabilidade | Zabbix, Grafana, Docker, SNMP | ✅ **Concluído** |
| 02 | Banco de Dados – App de Ofícios | Banco de Dados | MySQL, Docker, Flask, backup/restore | ⏳ Planejado |
| 03 | Gestão de Identidade | IAM | Windows AD, PowerShell, Keycloak, MFA | ⏳ Planejado |
| 04 | **[SOC – SIEM/XDR](04-soc-wazuh)** | SOC | Wazuh, MITRE ATT&CK, Docker | ✅ **Concluído** |
| 05 | Perímetro – Firewall/IDS | Segurança de Rede | pfSense, Suricata, VLANs, DMZ | ⏳ Planejado |
| 06 | Redes – Roteamento | Infra / Redes | Containerlab, FRRouting, OSPF, BGP | ⏳ Planejado |
| 07 | Cloud – AWS | Cloud | VPC, EC2, RDS, IAM, GuardDuty, Terraform | ⏳ Planejado |

## ✅ Projetos concluídos

### 01 · NOC — Monitoramento com Zabbix + Grafana
Monitora a VM, um serviço web e a rede (agente + SNMP), com **alertas, dashboards gerados por código, runbook e incidentes documentados**. Sobe com um comando e se autoconfigura via API Zabbix ("monitoramento como código").
**Demonstra:** monitoramento, triagem de alertas, registro de chamado, dashboard como código.
→ [`01-noc-monitoramento/`](01-noc-monitoramento)

### 04 · SOC — Detecção e Resposta com Wazuh (SIEM/XDR)
A **mesma** VM do NOC vira endpoint monitorado por um SIEM: coleta de logs, detecção, **mapeamento no MITRE ATT&CK** e investigação de cada alerta no padrão de um analista N1 (detectar → investigar → responder → documentar).
**Demonstra:** análise de alertas, investigação, resposta e documentação de incidente — o núcleo do SOC N1.
→ [`04-soc-wazuh/`](04-soc-wazuh)

> 🔗 Os projetos 01 e 04 se conectam: a VM `noc-lab` é vista pelo **Zabbix** (disponibilidade/NOC) **e** pelo **Wazuh** (segurança/SOC) ao mesmo tempo, como numa empresa real.

## 🧰 Competências demonstradas
Linux (Ubuntu Server) · Docker & Docker Compose · Monitoramento (Zabbix, Grafana, SNMP) · SIEM/XDR (Wazuh) · MITRE ATT&CK · Infra como código · Python & Bash · Documentação técnica e de incidentes (ITSM/SOC) · Virtualização (VirtualBox)

## 💻 Lab
Ryzen 3 3200G (4 núcleos) · 16 GB RAM · RX 550 — VMs em VirtualBox, Ubuntu Server sem interface gráfica para economizar recursos.

## 🔒 Observação de segurança
Este é um laboratório de estudo: alguns serviços usam **credenciais padrão** (documentadas nos READMEs de cada projeto) para facilitar o aprendizado. Elas **devem ser trocadas** antes de qualquer uso fora de um ambiente isolado. Segredos reais ficam fora do Git (`.env`/`.gitignore`).

---
Autor: **Ariel Cipriano** · [LinkedIn](https://linkedin.com/in/ariel-cipriano) · [GitHub](https://github.com/Cipriano2004)
