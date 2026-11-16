"""
Gera os dashboards do Grafana (JSON) a partir de código.
Uso:  python3 grafana/gerar_dashboards.py
Saída: grafana/dashboards/*.json  (carregados automaticamente pelo Grafana)

Paleta (tema escuro):
  séries  -> azul #3987e5, laranja #d95926, água #199e70, amarelo #c98500 (ordem fixa)
  estados -> bom #0ca30c, atenção #fab219, sério #ec835a, crítico #d03b3b (só para status)
"""
import json
import os

DS = {"type": "alexanderzobnin-zabbix-datasource", "uid": "zabbix"}
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500"]
GOOD, WARN, SERIOUS, CRIT = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
TEXT = "#c3c2b7"

OUT = os.path.join(os.path.dirname(__file__), "dashboards")

_pid = 0


def pid():
    global _pid
    _pid += 1
    return _pid


def target(group, host, item, ref="A", query_type="0", **extra):
    t = {
        "datasource": DS, "refId": ref, "queryType": query_type,
        "group": {"filter": group}, "host": {"filter": host},
        "application": {"filter": ""}, "item": {"filter": item},
        "itemTag": {"filter": ""}, "proxy": {"filter": ""}, "trigger": {"filter": ""},
        "tags": {"filter": ""}, "macro": {"filter": ""}, "functions": [],
        "resultFormat": "time_series", "schema": 12, "countTriggersBy": "",
        "evaltype": "0", "textFilter": "", "table": {"skipEmptyValues": False},
        "triggers": {"acknowledged": 2},
        "options": {"showDisabledItems": False, "skipEmptyValues": False,
                    "disableDataAlignment": False, "useTrends": "default",
                    "useZabbixValueMapping": False, "count": False,
                    "minSeverity": 0},
    }
    t.update(extra)
    return t


def thresholds(*steps):
    """steps: (valor ou None, cor)"""
    return {"mode": "absolute",
            "steps": [{"value": v, "color": c} for v, c in steps]}


def stat(title, x, y, w, h, targets, unit="none", steps=None, mappings=None,
         color_mode="value", graph="none", decimals=None, desc="", calcs=None):
    p = {
        "id": pid(), "type": "stat", "title": title, "description": desc,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": {
            "unit": unit, "color": {"mode": "thresholds"},
            "thresholds": steps or thresholds((None, TEXT)),
            "mappings": mappings or []}, "overrides": []},
        "options": {"reduceOptions": {"calcs": calcs or ["lastNotNull"], "fields": "",
                                      "values": False},
                    "colorMode": color_mode, "graphMode": graph, "justifyMode": "center",
                    "textMode": "value", "orientation": "auto", "wideLayout": True,
                    "showPercentChange": False},
    }
    if decimals is not None:
        p["fieldConfig"]["defaults"]["decimals"] = decimals
    return p


def gauge(title, x, y, w, h, targets, desc=""):
    return {
        "id": pid(), "type": "gauge", "title": title, "description": desc,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": {
            "unit": "percent", "min": 0, "max": 100, "decimals": 1,
            "color": {"mode": "thresholds"},
            "thresholds": thresholds((None, GOOD), (70, WARN), (90, CRIT))},
            "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "showThresholdMarkers": True, "showThresholdLabels": False,
                    "minVizHeight": 75, "minVizWidth": 75, "sizing": "auto"},
    }


def timeseries(title, x, y, w, h, targets, unit, overrides=None, fill=12,
               steps=None, threshold_style="off", desc="", legend="list"):
    return {
        "id": pid(), "type": "timeseries", "title": title, "description": desc,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": {
            "unit": unit, "color": {"mode": "palette-classic"},
            "custom": {"drawStyle": "line", "lineWidth": 2, "fillOpacity": fill,
                       "gradientMode": "opacity", "lineInterpolation": "smooth",
                       "showPoints": "never", "spanNulls": True,
                       "axisBorderShow": False, "axisPlacement": "auto",
                       "thresholdsStyle": {"mode": threshold_style}},
            "thresholds": steps or thresholds((None, GOOD))},
            "overrides": overrides or []},
        "options": {"legend": {"displayMode": legend, "placement": "bottom", "showLegend": True,
                               "calcs": ["lastNotNull", "max"] if legend == "table" else []},
                    "tooltip": {"mode": "multi", "sort": "desc"}},
    }


def color_override(regex, color, name=None, extra=None):
    props = [{"id": "color", "value": {"mode": "fixed", "fixedColor": color}}]
    if name:
        props.append({"id": "displayName", "value": name})
    props += extra or []
    return {"matcher": {"id": "byRegexp", "options": regex}, "properties": props}


def problems_panel(title, x, y, w, h, group="/.*/", host="/.*/"):
    t = target(group, host, "", query_type="5", showProblems="problems",
               resultFormat="table")
    t["options"].update({"acknowledged": 2, "limit": 1001, "useTimeRange": False,
                         "fetchHistoricalItemValue": True, "sortProblems": "default"})
    sev = [("Not classified", "rgb(108, 108, 108)"), ("Information", "rgb(120, 158, 183)"),
           ("Warning", WARN), ("Average", SERIOUS), ("High", CRIT), ("Disaster", "#8e1e1e")]
    return {
        "id": pid(), "type": "alexanderzobnin-zabbix-triggers-panel", "title": title,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [t],
        "options": {
            "layout": "table", "pageSize": 10, "fontSize": "100%",
            "hostField": True, "hostTechNameField": False, "hostGroups": False,
            "hostProxy": False, "severityField": True, "statusField": True,
            "statusIcon": False, "ageField": True, "ackField": True, "showTags": True,
            "descriptionField": True, "descriptionAtNewLine": False, "opdataField": False,
            "problemTimeline": True, "highlightBackground": False,
            "highlightNewEvents": True, "highlightNewerThan": "15m",
            "markAckEvents": False, "sortProblems": "lastchange",
            "okEventColor": GOOD, "ackEventColor": "rgb(56, 219, 156)",
            "customLastChangeFormat": False, "lastChangeFormat": "",
            "allowDangerousHTML": False, "resizedColumns": [], "showDatasourceName": False,
            "triggerSeverity": [{"priority": i, "severity": s, "color": c, "show": True}
                                for i, (s, c) in enumerate(sev)],
        },
    }


def row(title, y):
    return {"id": pid(), "type": "row", "title": title, "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def dashboard(uid, title, panels, desc, templating=None, time_from="now-3h"):
    return {
        "uid": uid, "title": title, "description": desc,
        "tags": ["noc", "zabbix", "empresa-x"], "timezone": "browser",
        "editable": True, "graphTooltip": 1, "refresh": "30s",
        "time": {"from": time_from, "to": "now"},
        "timepicker": {"refresh_intervals": ["10s", "30s", "1m", "5m"]},
        "schemaVersion": 39, "version": 1, "style": "dark",
        "templating": {"list": templating or []},
        "annotations": {"list": []},
        "links": [{"title": "Dashboards NOC", "type": "dashboards", "tags": ["noc"],
                   "asDropdown": True}],
        "panels": panels,
    }


# ------------------------------------------------------------------ Visão geral
def visao_geral():
    global _pid
    _pid = 0
    # O plugin do Zabbix filtra hosts pelo NOME VISÍVEL (não pelo nome técnico)
    EX = "Empresa X"
    VM, SNMP, SITE = "VM noc-lab (agente)", "VM noc-lab (SNMP)", "Site interno (web-teste)"
    up_map = [{"type": "value", "options": {
        "1": {"text": "● NO AR", "color": GOOD, "index": 0},
        "0": {"text": "✖ FORA DO AR", "color": CRIT, "index": 1}}}]
    p = []
    p.append(row("Status agora", 0))
    p.append(stat("Site interno", 0, 1, 4, 5,
                  [target(EX, SITE, "Site interno: HTTP no ar")],
                  mappings=up_map, color_mode="background",
                  steps=thresholds((None, CRIT), (1, GOOD)),
                  desc="Checagem da porta 80 do serviço web a cada 30s."))
    # O Zabbix grava 0 quando o site não responde: mostramos "sem resposta" em vermelho
    sem_resp = [{"type": "value", "options": {
        "0": {"text": "sem resposta", "color": CRIT, "index": 0}}}]
    p.append(stat("Tempo de resposta", 4, 1, 3, 5,
                  [target(EX, SITE, "Site interno: tempo de resposta")],
                  unit="s", decimals=0, graph="area", mappings=sem_resp,
                  steps=thresholds((None, GOOD), (0.3, WARN), (0.5, CRIT)),
                  desc="Tempo para abrir conexão HTTP com o site interno."))
    p.append(stat("Disponibilidade (SLA)", 7, 1, 3, 5,
                  [target(EX, SITE, "Site interno: HTTP no ar")],
                  unit="percentunit", decimals=2, calcs=["mean"],
                  steps=thresholds((None, CRIT), (0.99, WARN), (0.999, GOOD)),
                  desc="% do tempo em que o site ficou no ar no período selecionado no topo. "
                       "Meta: 99,9% (verde). Abaixo de 99% fica vermelho."))
    cnt = target("/.*/", "/.*/", "", query_type="4")
    cnt["options"].update({"count": True, "minSeverity": 2, "acknowledged": 2})
    p.append(stat("Problemas ativos", 10, 1, 3, 5, [cnt], color_mode="background",
                  steps=thresholds((None, GOOD), (1, WARN), (3, CRIT)), decimals=0,
                  desc="Triggers em problema com severidade Warning ou maior."))
    p.append(gauge("CPU da VM", 13, 1, 4, 5, [target(EX, VM, "CPU utilization")]))
    p.append(gauge("Memória da VM", 17, 1, 4, 5, [target(EX, VM, "Memory utilization")]))
    p.append(stat("Uptime da VM", 21, 1, 3, 5, [target(EX, VM, "System uptime")],
                  unit="dtdurations", decimals=0))

    p.append(problems_panel("Problemas em aberto", 0, 6, 24, 8))

    p.append(row("Serviço: site interno", 14))
    p.append(timeseries(
        "Tempo de resposta do site", 0, 15, 12, 8,
        [target(EX, SITE, "Site interno: tempo de resposta")], "s",
        overrides=[color_override(".*", SERIES[0], "Tempo de resposta")],
        steps=thresholds((None, "transparent"), (0.5, CRIT)), threshold_style="dashed",
        desc="Linha tracejada vermelha = limite do trigger 'site lento' (0,5s)."))
    tl = {
        "id": pid(), "type": "state-timeline", "title": "Disponibilidade do site",
        "datasource": DS, "gridPos": {"x": 12, "y": 15, "w": 12, "h": 8},
        "targets": [target(EX, SITE, "Site interno: HTTP no ar")],
        "fieldConfig": {"defaults": {
            "color": {"mode": "thresholds"},
            "thresholds": thresholds((None, CRIT), (1, GOOD)),
            "mappings": up_map, "custom": {"lineWidth": 0, "fillOpacity": 85}},
            "overrides": [{"matcher": {"id": "byRegexp", "options": ".*"},
                           "properties": [{"id": "displayName", "value": "Site interno"}]}]},
        "options": {"showValue": "never", "rowHeight": 0.8, "mergeValues": True,
                    "alignValue": "left", "legend": {"showLegend": False, "displayMode": "list",
                                                     "placement": "bottom"},
                    "tooltip": {"mode": "single"}},
    }
    p.append(tl)

    p.append(row("Infraestrutura: VM noc-lab", 23))
    p.append(timeseries(
        "CPU e memória da VM (%)", 0, 24, 12, 8,
        [target(EX, VM, "CPU utilization", "A"), target(EX, VM, "Memory utilization", "B")],
        "percent",
        overrides=[color_override(".*CPU utilization.*", SERIES[0], "CPU"),
                   color_override(".*Memory utilization.*", SERIES[1], "Memória")],
        steps=thresholds((None, "transparent"), (90, CRIT)), threshold_style="dashed"))
    p.append(timeseries(
        "Tráfego de rede da VM (SNMP)", 12, 24, 12, 8,
        [target(EX, SNMP, "/enp0s3.*Bits (received|sent)/")], "bps",
        overrides=[color_override(".*Bits received.*", SERIES[0], "Download (recebido)"),
                   color_override(".*Bits sent.*", SERIES[1], "Upload (enviado)",
                                  [{"id": "custom.transform", "value": "negative-Y"}])],
        desc="Coletado por SNMP v2c. Upload aparece abaixo do zero para facilitar a leitura."))
    p.append(timeseries(
        "Carga do sistema (load average)", 0, 32, 12, 8,
        [target(EX, VM, "/Load average \\((1|5)m avg\\)/")], "short",
        overrides=[color_override(".*1m avg.*", SERIES[0], "1 minuto"),
                   color_override(".*5m avg.*", SERIES[1], "5 minutos")], fill=0))
    p.append({
        "id": pid(), "type": "bargauge", "title": "Uso de disco",
        "datasource": DS, "gridPos": {"x": 12, "y": 32, "w": 12, "h": 8},
        # Só o disco real da VM (o agente vê a raiz da VM montada em /hostfs)
        "targets": [target(EX, VM, "/FS \\[\\/hostfs(\\/boot)?\\]: Space: Used, in %/")],
        "fieldConfig": {"defaults": {
            "unit": "percent", "min": 0, "max": 100, "decimals": 1,
            "color": {"mode": "thresholds"},
            "thresholds": thresholds((None, GOOD), (80, WARN), (90, CRIT))},
            "overrides": [
                {"matcher": {"id": "byRegexp", "options": ".*hostfs/boot.*"},
                 "properties": [{"id": "displayName", "value": "/boot"}]},
                {"matcher": {"id": "byRegexp", "options": ".*hostfs\\].*"},
                 "properties": [{"id": "displayName", "value": "/ (raiz)"}]}]},
        "options": {"orientation": "horizontal", "displayMode": "gradient",
                    "valueMode": "color", "showUnfilled": True, "minVizHeight": 16,
                    "maxVizHeight": 28, "namePlacement": "top", "sizing": "auto",
                    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}},
    })
    return dashboard("noc-visao-geral", "NOC · Visão Geral (Empresa X)", p,
                     "Telão do NOC: status do serviço, problemas em aberto e saúde da VM.",
                     time_from="now-1h")


# ------------------------------------------------------------------ Detalhes do host
def detalhes_host():
    global _pid
    _pid = 0

    def var(name, label, qtype, group="", host="", regex="", default=None):
        return {"name": name, "label": label, "type": "query", "datasource": DS,
                "query": {"queryType": qtype, "group": group or "/.*/", "host": host,
                          "application": "", "itemTag": "", "item": ""},
                "definition": f"Zabbix - {qtype}", "refresh": 1, "regex": regex,
                "includeAll": False, "multi": False, "sort": 1, "hide": 0,
                "current": ({"text": default, "value": default, "selected": True}
                            if default else {}), "options": []}

    G, H = "$grupo", "$host"
    tmpl = [var("grupo", "Grupo", "group", regex="/Empresa X|Linux servers|Zabbix servers/",
                default="Empresa X"),
            var("host", "Host", "host", group="$grupo", host="/.*/",
                default="VM noc-lab (agente)")]
    p = []
    p.append(row("Resumo de $host", 0))
    p.append(gauge("CPU", 0, 1, 6, 6, [target(G, H, "CPU utilization")]))
    p.append(gauge("Memória", 6, 1, 6, 6, [target(G, H, "Memory utilization")]))
    p.append(stat("Uptime", 12, 1, 6, 6, [target(G, H, "/System uptime|Uptime/")],
                  unit="dtdurations", decimals=0))
    p.append(stat("Processos", 18, 1, 6, 6, [target(G, H, "Number of processes")],
                  decimals=0, graph="area"))
    p.append(row("Uso ao longo do tempo", 7))
    p.append(timeseries("CPU (%)", 0, 8, 12, 8, [target(G, H, "CPU utilization")], "percent",
                        overrides=[color_override(".*", SERIES[0], "CPU")]))
    p.append(timeseries("Memória (%)", 12, 8, 12, 8, [target(G, H, "Memory utilization")],
                        "percent", overrides=[color_override(".*", SERIES[1], "Memória")]))
    p.append(timeseries(
        "Rede (por interface)", 0, 16, 24, 9,
        [target(G, H, "/Bits (received|sent)/")], "bps", fill=0, legend="table",
        overrides=[{"matcher": {"id": "byRegexp", "options": ".*Bits sent.*"},
                    "properties": [{"id": "custom.transform", "value": "negative-Y"}]}],
        desc="Upload abaixo do zero. A tabela mostra último valor e máximo por interface."))
    p.append(problems_panel("Problemas deste host", 0, 25, 24, 7, group=G, host=H))
    return dashboard("noc-host-detalhes", "NOC · Detalhes do Host", p,
                     "Escolha grupo e host no topo para ver CPU, memória, rede e problemas.",
                     templating=tmpl, time_from="now-6h")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, dash in [("noc-visao-geral.json", visao_geral()),
                       ("noc-host-detalhes.json", detalhes_host())]:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(dash, f, ensure_ascii=False, indent=2)
        print("gerado:", name, "-", len(dash["panels"]), "painéis")
