# Runbook de Resposta a Alertas – SOC Empresa X

Procedimento padrão para cada tipo de alerta do Wazuh. Objetivo: qualquer analista N1 investiga e responde (ou escala) seguindo os passos.

**Regra geral para todo alerta**
1. **Triagem:** abra o alerta no dashboard (Threat Hunting → Events) e leia: host, regra, nível, timestamp, usuário, IP de origem.
2. **Classifique** usando o MITRE ATT&CK (a técnica já vem no alerta).
3. **Decida:** falso positivo, atividade legítima ou incidente real.
4. Se for incidente, **contenha** e **escale** conforme a severidade.
5. **Documente** em `docs/incidentes/` com o template.

Onde olhar no dashboard: **Threat Hunting** (busca de eventos), **Security events**, **Agents** (estado dos endpoints), **MITRE ATT&CK** (alertas por técnica).

---

## Brute force / múltiplas falhas de autenticação
**Regra:** 5503 (authentication failed), 5551/5712 (brute force) · **MITRE:** T1110

**Investigação**
- Quantas tentativas, em quanto tempo, de qual IP de origem (`srcip`) e para qual usuário (`dstuser`)?
- O IP é interno (conhecido) ou externo?
- A sequência terminou em **sucesso** (regra 5501/5715)? Se sim, a conta pode estar comprometida.

**Resposta**
- IP externo + muitas tentativas → bloquear o IP no firewall; considerar resposta ativa do Wazuh.
- Terminou em sucesso → **tratar como comprometimento**: forçar troca de senha, revisar o que a conta fez depois, escalar para N2.
- Usuário interno errando a senha → provável esquecimento; confirmar com a pessoa.

---

## Criação ou remoção de conta
**Regra:** 5902 (new user), 5903 (user deleted) · **MITRE:** T1136

**Investigação**
- Quem criou a conta (`sudo`/root)? Estava previsto (mudança aprovada)?
- O nome da conta é suspeito (ex.: parecido com conta de serviço, ou genérico)?

**Resposta**
- Conta não prevista → desabilitar imediatamente, investigar como foi criada (brute force anterior? acesso indevido?), escalar.
- Conta prevista → registrar como atividade legítima e fechar.

---

## Uso de privilégio (sudo) para ação sensível
**Regra:** 5402 (successful sudo) · **MITRE:** T1548

**Investigação**
- Qual comando foi executado com sudo? Leitura de `/etc/shadow`, parada de serviço de segurança, instalação de pacote?
- O usuário tem autorização para isso?

**Resposta**
- Ação legítima de administração → registrar.
- Comando perigoso de usuário sem autorização → escalar para Segurança; pode ser escalonamento de privilégio.

---

## Alteração de arquivo monitorado (FIM)
**Regra:** 550 (arquivo modificado), 554 (arquivo criado) · **MITRE:** T1565

**Investigação**
- Qual arquivo mudou? Em `/etc` (configuração), binário de sistema, arquivo de autenticação?
- A mudança coincide com uma manutenção aprovada?

**Resposta**
- Mudança não prevista em arquivo crítico (`/etc/passwd`, `/etc/sudoers`, `sshd_config`) → **incidente**: comparar com o valor anterior, reverter, escalar.
- Mudança prevista → registrar.

---

## Binário suspeito / execução anômala
**Regra:** rootcheck, FIM em `/tmp` · **MITRE:** T1059

**Investigação**
- Executável em local incomum (`/tmp`, `/dev/shm`), nome oculto (começa com `.`)?
- Quem criou, quando, e o arquivo ainda está lá?

**Resposta**
- Binário desconhecido em `/tmp` → **não execute**; colete o hash (IOC), isole o host se necessário, escale para Segurança.

---

## Agente desconectado
**Sintoma:** em Agents, o endpoint aparece **Disconnected** ou **Never connected**.

**Investigação (no endpoint)**
```bash
systemctl status wazuh-agent
journalctl -u wazuh-agent -n 30 --no-pager
```
**Resposta**
- Serviço parado → `systemctl restart wazuh-agent`.
- Firewall bloqueando 1514/1515 → liberar no caminho até o manager.
- "Angola de atenção": um agente sumir pode ser falha **ou** alguém tentando se esconder; investigue antes de descartar.

---

## Severidade e escalonamento (exemplo do lab)
| Nível Wazuh | Significado | Ação |
|---|---|---|
| 0–4 | Informativo | Registrar, sem ação |
| 5–9 | Atenção | Investigar na triagem |
| 10–12 | Importante | Investigar com prioridade; conter se confirmado |
| 13–15 | Crítico | Conter imediatamente e escalar para N2/Segurança |
