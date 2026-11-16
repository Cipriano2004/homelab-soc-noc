"""
Configuração automática do Zabbix via API (Zabbix 7.0) – "monitoramento como código".

Roda uma vez quando o ambiente sobe (serviço `zabbix-setup` do docker-compose).
É idempotente: se algo já existe, ele não duplica. Pode rodar quantas vezes quiser.

O que ele cria:
  - Grupo de hosts "Empresa X"
  - Host "vm-noc-lab"        → a própria VM, monitorada por Zabbix Agent 2
  - Host "vm-noc-lab-snmp"   → a mesma VM, monitorada por SNMP v2c (prática de NOC)
  - Host "site-interno"      → o serviço web da empresa (container web-teste):
        * item: porta HTTP no ar (simple check)
        * item: tempo de resposta (simple check)
        * cenário web (HTTP 200 + tempo de download)
        * triggers: fora do ar (High), lento (Warning), cenário web falhou (Average)
  - (Opcional) Alertas no Telegram, se TELEGRAM_TOKEN e TELEGRAM_CHAT_ID estiverem no .env

Só usa a biblioteca padrão do Python (sem pip install).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = os.environ.get("ZBX_API_URL", "http://zabbix-web:8080/api_jsonrpc.php")
API_USER = os.environ.get("ZBX_API_USER", "Admin")
API_PASS = os.environ.get("ZBX_API_PASSWORD", "zabbix")

# A VM é alcançada pelo gateway da rede Docker "noc" (subnet fixa no docker-compose)
VM_IP = os.environ.get("VM_IP_FROM_DOCKER", "172.30.0.1")
SNMP_COMMUNITY = os.environ.get("SNMP_COMMUNITY", "lab-noc-ro")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

GROUP_NAME = "Empresa X"
TOKEN = None
_req_id = 0


def log(msg):
    print(f"[setup] {msg}", flush=True)


def api(method, params=None, auth=True):
    """Chama a API JSON-RPC do Zabbix e devolve o 'result'."""
    global _req_id
    _req_id += 1
    body = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": _req_id}
    headers = {"Content-Type": "application/json-rpc"}
    if auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"{method}: {err.get('message')} {err.get('data')}")
    return data["result"]


def wait_for_api(timeout=600):
    log(f"Aguardando a API do Zabbix em {API_URL} ...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            version = api("apiinfo.version", auth=False)
            log(f"API respondeu. Versão do Zabbix: {version}")
            return
        except (urllib.error.URLError, ConnectionError, RuntimeError, OSError, json.JSONDecodeError):
            time.sleep(5)
    log("ERRO: a API não respondeu a tempo.")
    sys.exit(1)


def login():
    global TOKEN
    # O frontend pode responder antes do banco terminar de ser criado: tenta algumas vezes.
    for attempt in range(1, 31):
        try:
            TOKEN = api("user.login", {"username": API_USER, "password": API_PASS}, auth=False)
            log("Login na API feito.")
            return
        except Exception as exc:  # noqa: BLE001
            log(f"Login ainda não disponível (tentativa {attempt}): {exc}")
            time.sleep(10)
    log("ERRO: não consegui logar. Confira ZABBIX_API_USER/ZABBIX_API_PASSWORD no .env")
    sys.exit(1)


# ---------------------------------------------------------------- helpers

def get_or_create_group(name):
    found = api("hostgroup.get", {"filter": {"name": [name]}, "output": ["groupid"]})
    if found:
        return found[0]["groupid"]
    gid = api("hostgroup.create", {"name": name})["groupids"][0]
    log(f"Grupo criado: {name}")
    return gid


def group_id(name):
    found = api("hostgroup.get", {"filter": {"name": [name]}, "output": ["groupid"]})
    return found[0]["groupid"] if found else None


def template_id(name):
    found = api("template.get", {"filter": {"host": [name]}, "output": ["templateid"]})
    if not found:
        log(f"AVISO: template '{name}' não encontrado.")
        return None
    return found[0]["templateid"]


def get_host(name):
    found = api("host.get", {"filter": {"host": [name]}, "output": ["hostid"],
                             "selectInterfaces": ["interfaceid", "type"]})
    return found[0] if found else None


def ensure_host(name, visible, groups, templates, interfaces, macros=None, description=""):
    host = get_host(name)
    if host:
        log(f"Host já existe: {name}")
        return host["hostid"]
    params = {
        "host": name,
        "name": visible,
        "description": description,
        "groups": [{"groupid": g} for g in groups if g],
        "templates": [{"templateid": t} for t in templates if t],
        "interfaces": interfaces,
    }
    if macros:
        params["macros"] = macros
    hid = api("host.create", params)["hostids"][0]
    log(f"Host criado: {name}")
    return hid


def ensure_item(hostid, key, params):
    found = api("item.get", {"hostids": hostid, "filter": {"key_": key}, "output": ["itemid"]})
    if found:
        log(f"Item já existe: {key}")
        return found[0]["itemid"]
    params = dict(params, hostid=hostid, key_=key)
    iid = api("item.create", params)["itemids"][0]
    log(f"Item criado: {params['name']}")
    return iid


def ensure_trigger(description, expression, priority, comments="", tags=None):
    found = api("trigger.get", {"filter": {"description": description}, "output": ["triggerid"]})
    if found:
        log(f"Trigger já existe: {description}")
        return found[0]["triggerid"]
    params = {"description": description, "expression": expression,
              "priority": priority, "comments": comments}
    if tags:
        params["tags"] = tags
    tid = api("trigger.create", params)["triggerids"][0]
    log(f"Trigger criado: {description}")
    return tid


# ---------------------------------------------------------------- configuração

def configure_hosts():
    gid = get_or_create_group(GROUP_NAME)
    linux_gid = group_id("Linux servers")

    # 1) A VM via Zabbix Agent 2 (container com rede do host)
    ensure_host(
        "vm-noc-lab", "VM noc-lab (agente)",
        [gid, linux_gid],
        [template_id("Linux by Zabbix agent")],
        [{"type": 1, "main": 1, "useip": 1, "ip": VM_IP, "dns": "", "port": "10050"}],
        description="VM Ubuntu Server do lab NOC, monitorada por Zabbix Agent 2.",
    )

    # 2) A mesma VM via SNMP v2c
    ensure_host(
        "vm-noc-lab-snmp", "VM noc-lab (SNMP)",
        [gid, linux_gid],
        [template_id("Linux by SNMP")],
        [{"type": 2, "main": 1, "useip": 1, "ip": VM_IP, "dns": "", "port": "161",
          "details": {"version": 2, "bulk": 1, "community": "{$SNMP_COMMUNITY}"}}],
        macros=[{"macro": "{$SNMP_COMMUNITY}", "value": SNMP_COMMUNITY}],
        description="Mesma VM monitorada por SNMP v2c (em produção use SNMPv3).",
    )

    # 3) O "serviço da empresa": site interno (container web-teste)
    site_id = ensure_host(
        "site-interno", "Site interno (web-teste)",
        [gid],
        [],
        [{"type": 1, "main": 1, "useip": 0, "ip": "", "dns": "web-teste", "port": "10050"}],
        description="Serviço web interno da Empresa X. Usado para simular incidentes.",
    )
    iface = get_host("site-interno")["interfaces"][0]["interfaceid"]

    ensure_item(site_id, "net.tcp.service[http,web-teste,80]", {
        "name": "Site interno: HTTP no ar", "type": 3, "value_type": 3,
        "delay": "30s", "interfaceid": iface,
        "description": "1 = porta 80 respondeu, 0 = fora do ar",
        "tags": [{"tag": "component", "value": "web"}],
    })
    ensure_item(site_id, "net.tcp.service.perf[http,web-teste,80]", {
        "name": "Site interno: tempo de resposta", "type": 3, "value_type": 0,
        "units": "s", "delay": "30s", "interfaceid": iface,
        "tags": [{"tag": "component", "value": "web"}],
    })

    # Cenário web (HTTP 200)
    found = api("httptest.get", {"hostids": site_id, "filter": {"name": "Site interno"},
                                 "output": ["httptestid"]})
    if not found:
        api("httptest.create", {
            "name": "Site interno", "hostid": site_id, "delay": "1m", "retries": 1,
            "steps": [{"name": "Página inicial", "url": "http://web-teste/",
                       "status_codes": "200", "no": 1}],
            "tags": [{"tag": "component", "value": "web"}],
        })
        log("Cenário web criado: Site interno")
    else:
        log("Cenário web já existe: Site interno")

    ensure_trigger(
        "Site interno fora do ar",
        "last(/site-interno/net.tcp.service[http,web-teste,80])=0",
        4,
        comments="Ver runbook: docs/RUNBOOK.md#site-interno-fora-do-ar",
        tags=[{"tag": "scope", "value": "availability"}],
    )
    ensure_trigger(
        "Site interno lento (resposta média > 0,5s em 2 min)",
        "avg(/site-interno/net.tcp.service.perf[http,web-teste,80],2m)>0.5",
        2,
        comments="Ver runbook: docs/RUNBOOK.md#site-interno-lento",
        tags=[{"tag": "scope", "value": "performance"}],
    )
    ensure_trigger(
        "Site interno: cenário web falhou",
        "last(/site-interno/web.test.fail[Site interno])<>0",
        3,
        comments="Ver runbook: docs/RUNBOOK.md#cenario-web-falhou",
        tags=[{"tag": "scope", "value": "availability"}],
    )


def configure_telegram():
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        log("Telegram não configurado (TELEGRAM_TOKEN/TELEGRAM_CHAT_ID vazios no .env) – pulando.")
        return
    try:
        mt = api("mediatype.get", {"filter": {"name": "Telegram"},
                                   "output": ["mediatypeid"], "selectParameters": "extend"})
        if not mt:
            log("AVISO: media type 'Telegram' não encontrado.")
            return
        mtid = mt[0]["mediatypeid"]
        params = [{"name": p["name"], "value": p["value"]} for p in mt[0]["parameters"]]
        for p in params:
            if p["name"] in ("api_token", "Token"):
                p["value"] = TELEGRAM_TOKEN
        api("mediatype.update", {"mediatypeid": mtid, "status": 0, "parameters": params})
        log("Media type Telegram ativado.")

        admin = api("user.get", {"filter": {"username": API_USER}, "output": ["userid"],
                                 "selectMedias": ["mediatypeid", "sendto"]})[0]
        medias = [m for m in admin.get("medias", []) if m["mediatypeid"] != mtid]
        medias = [{"mediatypeid": m["mediatypeid"], "sendto": m["sendto"]} for m in medias]
        medias.append({"mediatypeid": mtid, "sendto": TELEGRAM_CHAT_ID, "active": 0,
                       "severity": 63, "period": "1-7,00:00-24:00"})
        api("user.update", {"userid": admin["userid"], "medias": medias})
        log("Chat do Telegram vinculado ao usuário.")

        name = "Alertas NOC - Telegram"
        if api("action.get", {"filter": {"name": name}, "output": ["actionid"]}):
            log("Ação de alerta já existe.")
            return
        api("action.create", {
            "name": name, "eventsource": 0, "status": 0, "esc_period": "1h",
            "filter": {"evaltype": 0, "conditions": [
                {"conditiontype": 4, "operator": 5, "value": "2"}]},  # severidade >= Warning
            "operations": [{"operationtype": 0, "esc_step_from": 1, "esc_step_to": 1,
                            "opmessage": {"default_msg": 1, "mediatypeid": mtid},
                            "opmessage_usr": [{"userid": admin["userid"]}]}],
            "recovery_operations": [{"operationtype": 11,
                                     "opmessage": {"default_msg": 1}}],
        })
        log("Ação 'Alertas NOC - Telegram' criada.")
    except Exception as exc:  # noqa: BLE001
        log(f"AVISO: não consegui configurar o Telegram automaticamente: {exc}")


def main():
    wait_for_api()
    login()
    configure_hosts()
    configure_telegram()
    log("Configuração concluída com sucesso. ✅")


if __name__ == "__main__":
    main()
