# Chamado SOC INC-000X – <título curto do alerta>

| Campo | Valor |
|---|---|
| Data/hora da detecção | dd/mm/aaaa hh:mm |
| Fonte | Wazuh (regra XXXX, nível Y) |
| Host afetado | |
| Usuário / IP de origem | |
| Severidade | Baixa / Média / Alta / Crítica |
| Técnica MITRE ATT&CK | TXXXX – <nome> |
| Analista | Ariel Cipriano (SOC N1) |
| Classificação | Falso positivo / Atividade legítima / Incidente |
| Status | Resolvido |

## 1. Alerta
O que o Wazuh detectou (regra, nível, descrição). Cole o print do evento.

<!-- Print do alerta (opcional): ![alerta](../img/inc-000X-alerta.png) -->

## 2. Investigação
O que você verificou, passo a passo (quem, o quê, quando, de onde). Campos do evento: `agent.name`, `rule.id`, `data.srcip`, `data.dstuser`, etc.

## 3. IOCs (indicadores de comprometimento)
Arquivos, hashes, IPs, usuários envolvidos. Se não houver, escreva "nenhum".

## 4. Mapeamento MITRE ATT&CK
Tática e técnica (ex.: Credential Access / T1110 – Brute Force) e por que se encaixa.

## 5. Resposta
O que foi feito (conter, reverter, bloquear, apenas registrar) e por quê.

## 6. Lições aprendidas
O que detectaria isso mais cedo, ou o que evitaria o evento.
