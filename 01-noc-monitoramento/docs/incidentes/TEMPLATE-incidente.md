# Chamado INC-000X – <título curto do problema>

| Campo | Valor |
|---|---|
| Data/hora da abertura | dd/mm/aaaa hh:mm |
| Aberto por | Alerta automático do Zabbix (Telegram) |
| Severidade | Alta / Média / Baixa |
| Serviço afetado | |
| Responsável | Ariel Cipriano (NOC) |
| Status | Resolvido |
| Data/hora da resolução | dd/mm/aaaa hh:mm |
| Tempo até resolver | xx min |

## 1. Alerta recebido
O que chegou no Telegram / apareceu no painel de Problemas do Zabbix (cole o print).

<!-- Print do alerta (opcional): ![alerta](../img/inc-000X-alerta.png) -->

## 2. Impacto
Quem ou o que ficou sem funcionar? (ex.: "site interno fora do ar para todos os usuários")

## 3. Diagnóstico (passo a passo do que você verificou)
1. Conferi no Zabbix qual item disparou: …
2. Testei manualmente: `comando que você rodou` → resultado
3. Verifiquei o estado do serviço: `docker ps -a` → …
4. Causa encontrada: …

## 4. Solução aplicada
Comandos ou ações que resolveram.

## 5. Validação
Como você confirmou que voltou (alerta de "Resolvido" no Telegram, gráfico normalizado no Grafana).

<!-- Print após resolução (opcional): ![resolvido](../img/inc-000X-resolvido.png) -->

## 6. Lições aprendidas / prevenção
O que poderia evitar que isso aconteça de novo? (ex.: reinício automático, alerta mais cedo, redundância)
